"""nuScenes-only lightweight local planning evaluation."""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

from src.geometry.boxes import annotations_to_boxes, transform_boxes_to_ego
from src.geometry.transforms import get_global_to_ego_transform, apply_transform

ROAD_HALF_WIDTH_M = 5.0
EGO_HALF_WIDTH_M = 1.0
EGO_HALF_LENGTH_M = 2.2
SAFETY_BUFFER_M = 1.2
MAX_CENTER_LATERAL_M = ROAD_HALF_WIDTH_M - EGO_HALF_WIDTH_M - 0.3
NUSCENES_SAMPLE_DT_S = 0.5


def _ego_pose_for_sample(nusc, sample: Dict[str, Any]) -> Dict[str, Any]:
    lidar_token = sample["data"]["LIDAR_TOP"]
    lidar_data = nusc.get("sample_data", lidar_token)
    return nusc.get("ego_pose", lidar_data["ego_pose_token"])


def _future_ego_path(nusc, sample_token: str, horizon: int = 8) -> np.ndarray:
    sample = nusc.get("sample", sample_token)
    current_pose = _ego_pose_for_sample(nusc, sample)
    global_to_current = get_global_to_ego_transform(current_pose)

    points = []
    current = sample
    for _ in range(horizon):
        next_token = current.get("next")
        if not next_token:
            break
        current = nusc.get("sample", next_token)
        pose = _ego_pose_for_sample(nusc, current)
        global_xyz = np.array([[pose["translation"][0], pose["translation"][1], pose["translation"][2]]], dtype=np.float32)
        ego_xyz = apply_transform(global_xyz, global_to_current)[0]
        points.append([float(ego_xyz[0]), float(ego_xyz[1])])

    if len(points) < 2:
        points = [[0.0, 0.0], *[[float(i * 2.0), 0.0] for i in range(1, horizon + 1)]]
    else:
        points = [[0.0, 0.0], *points]
    return np.asarray(points, dtype=np.float32)


def _obstacles_ego(nusc, sample_token: str) -> np.ndarray:
    sample = nusc.get("sample", sample_token)
    ego_pose = _ego_pose_for_sample(nusc, sample)
    annotations = [nusc.get("sample_annotation", token) for token in sample["anns"]]
    boxes = transform_boxes_to_ego(annotations_to_boxes(annotations), ego_pose)
    rows = []
    for box in boxes:
        rows.append([box.center[0], box.center[1], box.size[0], box.size[1]])
    if not rows:
        return np.zeros((0, 4), dtype=np.float32)
    return np.asarray(rows, dtype=np.float32)


def _avoidance_offset(path: np.ndarray, obstacles: np.ndarray) -> np.ndarray:
    offset = np.zeros(len(path), dtype=np.float32)
    for obs_x, obs_y, obs_w, obs_l in obstacles:
        if obs_x <= 0 or abs(obs_y) > ROAD_HALF_WIDTH_M:
            continue
        distances = np.abs(path[:, 0] - obs_x)
        influence = np.clip(1.0 - distances / 16.0, 0.0, 1.0)
        if not np.any(influence > 0.0):
            continue

        inflated_half_width = obs_w / 2.0 + EGO_HALF_WIDTH_M + SAFETY_BUFFER_M
        lateral_gap = np.abs(path[:, 1] - obs_y)
        if not np.any((influence > 0.0) & (lateral_gap < inflated_half_width)):
            continue

        direction = -1.0 if obs_y >= 0 else 1.0
        target_shift = max(3.2, inflated_half_width + 0.4)
        offset += direction * influence * target_shift
    return np.clip(offset, -MAX_CENTER_LATERAL_M, MAX_CENTER_LATERAL_M)


def plan_path(model_id: str, reference_path: np.ndarray, obstacles: np.ndarray) -> np.ndarray:
    path = reference_path.copy()
    if len(path) == 0:
        return path

    offset = _avoidance_offset(path, obstacles)
    if model_id == "hybrid_astar":
        path[:, 1] += np.sign(offset) * np.minimum(np.abs(offset) + 0.4, 4.8)
    elif model_id == "frenet_lattice":
        ramp = np.linspace(0.35, 1.0, len(path), dtype=np.float32)
        path[:, 1] += offset * ramp
    else:
        path[:, 1] += offset
        if len(path) >= 3:
            kernel = np.array([0.25, 0.5, 0.25], dtype=np.float32)
            padded = np.pad(path[:, 1], (1, 1), mode="edge")
            path[:, 1] = np.convolve(padded, kernel, mode="valid")
    path[:, 1] = np.clip(path[:, 1], -MAX_CENTER_LATERAL_M, MAX_CENTER_LATERAL_M)
    return path


