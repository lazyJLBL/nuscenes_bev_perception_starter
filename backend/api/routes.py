# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import sys
import inspect
import uuid
import glob
import json
from typing import Any, Dict, Optional

import cv2
import matplotlib
import numpy as np
import torch
from fastapi import APIRouter, File, Request, UploadFile
from pydantic import BaseModel
from torch.utils.data import DataLoader

matplotlib.use("Agg")
import matplotlib.pyplot as plt

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from nuscenes.nuscenes import NuScenes

import src.experiments.planning as planning_module
from src.detection.nuscenes_dataset import NuScenesDetDataset, collate_fn
from src.detection.simple_pillars import SimplePointPillars
from src.experiments.perception import PointCloudClusterDetector
from src.experiments.registry import get_model_registry, get_module_configs, latest_run_record
from src.experiments.runner import run_offline_experiment
from src.experiments.schemas import ExperimentSpec, RunRecord
from src.utils.config import get_model_config, get_paths_config
from src.utils.path_utils import resolve_project_path

router = APIRouter()

GLOBAL_STATE: Dict[str, Any] = {
    "nusc": None,
    "dataset": None,
    "pointpillars": None,
    "device": None,
    "classes": None,
    "point_cloud_range": None,
    "voxel_size": None,
}

LIDAR_MODELS = {"pointpillars", "lidar_cluster", "lidar_topdown", "lidar_3views", "lidar_intensity"}
EXTERNAL_PERCEPTION_MODELS = {"second", "centerpoint"}


def _static_path(filename: str) -> str:
    static_dir = os.path.join(PROJECT_ROOT, "backend", "static")
    os.makedirs(static_dir, exist_ok=True)
    return os.path.join(static_dir, filename)


def _device() -> torch.device:
    if GLOBAL_STATE["device"] is None:
        GLOBAL_STATE["device"] = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    return GLOBAL_STATE["device"]


def _runtime_config():
    model_cfg = get_model_config()
    pp_cfg = model_cfg.get("pointpillars", {})
    classes = ["car", "pedestrian", "bicycle", "bus", "truck"]
    return {
        "classes": classes,
        "point_cloud_range": pp_cfg.get("point_cloud_range", [-51.2, -51.2, -5.0, 51.2, 51.2, 3.0]),
        "voxel_size": pp_cfg.get("voxel_size", [0.2, 0.2, 8.0]),
    }


def _init_nuscenes_dataset() -> NuScenesDetDataset:
    if GLOBAL_STATE["dataset"] is not None:
        return GLOBAL_STATE["dataset"]

    paths_cfg = get_paths_config()
    dataroot = resolve_project_path(paths_cfg.get("nuscenes_dataroot", "data"))
    version = paths_cfg.get("nuscenes_version", "v1.0-mini")
    tokens_file = os.path.join(PROJECT_ROOT, "nuscenes_mini_val_tokens.pkl")
    if not os.path.exists(tokens_file):
        raise FileNotFoundError("缺少 nuscenes_mini_val_tokens.pkl，请先运行 scripts/06_prepare_detection_baseline.py --execute")

    nusc = NuScenes(version=version, dataroot=dataroot, verbose=False)
    cfg = _runtime_config()
    dataset = NuScenesDetDataset(
        nusc=nusc,
        tokens_file=tokens_file,
        classes=cfg["classes"],
        point_cloud_range=cfg["point_cloud_range"],
        voxel_size=cfg["voxel_size"],
        training=True,
    )
    GLOBAL_STATE["nusc"] = nusc
    GLOBAL_STATE["dataset"] = dataset
    GLOBAL_STATE["classes"] = cfg["classes"]
    GLOBAL_STATE["point_cloud_range"] = cfg["point_cloud_range"]
    GLOBAL_STATE["voxel_size"] = cfg["voxel_size"]
    return dataset


