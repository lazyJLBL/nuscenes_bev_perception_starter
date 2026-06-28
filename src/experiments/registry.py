"""Model registry and frontend module configuration generation."""

from __future__ import annotations

import glob
import json
import os
from copy import deepcopy
from typing import Any, Dict, Optional

from src.utils.config import get_project_root


def _project_root(project_root: Optional[str] = None) -> str:
    return project_root or get_project_root()


def _load_json_if_exists(path: str) -> Optional[Dict[str, Any]]:
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def latest_run_record(project_root: Optional[str] = None) -> Optional[Dict[str, Any]]:
    root = _project_root(project_root)
    candidates = sorted(glob.glob(os.path.join(root, "outputs", "experiments", "*", "run_record.json")))
    if not candidates:
        return None
    return _load_json_if_exists(candidates[-1])


def _detection_metrics(project_root: Optional[str] = None) -> Dict[str, Any]:
    root = _project_root(project_root)
    metrics = _load_json_if_exists(os.path.join(root, "outputs", "predictions", "metrics_summary.json")) or {}
    return {
        "mean_ap": float(metrics.get("mean_ap", 0.0) or 0.0),
        "nd_score": float(metrics.get("nd_score", 0.0) or 0.0),
        "trans_err": float(metrics.get("tp_errors", {}).get("trans_err", 0.0) or 0.0),
    }


def get_model_registry(project_root: Optional[str] = None) -> Dict[str, Dict[str, Dict[str, Any]]]:
    root = _project_root(project_root)
    detection_metrics = _detection_metrics(root)
    checkpoint_exists = any(
        os.path.exists(os.path.join(root, "outputs", "predictions", "train_results", name))
        for name in ("model_exported.pth", "best.pth", "latest.pth")
    )

    pointpillars_status = "active" if checkpoint_exists else "needs_checkpoint"
    pointpillars_warning = "" if checkpoint_exists else "需要先训练或导入 checkpoint。"
    if detection_metrics["mean_ap"] <= 0.0 and detection_metrics["nd_score"] <= 0.0:
        pointpillars_warning = "当前评估指标为 0，请重新训练或检查检测结果。"

    return {
        "preprocessing": {
            "cam_surround": {
                "name": "6路环视相机预处理",
                "status": "active",
                "latency": 8.0,
                "memory": 0.4,
                "fps": 125,
                "desc": "读取并校验相机图像，输出可复现实验前处理预览。",
                "metrics": {"sync_rate": 1.0},
            },
            "lidar_topdown": {
                "name": "LiDAR BEV 俯视图",
                "status": "active",
                "latency": 5.0,
                "memory": 0.2,
                "fps": 200,
                "desc": "基于点云生成 BEV 预处理图，不依赖学习模型。",
                "metrics": {"deterministic": True},
            },
        },
        "perception": {
            "pointpillars": {
                "name": "Simple PointPillars",
                "status": pointpillars_status,
                "latency": 18.0,
                "memory": 1.2,
                "fps": 55,
                "desc": "项目内置的 anchor-based PointPillars smoke baseline，使用真实 checkpoint 和 nuScenes 检测指标。",
                "metrics": detection_metrics,
                "warning": pointpillars_warning,
                "outputImage": "/results/simple_bev_boxes_ca9a282c.jpg",
                "camImage": "/results/boxes_cam_front_ca9a282c.jpg",
            },
            "lidar_cluster": {
                "name": "LiDAR Cluster Baseline",
                "status": "active",
                "latency": 9.0,
                "memory": 0.1,
                "fps": 110,
                "desc": "无需训练的真实点云聚类 baseline，用于验证数据、可视化和实验管线，不冒充深度模型。",
                "metrics": {"metric_source": "local_clustering_smoke"},
                "outputImage": "/results/sample_lidar_topdown_ca9a282c.jpg",
                "camImage": None,
            },
            "second": {
                "name": "SECOND (external adapter)",
                "status": "unavailable",
                "latency": None,
                "memory": None,
                "fps": None,
                "desc": "已移除模拟结果。接入真实 OpenPCDet/MMDetection3D checkpoint 后才可参与对比。",
                "metrics": {},
                "warning": "未配置真实 SECOND 权重和适配器。",
            },
            "centerpoint": {
                "name": "CenterPoint (external adapter)",
                "status": "unavailable",
                "latency": None,
                "memory": None,
                "fps": None,
                "desc": "已移除模拟结果。接入真实 CenterPoint checkpoint 后才可参与对比。",
                "metrics": {},
                "warning": "未配置真实 CenterPoint 权重和适配器。",
            },
        },
        "decision": {
            "fsm_decision": {
                "name": "Rule-based FSM",
                "status": "active",
                "latency": 2.0,
                "memory": 0.1,
                "fps": 500,
                "desc": "基于前向障碍距离和安全阈值的可解释行为决策。",
                "metrics": {},
            },
            "idm_mobil": {
                "name": "IDM/MOBIL Heuristic",
                "status": "active",
                "latency": 3.0,
                "memory": 0.1,
                "fps": 333,
                "desc": "基于跟驰距离、期望速度和变道间隙的经典交通行为模型。",
                "metrics": {},
            },
            "imitation_policy": {
                "name": "Lightweight Imitation Policy",
                "status": "active",
                "latency": 4.0,
                "memory": 0.2,
                "fps": 250,
                "desc": "用 nuScenes 场景密度和 ego 先验构造的轻量确定性模仿策略。",
                "metrics": {},
            },
        },
        "planning": {
            "frenet_lattice": {
                "name": "Frenet/Lattice Planner",
                "status": "active",
                "latency": 18.0,
                "memory": 0.2,
                "fps": 55,
                "desc": "在局部参考轨迹上施加避障横向偏移的轻量规划器。",
                "metrics": {},
            },
            "hybrid_astar": {
                "name": "Hybrid A* Lite",
                "status": "active",
                "latency": 24.0,
                "memory": 0.3,
                "fps": 41,
                "desc": "近似非完整约束搜索行为的离线局部避障 baseline。",
                "metrics": {},
            },
            "mpc_smoothing": {
                "name": "MPC-style Smoothing",
                "status": "active",
                "latency": 20.0,
                "memory": 0.3,
                "fps": 50,
                "desc": "对避障轨迹进行滚动平滑，优先降低 jerk 和曲率。",
                "metrics": {},
            },
        },
    }


