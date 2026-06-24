"""
09_visualize_predictions.py — 可视化 3D 检测预测结果
=======================================================
将 3D 检测模型的推理结果可视化到 BEV 和相机图像上。

运行命令:
    python scripts/09_visualize_predictions.py --prediction-file <path_to_json>
"""

import sys
import os
import json
import cv2
import numpy as np
import matplotlib.pyplot as plt
import argparse
from pyquaternion import Quaternion

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from src.dataset.nuscenes_loader import NuScenesLoader
from src.geometry.boxes import Box3D, annotations_to_boxes, transform_boxes_to_ego, transform_boxes_to_camera
from src.bev.simple_bev import SimpleBEVGenerator
from src.visualization.draw_boxes import draw_boxes_on_image
from src.visualization.draw_bev import draw_boxes_on_bev_image
from src.utils.path_utils import ensure_output_dirs, get_output_path
from src.utils.config import get_dataset_config, get_model_config
from src.utils.logger import print_header

def json_to_boxes(preds: list) -> list[Box3D]:
    """Convert nuScenes prediction dicts to Box3D objects."""
    boxes = []
    for pred in preds:
        box = Box3D(
            center=pred["translation"],
            size=pred["size"],
            orientation=Quaternion(pred["rotation"]),
            label=pred["detection_name"],
            score=pred["detection_score"]
        )
        boxes.append(box)
    return boxes

def visualize_pred_vs_gt(loader, sample_token, pred_boxes_global):
    """
    Visualize GT vs Prediction.
    """
    short_token = sample_token[:8]
    dataset_config = get_dataset_config()
    bev_config = dataset_config['bev']
    
    # 1. 获取 GT
    gt_annotations = loader.get_annotations(sample_token)
    gt_boxes = annotations_to_boxes(gt_annotations)
    
    # 2. 获取传感器和点云数据
    points = loader.load_lidar_points(sample_token)
    _, lidar_calib, lidar_ego_pose = loader.get_sensor_records(sample_token, 'LIDAR_TOP')
    cam_sd, cam_calib, cam_ego_pose = loader.get_sensor_records(sample_token, 'CAM_FRONT')
    
    # 3. 转换到 Ego 坐标系 (用于 BEV)
    from src.geometry.transforms import lidar_to_ego
    points_ego = lidar_to_ego(points, lidar_calib)
    gt_boxes_ego = transform_boxes_to_ego(gt_boxes, lidar_ego_pose)
    pred_boxes_ego = transform_boxes_to_ego(pred_boxes_global, lidar_ego_pose)
    
    # 4. 转换到 Camera 坐标系 (用于前视图)
    gt_boxes_cam = transform_boxes_to_camera(gt_boxes, cam_ego_pose, cam_calib)
    # pred_boxes 是 global 的，简单起见，我们暂不在 CAM_FRONT 画 pred，只画在 BEV 上。
    
    # 我们用一个简化的方式在 CAM 上画:
    # 我们可以把 pred_boxes_ego (基于 lidar ego) 转成基于 cam_front 视角的 box
    # 但严格来说，需要 nusc 的 map 工具，这里我们仅在 BEV 展示对比，CAM 展示 GT。

    print("\n📌 创建对比可视化...")
    
    fig = plt.figure(figsize=(24, 12))
    
    # BEV 视图
    ax1 = fig.add_subplot(1, 2, 1)
    
    # 绘制点云
    mask = (
        (points_ego[:, 0] >= -50) & (points_ego[:, 0] <= 50) &
        (points_ego[:, 1] >= -50) & (points_ego[:, 1] <= 50)
    )
    filtered = points_ego[mask]
    ax1.scatter(filtered[:, 1], filtered[:, 0], c='gray', s=0.1, alpha=0.5)
    
    # 绘制 GT boxes (绿色)
    for box in gt_boxes_ego:
        corners = box.bottom_corners()
        polygon = plt.Polygon(
            corners[:, [1, 0]], closed=True,
            fill=False, edgecolor='lime', linewidth=1.5,
        )
        ax1.add_patch(polygon)
        
    # 绘制 Pred boxes (红色)
    for box in pred_boxes_ego:
        corners = box.bottom_corners()
        polygon = plt.Polygon(
            corners[:, [1, 0]], closed=True,
            fill=False, edgecolor='red', linewidth=1.5, linestyle='--'
        )
        ax1.add_patch(polygon)
    
    # Ego vehicle
    ax1.plot(0, 0, marker='*', color='blue', markersize=15)
    ax1.set_xlim(50, -50)  # 反转 X 轴
    ax1.set_ylim(-50, 50)
    ax1.set_title(f'BEV 俯视图: GT (绿色) vs Pred (红色)\n(sample: {short_token})', fontsize=14)
    ax1.set_aspect('equal')
    ax1.set_facecolor('black')
    
    # 类别统计对比
    ax2 = fig.add_subplot(1, 2, 2)
    
    from collections import Counter
    gt_labels = [b.label.split('.')[-1] if '.' in b.label else b.label for b in gt_boxes]
    pred_labels = [b.label for b in pred_boxes_global]
    
    gt_counts = Counter(gt_labels)
    pred_counts = Counter(pred_labels)
    
    all_cats = list(set(list(gt_counts.keys()) + list(pred_counts.keys())))
    gt_vals = [gt_counts.get(c, 0) for c in all_cats]
    pred_vals = [pred_counts.get(c, 0) for c in all_cats]
    
    x = np.arange(len(all_cats))
    width = 0.35
    
    ax2.bar(x - width/2, gt_vals, width, label='GT', color='lime')
    ax2.bar(x + width/2, pred_vals, width, label='Prediction', color='red')
    
    ax2.set_ylabel('数量')
    ax2.set_title('目标类别统计: GT vs Prediction')
    ax2.set_xticks(x)
    ax2.set_xticklabels(all_cats, rotation=45)
    ax2.legend()
    
    plt.tight_layout()
    
    save_path = get_output_path("predictions", f"pred_vs_gt_bev_{short_token}.jpg")
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  ✅ 对比可视化已保存: {save_path}")