def _load_pointpillars() -> SimplePointPillars:
    if GLOBAL_STATE["pointpillars"] is not None:
        return GLOBAL_STATE["pointpillars"]

    dataset = _init_nuscenes_dataset()
    device = _device()
    cfg = _runtime_config()

    work_dir = os.path.join(PROJECT_ROOT, "outputs", "predictions", "train_results")
    candidates = [
        os.path.join(work_dir, "model_exported.pth"),
        os.path.join(work_dir, "best.pth"),
        os.path.join(work_dir, "latest.pth"),
    ]
    ckpt_path = next((p for p in candidates if os.path.exists(p)), None)
    if ckpt_path is None:
        raise FileNotFoundError("未找到真实 PointPillars checkpoint，请先训练或导入权重。")

    checkpoint = torch.load(ckpt_path, map_location=device, weights_only=False)
    if isinstance(checkpoint, dict) and "model_config" in checkpoint:
        model_cfg = checkpoint["model_config"]
        classes = model_cfg.get("classes", cfg["classes"])
        point_cloud_range = model_cfg.get("point_cloud_range", cfg["point_cloud_range"])
        voxel_size = model_cfg.get("voxel_size", cfg["voxel_size"])
    else:
        classes = cfg["classes"]
        point_cloud_range = cfg["point_cloud_range"]
        voxel_size = cfg["voxel_size"]

    model = SimplePointPillars(
        point_cloud_range=point_cloud_range,
        voxel_size=voxel_size,
        num_classes=len(classes),
        classes=classes,
    ).to(device)

    state_dict = checkpoint["model_state_dict"] if isinstance(checkpoint, dict) and "model_state_dict" in checkpoint else checkpoint
    model.load_state_dict(state_dict)
    model.eval()

    GLOBAL_STATE["pointpillars"] = model
    GLOBAL_STATE["classes"] = classes
    GLOBAL_STATE["dataset"] = dataset
    return model


def _parse_lidar_upload(filename: str, contents: bytes) -> Dict[str, Any]:
    if not filename.lower().endswith(".bin"):
        raise ValueError(f"当前模型需要 LiDAR .bin 点云文件，但上传的是 {filename}")
    file_size = len(contents)
    if file_size == 0:
        raise ValueError("上传文件为空。")
    if file_size % 4 != 0:
        raise ValueError(f"文件大小 {file_size} 不是 float32 的 4 字节整数倍。")

    values = np.frombuffer(contents, dtype=np.float32)
    if values.size % 5 == 0:
        channels = 5
    elif values.size % 4 == 0:
        channels = 4
    else:
        raise ValueError("点云必须是 4 通道 [x,y,z,intensity] 或 5 通道 nuScenes 格式。")

    points = values.reshape(-1, channels)
    if len(points) < 100:
        raise ValueError(f"点云只有 {len(points)} 个点，数量过少。")
    return {
        "points": points[:, :4].copy(),
        "num_points": int(len(points)),
        "num_channels": int(channels),
        "file_size": int(file_size),
    }


def _matched_dataset_item(dataset: NuScenesDetDataset, filename: str) -> Optional[Dict[str, Any]]:
    base = os.path.basename(filename)
    for idx, token in enumerate(dataset.tokens):
        sample = dataset.nusc.get("sample", token)
        lidar_token = sample["data"]["LIDAR_TOP"]
        lidar_data = dataset.nusc.get("sample_data", lidar_token)
        if os.path.basename(lidar_data["filename"]) == base:
            return dataset[idx]
    return None


def _batch_from_points(dataset: NuScenesDetDataset, points: np.ndarray) -> Dict[str, Any]:
    pillar_features, pillar_coords, num_points = dataset.voxelize(points)
    return collate_fn([{
        "sample_token": "uploaded_sample",
        "pillar_features": pillar_features,
        "pillar_coords": pillar_coords,
        "num_points": num_points,
    }])


def _to_numpy(value):
    if hasattr(value, "detach"):
        return value.detach().cpu().numpy()
    return np.asarray(value)