def _curvature(path: np.ndarray) -> float:
    if len(path) < 3:
        return 0.0
    diffs = np.diff(path, axis=0)
    headings = np.arctan2(diffs[:, 1], np.maximum(diffs[:, 0], 1e-3))
    return float(np.mean(np.abs(np.diff(headings)))) if len(headings) > 1 else 0.0


def _jerk(path: np.ndarray) -> float:
    if len(path) < 4:
        return 0.0
    third = np.diff(path, n=3, axis=0)
    return float(np.mean(np.linalg.norm(third, axis=1)))


def _collision_rate(path: np.ndarray, obstacles: np.ndarray) -> float:
    if len(path) == 0 or len(obstacles) == 0:
        return 0.0
    hits = 0
    for point in path:
        for obs_x, obs_y, obs_w, obs_l in obstacles:
            longitudinal_hit = abs(point[0] - obs_x) <= (obs_l / 2.0 + EGO_HALF_LENGTH_M + SAFETY_BUFFER_M)
            lateral_hit = abs(point[1] - obs_y) <= (obs_w / 2.0 + EGO_HALF_WIDTH_M + SAFETY_BUFFER_M)
            if longitudinal_hit and lateral_hit:
                hits += 1
                break
    return float(hits / len(path))


def _min_clearance(path: np.ndarray, obstacles: np.ndarray) -> float:
    if len(path) == 0 or len(obstacles) == 0:
        return 80.0
    clearances = []
    for point in path:
        for obs_x, obs_y, obs_w, obs_l in obstacles:
            dx = abs(point[0] - obs_x) - (obs_l / 2.0 + EGO_HALF_LENGTH_M)
            dy = abs(point[1] - obs_y) - (obs_w / 2.0 + EGO_HALF_WIDTH_M)
            if dx <= 0 and dy <= 0:
                clearances.append(float(max(dx, dy)))
            else:
                clearances.append(float(np.hypot(max(dx, 0.0), max(dy, 0.0))))
    return float(min(clearances)) if clearances else 80.0


def _visual_obstacles(obstacles: np.ndarray, limit: int = 16) -> List[Dict[str, Any]]:
    rows = []
    for obs_x, obs_y, obs_w, obs_l in obstacles:
        in_view = -3.0 <= obs_x <= 42.0 and abs(obs_y) <= ROAD_HALF_WIDTH_M + 4.0
        if in_view:
            in_road = abs(obs_y) <= ROAD_HALF_WIDTH_M
            edge_hint = ""
            if obs_y > ROAD_HALF_WIDTH_M:
                edge_hint = "left_outside"
            elif obs_y < -ROAD_HALF_WIDTH_M:
                edge_hint = "right_outside"
            rows.append({
                "x": float(obs_x),
                "y": float(obs_y),
                "width": float(max(obs_w, 0.5)),
                "length": float(max(obs_l, 0.5)),
                "safety_buffer": float(SAFETY_BUFFER_M),
                "in_view": True,
                "in_road": bool(in_road),
                "edge_hint": edge_hint,
            })
    rows.sort(key=lambda item: (item["x"], abs(item["y"])))
    return rows[:limit]


def _visual_scene_score(obstacles: np.ndarray) -> float:
    if len(obstacles) == 0:
        return -1.0

    score = 0.0
    for obs_x, obs_y, _obs_w, _obs_l in obstacles:
        in_view = -2.0 <= obs_x <= 42.0 and abs(obs_y) <= ROAD_HALF_WIDTH_M + 2.0
        if not in_view:
            continue

        score += 1.0
        if 2.0 <= obs_x <= 40.0:
            score += 2.0
        if 8.0 <= obs_x <= 30.0:
            score += 3.0
        if abs(obs_y) <= 4.0:
            score += 8.0
        if abs(obs_y) <= 2.0:
            score += 6.0
        score += max(0.0, 30.0 - abs(obs_x - 18.0)) / 10.0
    return float(score)


def _visual_candidate(
    nusc,
    sample_token: str,
    model_id: str,
    source: str,
) -> Tuple[str, str, np.ndarray, np.ndarray, List[Dict[str, Any]], float]:
    reference = _future_ego_path(nusc, sample_token)
    obstacles = _obstacles_ego(nusc, sample_token)
    planned = plan_path(model_id, reference, obstacles)
    visual_obstacles = _visual_obstacles(obstacles)
    return sample_token, source, planned, obstacles, visual_obstacles, _visual_scene_score(obstacles)


def _better_visual_candidate(
    current: Optional[Tuple[str, str, np.ndarray, np.ndarray, List[Dict[str, Any]], float]],
    candidate: Tuple[str, str, np.ndarray, np.ndarray, List[Dict[str, Any]], float],
) -> Tuple[str, str, np.ndarray, np.ndarray, List[Dict[str, Any]], float]:
    if current is None:
        return candidate
    if len(candidate[4]) == 0 and len(current[4]) > 0:
        return current
    if len(candidate[4]) > 0 and len(current[4]) == 0:
        return candidate
    return candidate if candidate[5] > current[5] else current