def main():
    parser = argparse.ArgumentParser(description="3D 检测预测结果可视化")
    parser.add_argument("--prediction-file", type=str, default=None, help="指定预测的 JSON 文件")
    parser.add_argument("--sample-token", type=str, default=None, help="指定要处理的 sample token")
    args = parser.parse_args()

    print_header("3D 检测预测结果可视化")
    
    ensure_output_dirs()
    
    model_cfg = get_model_config()
    det_cfg = model_cfg.get('detection', {})
    
    pred_file = args.prediction_file if args.prediction_file else os.path.join(PROJECT_ROOT, det_cfg.get('prediction_file', 'outputs/predictions/detection_results.json'))
    
    if not os.path.exists(pred_file):
        print(f"❌ 找不到预测文件: {pred_file}")
        print("请先运行: python scripts/08_inference_baseline.py --execute")
        return
        
    print(f"📌 加载预测结果: {pred_file}")
    with open(pred_file, "r") as f:
        predictions = json.load(f)
        
    results = predictions.get("results", {})
    if not results:
        print("❌ 预测文件格式不正确或为空！")
        return
        
    print("\n📌 加载 nuScenes 数据集 (用于获取点云和 GT)...")
    try:
        loader = NuScenesLoader(verbose=False)
    except FileNotFoundError as e:
        print(str(e))
        sys.exit(1)
        
    # 获取 sample token
    if args.sample_token:
        sample_token = args.sample_token
    else:
        # 找一个在预测结果里有的 token
        sample_token = list(results.keys())[0]
    
    if sample_token not in results:
        print(f"❌ 在预测文件中找不到 token: {sample_token}")
        return
        
    preds = results[sample_token]
    pred_boxes = json_to_boxes(preds)
    
    print(f"📌 {sample_token[:8]} 共有 {len(pred_boxes)} 个预测框。")
    visualize_pred_vs_gt(loader, sample_token, pred_boxes)
    
    print_header("可视化完成 ✅")

if __name__ == '__main__':
    main()
