import pickle
from pathlib import Path

import numpy as np
import pytest
from nuscenes.nuscenes import NuScenes

from src.experiments.perception import PointCloudClusterDetector
from src.experiments.planning import evaluate_planning_model, plan_path
from src.utils.config import get_paths_config
from src.utils.path_utils import resolve_project_path


def test_lidar_cluster_detector_emits_real_boxes():
    rng = np.random.default_rng(0)
    cluster_a = rng.normal(loc=[10.0, 1.0, 0.2, 0.5], scale=[0.6, 0.4, 0.2, 0.1], size=(80, 4))
    cluster_b = rng.normal(loc=[18.0, -3.0, 0.4, 0.5], scale=[0.7, 0.5, 0.2, 0.1], size=(90, 4))
    points = np.vstack([cluster_a, cluster_b]).astype(np.float32)

    detector = PointCloudClusterDetector(min_cluster_points=10)
    result = detector.predict(points)

    assert result["boxes"].shape[1] == 7
    assert len(result["scores"]) >= 1
    assert np.all(result["scores"] > 0)


def test_planner_changes_path_when_obstacle_is_in_corridor():
    reference = np.array([[2.0, 0.0], [4.0, 0.0], [6.0, 0.0], [8.0, 0.0]], dtype=np.float32)
    obstacles = np.array([[5.0, 0.0, 2.0, 4.0]], dtype=np.float32)

    planned = plan_path("mpc_smoothing", reference, obstacles)

    assert planned.shape == reference.shape
    assert np.max(np.abs(planned[:, 1])) > 0.1


def test_planning_eval_exposes_visual_obstacles_on_mini_val():
    token_file = Path("nuscenes_mini_val_tokens.pkl")
    if not token_file.exists():
        pytest.skip("nuScenes mini tokens are not prepared")

    paths = get_paths_config()
    dataroot = resolve_project_path(paths.get("nuscenes_dataroot", "data"))
    if not Path(dataroot).exists():
        pytest.skip("nuScenes dataroot is not available")

    with token_file.open("rb") as f:
        tokens = list(pickle.load(f))

    nusc = NuScenes(
        version=paths.get("nuscenes_version", "v1.0-mini"),
        dataroot=dataroot,
        verbose=False,
    )
    metrics = evaluate_planning_model(
        nusc,
        tokens[:8],
        "mpc_smoothing",
        visual_sample_tokens=tokens,
    )

    assert len(metrics["visual_obstacles"]) > 0
    assert metrics["visual_obstacle_count"] == len(metrics["visual_obstacles"])
    assert metrics["visual_scene_score"] > 0
    assert metrics["visual_sample_token"]
    assert "speed_kmh" in metrics["timesteps"][0]
    assert "speed_mps" in metrics["timesteps"][0]