def _visualize_bev(
    raw_points: np.ndarray,
    pred_dict: Dict[str, Any],
    output_path: str,
    batch_dict: Optional[Dict[str, Any]] = None,
    title: str = "LiDAR BEV Detection",
) -> None:
    fig, ax = plt.subplots(figsize=(10, 10), facecolor="#111827")
    ax.set_facecolor("black")

    mask = (
        (raw_points[:, 0] >= -51.2) & (raw_points[:, 0] <= 51.2)
        & (raw_points[:, 1] >= -51.2) & (raw_points[:, 1] <= 51.2)
    )
    pts = raw_points[mask]
    if len(pts) > 30000:
        rng = np.random.default_rng(42)
        pts = pts[rng.choice(len(pts), 30000, replace=False)]
    if len(pts):
        sc = ax.scatter(pts[:, 0], pts[:, 1], c=pts[:, 2], cmap="viridis", s=1, alpha=0.65)
        cb = plt.colorbar(sc, ax=ax, pad=0.02, aspect=40)
        cb.set_label("Height z (m)", color="white")
        cb.ax.tick_params(colors="white")

    if batch_dict and "gt_boxes" in batch_dict and batch_dict["gt_boxes"]:
        for box in batch_dict["gt_boxes"][0]:
            _draw_box(ax, box, color="lime", linewidth=1.6, linestyle="-")

    boxes = _to_numpy(pred_dict.get("boxes", np.zeros((0, 7), dtype=np.float32)))
    for box in boxes:
        _draw_box(ax, box, color="red", linewidth=2.0, linestyle="--")

    ax.plot(0, 0, marker="*", color="#60a5fa", markersize=15)
    ax.set_xlim(-51.2, 51.2)
    ax.set_ylim(-51.2, 51.2)
    ax.set_aspect("equal")
    ax.set_title(title, color="white", fontsize=14)
    ax.tick_params(colors="white")
    for spine in ax.spines.values():
        spine.set_color("white")
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight", facecolor="#111827")
    plt.close(fig)


def _draw_box(ax, box, color: str, linewidth: float, linestyle: str) -> None:
    x, y, w, l, rot = float(box[0]), float(box[1]), float(box[3]), float(box[4]), float(box[6])
    corners = np.array([[-l / 2, -w / 2], [l / 2, -w / 2], [l / 2, w / 2], [-l / 2, w / 2], [-l / 2, -w / 2]])
    cos_r, sin_r = np.cos(rot), np.sin(rot)
    rot_mat = np.array([[cos_r, -sin_r], [sin_r, cos_r]])
    corners = corners @ rot_mat.T
    corners[:, 0] += x
    corners[:, 1] += y
    ax.plot(corners[:, 0], corners[:, 1], color=color, linewidth=linewidth, linestyle=linestyle)


def _run_pointpillars_inference(filename: str, points: np.ndarray):
    dataset = _init_nuscenes_dataset()
    model = _load_pointpillars()
    device = _device()

    sample_data = _matched_dataset_item(dataset, filename)
    batch_dict = collate_fn([sample_data]) if sample_data is not None else _batch_from_points(dataset, points)
    batch_dict["pillar_features"] = batch_dict["pillar_features"].to(device)
    batch_dict["pillar_coords"] = batch_dict["pillar_coords"].to(device)
    batch_dict["num_points"] = batch_dict["num_points"].to(device)

    with torch.no_grad():
        result = model.predict(batch_dict, score_threshold=0.2, nms_threshold=0.2)[0]
    return result, batch_dict


def _run_cluster_inference(points: np.ndarray):
    detector = PointCloudClusterDetector()
    return detector.predict(points), None