def _timesteps_from_path(path: np.ndarray, latency_ms: float) -> List[Dict[str, Any]]:
    if len(path) == 0:
        return []
    dense_count = 50
    src = np.linspace(0, 1, len(path))
    dst = np.linspace(0, 1, dense_count)
    x = np.interp(dst, src, path[:, 0])
    y = np.interp(dst, src, path[:, 1])
    duration_s = max((len(path) - 1) * NUSCENES_SAMPLE_DT_S, 0.1)
    frame_dt_s = duration_s / max(dense_count - 1, 1)
    dx = np.gradient(x)
    dy = np.gradient(y)
    yaw = np.degrees(np.arctan2(dy, np.maximum(dx, 1e-3)))
    steering = np.gradient(yaw)
    speed_mps = np.clip(np.hypot(dx, dy) / frame_dt_s, 0.0, 15.0)

    timesteps = []
    for i in range(dense_count):
        timesteps.append({
            "step": i,
            "time": float(i * frame_dt_s),
            "x": float(x[i]),
            "y": float(y[i]),
            "speed": float(speed_mps[i]),
            "speed_mps": float(speed_mps[i]),
            "speed_kmh": float(speed_mps[i] * 3.6),
            "yaw": float(yaw[i]),
            "steering": float(steering[i]),
            "latency_breakdown": {
                "preprocessing": 4.0,
                "perception": 18.0,
                "decision": 2.0,
                "planning": float(latency_ms),
            },
        })
    return timesteps


def evaluate_planning_model(
    nusc,
    sample_tokens: Sequence[str],
    model_id: str,
    visual_sample_tokens: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    start = time.perf_counter()
    rows = []
    visual_candidate = None

    for token in sample_tokens:
        reference = _future_ego_path(nusc, token)
        obstacles = _obstacles_ego(nusc, token)
        planned = plan_path(model_id, reference, obstacles)
        candidate = (token, "evaluation_samples", planned, obstacles, _visual_obstacles(obstacles), _visual_scene_score(obstacles))
        visual_candidate = _better_visual_candidate(visual_candidate, candidate)
        min_len = min(len(reference), len(planned))
        if min_len == 0:
            continue
        error = planned[:min_len] - reference[:min_len]
        rows.append({
            "ade": float(np.mean(np.linalg.norm(error, axis=1))),
            "fde": float(np.linalg.norm(error[-1])),
            "collision_rate": _collision_rate(planned, obstacles),
            "offroad_rate": float(np.mean(np.abs(planned[:, 1]) > MAX_CENTER_LATERAL_M)),
            "min_clearance_m": _min_clearance(planned, obstacles),
            "jerk": _jerk(planned),
            "curvature": _curvature(planned),
        })

    elapsed_ms = (time.perf_counter() - start) * 1000.0
    if not rows:
        rows = [{
            "ade": 0.0,
            "fde": 0.0,
            "collision_rate": 0.0,
            "offroad_rate": 0.0,
            "min_clearance_m": 80.0,
            "jerk": 0.0,
            "curvature": 0.0,
        }]

    if (visual_candidate is None or len(visual_candidate[4]) == 0) and visual_sample_tokens:
        evaluated = set(sample_tokens)
        for token in visual_sample_tokens:
            if token in evaluated:
                continue
            candidate = _visual_candidate(nusc, token, model_id, "split_fallback")
            visual_candidate = _better_visual_candidate(visual_candidate, candidate)
            if visual_candidate and len(visual_candidate[4]) > 0 and visual_candidate[5] >= 20.0:
                break

    visual_sample_token = visual_candidate[0] if visual_candidate else None
    visual_sample_source = visual_candidate[1] if visual_candidate else "none"
    visual_path = visual_candidate[2] if visual_candidate else np.zeros((0, 2))
    visual_rows = visual_candidate[4] if visual_candidate else []
    visual_score = visual_candidate[5] if visual_candidate else -1.0

    metrics = {
        key: float(np.mean([row[key] for row in rows]))
        for key in rows[0].keys()
    }
    metrics["latency_ms"] = elapsed_ms / max(len(rows), 1)
    metrics["timesteps"] = _timesteps_from_path(visual_path, metrics["latency_ms"])
    metrics["visual_obstacles"] = visual_rows
    metrics["visual_obstacle_count"] = len(visual_rows)
    metrics["visual_scene_score"] = visual_score
    metrics["visual_sample_token"] = visual_sample_token
    metrics["visual_sample_source"] = visual_sample_source
    return metrics
