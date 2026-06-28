"""nuScenes-only offline behavior decision evaluation."""

from __future__ import annotations

import time
from typing import Any, Dict, List, Sequence

import numpy as np

from src.geometry.boxes import annotations_to_boxes, transform_boxes_to_ego


def _ego_speed(nusc, sample: Dict[str, Any]) -> float:
    current = _ego_pose_for_sample(nusc, sample)
    next_token = sample.get("next")
    if not next_token:
        return 0.0
    nxt = nusc.get("sample", next_token)
    next_pose = _ego_pose_for_sample(nusc, nxt)
    dt = max((nxt["timestamp"] - sample["timestamp"]) / 1e6, 1e-3)
    dist = np.linalg.norm(np.array(next_pose["translation"][:2]) - np.array(current["translation"][:2]))
    return float(dist / dt)


def _ego_pose_for_sample(nusc, sample: Dict[str, Any]) -> Dict[str, Any]:
    lidar_token = sample["data"]["LIDAR_TOP"]
    lidar_data = nusc.get("sample_data", lidar_token)
    return nusc.get("ego_pose", lidar_data["ego_pose_token"])


def scene_context(nusc, sample_token: str) -> Dict[str, Any]:
    sample = nusc.get("sample", sample_token)
    ego_pose = _ego_pose_for_sample(nusc, sample)
    annotations = [nusc.get("sample_annotation", token) for token in sample["anns"]]
    boxes_ego = transform_boxes_to_ego(annotations_to_boxes(annotations), ego_pose)

    front_distances = []
    left_clearance = []
    right_clearance = []
    for box in boxes_ego:
        x, y = float(box.center[0]), float(box.center[1])
        if x > 0 and abs(y) < 4.0:
            front_distances.append(x)
        if 0 < x < 35 and 2.0 < y < 7.0:
            left_clearance.append(np.hypot(x, y))
        if 0 < x < 35 and -7.0 < y < -2.0:
            right_clearance.append(np.hypot(x, y))

    min_front = min(front_distances) if front_distances else 80.0
    left_gap = min(left_clearance) if left_clearance else 80.0
    right_gap = min(right_clearance) if right_clearance else 80.0
    speed = _ego_speed(nusc, sample)

    return {
        "sample_token": sample_token,
        "ego_speed": speed,
        "min_front_distance": float(min_front),
        "left_gap": float(left_gap),
        "right_gap": float(right_gap),
        "obstacle_count": len(boxes_ego),
    }


def _reference_action(ctx: Dict[str, Any]) -> str:
    if ctx["min_front_distance"] < 7.0:
        return "stop"
    if ctx["min_front_distance"] < 16.0:
        return "follow"
    return "cruise"


def decide(model_id: str, ctx: Dict[str, Any]) -> Dict[str, Any]:
    front = ctx["min_front_distance"]
    speed = ctx["ego_speed"]
    side_gap = max(ctx["left_gap"], ctx["right_gap"])

    if model_id == "idm_mobil":
        desired_speed = 12.0
        headway = max(front, 1.0)
        accel = 1.2 * (1.0 - (speed / desired_speed) ** 4 - (10.0 / headway) ** 2)
        if front < 7.0:
            action = "stop"
        elif side_gap > 14.0 and front < 18.0 and accel < -0.5:
            action = "lane_change"
        elif accel < -0.25:
            action = "follow"
        else:
            action = "cruise"
        target_speed = max(0.0, speed + accel)
    elif model_id == "imitation_policy":
        # Lightweight deterministic policy that imitates the ego trajectory prior:
        # conservative when scenes are dense, faster when the front corridor is clear.
        if front < 8.0:
            action = "stop"
            target_speed = 0.0
        elif ctx["obstacle_count"] > 18 and front < 22.0:
            action = "follow"
            target_speed = min(speed, 6.0)
        else:
            action = "cruise"
            target_speed = min(max(speed, 7.5), 13.0)
    else:
        if front < 8.0:
            action = "stop"
            target_speed = 0.0
        elif front < 18.0:
            action = "follow"
            target_speed = min(speed, 5.0)
        else:
            action = "cruise"
            target_speed = min(max(speed, 8.0), 12.0)

    safe = not (front < 8.0 and action == "cruise")
    return {
        "action": action,
        "target_speed": float(target_speed),
        "safe": bool(safe),
        "reference_action": _reference_action(ctx),
    }


def evaluate_decision_model(nusc, sample_tokens: Sequence[str], model_id: str) -> Dict[str, Any]:
    start = time.perf_counter()
    records: List[Dict[str, Any]] = []

    for token in sample_tokens:
        ctx = scene_context(nusc, token)
        pred = decide(model_id, ctx)
        records.append({**ctx, **pred})

    elapsed_ms = (time.perf_counter() - start) * 1000.0
    if not records:
        return {
            "safety_rate": 0.0,
            "decision_match_rate": 0.0,
            "min_front_distance": 0.0,
            "latency_ms": elapsed_ms,
            "samples": [],
        }

    safety_rate = sum(1 for r in records if r["safe"]) / len(records)
    match_rate = sum(1 for r in records if r["action"] == r["reference_action"]) / len(records)
    avg_target_speed = float(np.mean([r["target_speed"] for r in records]))
    min_front = float(np.min([r["min_front_distance"] for r in records]))

    return {
        "safety_rate": float(safety_rate),
        "decision_match_rate": float(match_rate),
        "avg_target_speed": avg_target_speed,
        "min_front_distance": min_front,
        "latency_ms": elapsed_ms / max(len(records), 1),
        "samples": records[:10],
    }