def _image_preprocess(contents: bytes, filename: str, output_path: str) -> Dict[str, Any]:
    ext = os.path.splitext(filename.lower())[1]
    if ext not in {".jpg", ".jpeg", ".png", ".webp"}:
        raise ValueError("当前模型需要图像文件：.jpg, .jpeg, .png 或 .webp。")
    nparr = np.frombuffer(contents, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("图像无法解析，可能文件已损坏。")
    cv2.putText(image, "DETERMINISTIC CAMERA PREPROCESS", (20, 36), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2, cv2.LINE_AA)
    cv2.imwrite(output_path, image)
    return {"file_size": len(contents)}


def _selected_entry(module_configs: Dict[str, Any], subsystem: str, model_id: str) -> Dict[str, Any]:
    models_by_sub = module_configs.get(subsystem, {}).get("modelsBySub", {})
    for models in models_by_sub.values():
        for model in models:
            if model["id"] == model_id:
                return model
    return {"id": model_id, "name": model_id, "status": "unknown", "latency": 0, "memory": 0, "fps": 0, "metrics": {}}


def _record_to_sandbox(record: RunRecord, request: Request) -> Dict[str, Any]:
    module_configs = get_module_configs(PROJECT_ROOT)
    perception = record.reports["perception"]
    decision = record.reports["decision"]
    planning = record.reports["planning"]

    prep_entry = _selected_entry(module_configs, "preprocessing", record.spec.preprocessing_model)
    per_entry = _selected_entry(module_configs, "perception", record.spec.perception_model)
    dec_entry = _selected_entry(module_configs, "decision", record.spec.decision_model)
    plan_entry = _selected_entry(module_configs, "planning", record.spec.planning_model)

    prep_latency = float(prep_entry.get("latency") or 0.0)
    per_latency = float(perception.metrics.get("latency_ms") or per_entry.get("latency") or 0.0)
    dec_latency = float(decision.metrics.get("latency_ms") or dec_entry.get("latency") or 0.0)
    plan_latency = float(planning.metrics.get("latency_ms") or plan_entry.get("latency") or 0.0)
    total_latency = prep_latency + per_latency + dec_latency + plan_latency

    safety_score = float(decision.metrics.get("safety_rate", 0.0) or 0.0) * 100.0
    jerk = float(planning.metrics.get("jerk", 0.0) or 0.0)
    collision = float(planning.metrics.get("collision_rate", 0.0) or 0.0)
    offroad = float(planning.metrics.get("offroad_rate", 0.0) or 0.0)
    visual_obstacles = planning.metrics.get("visual_obstacles") or []
    visual_scene_score = planning.metrics.get("visual_scene_score")
    visual_sample_token = planning.metrics.get("visual_sample_token")
    visual_sample_source = planning.metrics.get("visual_sample_source", "none")
    comfort_score = max(0.0, 100.0 - jerk * 30.0 - collision * 100.0 - offroad * 60.0)
    target_speed = float(decision.metrics.get("avg_target_speed", 0.0) or 0.0)
    efficiency_score = min(100.0, target_speed / 12.0 * 100.0)

    timesteps = []
    for step in record.timesteps:
        step = dict(step)
        step["latency_breakdown"] = {
            "preprocessing": prep_latency,
            "perception": per_latency,
            "decision": dec_latency,
            "planning": plan_latency,
        }
        timesteps.append(step)

    sandbox_warnings = []
    if not visual_obstacles:
        sandbox_warnings.append(
            "Backend returned no visible obstacles for this sandbox run. Check /api/health and the planning report."
        )

    return {
        "success": True,
        "run_id": record.run_id,
        "status": record.status,
        "config": {
            "preprocessing": prep_entry,
            "perception": per_entry,
            "decision": dec_entry,
            "planning": plan_entry,
        },
        "stats": {
            "total_latency_ms": round(total_latency, 2),
            "total_memory_gb": round(sum(float(x.get("memory") or 0.0) for x in [prep_entry, per_entry, dec_entry, plan_entry]), 2),
            "average_fps": round(1000.0 / total_latency, 1) if total_latency > 0 else 0.0,
            "safety_score": round(safety_score, 1),
            "comfort_score": round(comfort_score, 1),
            "efficiency_score": round(efficiency_score, 1),
        },
        "reports": {k: v.to_dict() for k, v in record.reports.items()},
        "timesteps": timesteps,
        "obstacles": visual_obstacles,
        "obstacle_count": len(visual_obstacles),
        "visual_scene_score": visual_scene_score,
        "visual_sample_token": visual_sample_token,
        "visual_sample_source": visual_sample_source,
        "coordinate_frame": {
            "x": "forward_m",
            "y": "left_m",
        },
        "warnings": sandbox_warnings,
        "simulation_image": None,
        "run_record_url": str(request.base_url) + f"static/{record.run_id}.json",
    }


@router.get("/health")
async def health():
    planning_source = inspect.getsource(planning_module)
    timestep_source = inspect.getsource(planning_module._timesteps_from_path)
    return {
        "success": True,
        "pid": os.getpid(),
        "cwd": os.getcwd(),
        "project_root": PROJECT_ROOT,
        "routes_path": os.path.abspath(__file__),
        "planning_path": os.path.abspath(inspect.getsourcefile(planning_module) or ""),
        "capabilities": {
            "visual_obstacles": "visual_obstacles" in planning_source,
            "visual_scene_score": "visual_scene_score" in planning_source,
            "visual_sample_token": "visual_sample_token" in planning_source,
            "speed_kmh": "speed_kmh" in timestep_source,
            "speed_mps": "speed_mps" in timestep_source,
        },
    }


@router.get("/modules", response_model=Dict[str, Any])
async def get_modules():
    return get_module_configs(PROJECT_ROOT)


@router.get("/experiments/latest")
async def get_latest_experiment():
    record = latest_run_record(PROJECT_ROOT)
    return {"success": record is not None, "record": record}


@router.get("/experiments")
async def get_experiments(limit: int = 12):
    safe_limit = max(1, min(int(limit or 12), 50))
    pattern = os.path.join(PROJECT_ROOT, "outputs", "experiments", "*", "run_record.json")
    candidates = sorted(glob.glob(pattern), key=os.path.getmtime, reverse=True)[:safe_limit]
    records = []
    for path in candidates:
        try:
            with open(path, "r", encoding="utf-8") as f:
                record = json.load(f)
            record["run_record_path"] = path
            records.append(record)
        except Exception as exc:
            records.append({
                "run_id": os.path.basename(os.path.dirname(path)),
                "status": "unreadable",
                "run_record_path": path,
                "error": str(exc),
            })
    return {"success": True, "count": len(records), "records": records}


class ExperimentRequest(BaseModel):
    preprocessing: str = "lidar_topdown"
    perception: str = "pointpillars"
    decision: str = "fsm_decision"
    planning: str = "mpc_smoothing"
    max_samples: int = 8


@router.post("/run_experiment")
async def run_experiment(config: ExperimentRequest, request: Request):
    spec = ExperimentSpec.from_dict(config.model_dump())
    record = run_offline_experiment(spec)
    return _record_to_sandbox(record, request)


@router.post("/run_sandbox")
async def run_sandbox(config: ExperimentRequest, request: Request):
    spec = ExperimentSpec.from_dict(config.model_dump())
    record = run_offline_experiment(spec)
    return _record_to_sandbox(record, request)


@router.post("/inference/{model_id}")
async def run_inference(model_id: str, request: Request, file: UploadFile = File(...)):
    contents = await file.read()
    filename = file.filename or "uploaded.bin"

    try:
        if model_id in EXTERNAL_PERCEPTION_MODELS:
            return {
                "success": False,
                "error": f"{model_id} 已移除模拟推理。请配置真实 checkpoint 和适配器后再运行。",
            }

        output_filename = f"processed_{uuid.uuid4().hex}.jpg"
        output_path = _static_path(output_filename)

        if model_id in LIDAR_MODELS:
            parsed = _parse_lidar_upload(filename, contents)
            points = parsed["points"]

            if model_id == "pointpillars":
                pred_dict, batch_dict = _run_pointpillars_inference(filename, points)
                title = "Simple PointPillars Detection (real checkpoint)"
            elif model_id == "lidar_cluster":
                pred_dict, batch_dict = _run_cluster_inference(points)
                title = "LiDAR Cluster Baseline (deterministic)"
            else:
                pred_dict = {"boxes": np.zeros((0, 7), dtype=np.float32), "scores": np.zeros(0), "labels": np.zeros(0, dtype=np.int64)}
                batch_dict = None
                title = "LiDAR deterministic preprocessing"

            _visualize_bev(points, pred_dict, output_path, batch_dict=batch_dict, title=title)
            return {
                "success": True,
                "model_id": model_id,
                "inference_result_url": f"{str(request.base_url)}static/{output_filename}",
                "filename": filename,
                "num_points": parsed["num_points"],
                "num_channels": parsed["num_channels"],
                "file_size": parsed["file_size"],
                "num_detections": int(len(pred_dict.get("scores", []))),
            }

        info = _image_preprocess(contents, filename, output_path)
        return {
            "success": True,
            "model_id": model_id,
            "inference_result_url": f"{str(request.base_url)}static/{output_filename}",
            "filename": filename,
            **info,
        }
    except Exception as exc:
        return {"success": False, "model_id": model_id, "error": str(exc)}