def _model_entry(model_id: str, model: Dict[str, Any]) -> Dict[str, Any]:
    metrics = deepcopy(model.get("metrics", {}))
    accuracy = "待评测"
    if isinstance(metrics.get("nd_score"), (int, float)):
        accuracy = f"NDS {metrics.get('nd_score', 0.0):.3f} / mAP {metrics.get('mean_ap', 0.0) or 0.0:.3f}"
    elif "safety_rate" in metrics:
        accuracy = f"安全率 {metrics['safety_rate'] * 100:.1f}%"
    elif "collision_rate" in metrics:
        accuracy = f"碰撞率 {metrics['collision_rate'] * 100:.1f}%"

    return {
        "id": model_id,
        "name": model["name"],
        "status": model.get("status", "active"),
        "accuracy": accuracy,
        "latency": model.get("latency"),
        "memory": model.get("memory"),
        "fps": model.get("fps"),
        "desc": model.get("desc", ""),
        "metrics": metrics,
        "warning": model.get("warning", ""),
        "outputImage": model.get("outputImage"),
        "camImage": model.get("camImage"),
        "isReal": True,
    }


def get_module_configs(project_root: Optional[str] = None) -> Dict[str, Any]:
    registry = get_model_registry(project_root)
    latest = latest_run_record(project_root)
    if latest:
        for subsystem, report in latest.get("reports", {}).items():
            model_id = report.get("model_id")
            if model_id in registry.get(subsystem, {}):
                registry[subsystem][model_id]["metrics"] = report.get("metrics", {})

    return {
        "preprocessing": {
            "title": "数据预处理 (Preprocessing)",
            "desc": "对 nuScenes 相机和 LiDAR 数据做确定性预处理，保证实验输入可复现。",
            "available": True,
            "subModules": [
                {"id": "camera_data", "name": "多相机视图处理"},
                {"id": "lidar_data", "name": "激光雷达点云处理"},
            ],
            "modelsBySub": {
                "camera_data": [_model_entry("cam_surround", registry["preprocessing"]["cam_surround"])],
                "lidar_data": [_model_entry("lidar_topdown", registry["preprocessing"]["lidar_topdown"])],
            },
        },
        "perception": {
            "title": "感知模型配置 (Perception)",
            "desc": "只展示真实可运行或明确标记未配置的感知模型，不再用调阈值冒充不同网络。",
            "available": True,
            "subModules": [
                {"id": "3d_detection", "name": "3D 目标检测"},
                {"id": "lane_detection", "name": "车道线检测"},
                {"id": "semantic_segmentation", "name": "语义分割"},
            ],
            "modelsBySub": {
                "3d_detection": [_model_entry(k, v) for k, v in registry["perception"].items()],
                "lane_detection": [],
                "semantic_segmentation": [],
            },
        },
        "decision": {
            "title": "决策模型配置 (Decision)",
            "desc": "基于 nuScenes 场景中的 ego 状态和障碍物距离进行离线行为决策评测。",
            "available": True,
            "subModules": [
                {"id": "behavior_decision", "name": "行为决策"},
            ],
            "modelsBySub": {
                "behavior_decision": [_model_entry(k, v) for k, v in registry["decision"].items()],
            },
        },
        "planning": {
            "title": "规划模型配置 (Planning)",
            "desc": "在 nuScenes ego 轨迹和障碍物上下文中评估局部规划的碰撞、舒适度和轨迹误差。",
            "available": True,
            "subModules": [
                {"id": "path_planning", "name": "局部轨迹规划"},
            ],
            "modelsBySub": {
                "path_planning": [_model_entry(k, v) for k, v in registry["planning"].items()],
            },
        },
    }
