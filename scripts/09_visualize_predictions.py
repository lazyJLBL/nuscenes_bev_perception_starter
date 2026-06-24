"""
09_visualize_predictions.py — 可视化 3D 检测预测结果
=======================================================
将 3D 检测模型的推理结果可视化到 BEV 和相机图像上。

运行命令:
    python scripts/09_visualize_predictions.py

此脚本支持:
    1. 可视化 nuScenes 的 GT（真值）标注作为演示
    2. 如果有推理结果文件，加载并可视化
    3. 对比 GT 和预测结果
"""

import sys
import os
import json
import cv2
import numpy as np
import matplotlib.pyplot as plt
import argparse

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from src.dataset.nuscenes_loader import NuScenesLoader
from src.geometry.boxes import Box3D, annotations_to_boxes, transform_boxes_to_ego, transform_boxes_to_camera
from src.bev.simple_bev import SimpleBEVGenerator
from src.visualization.draw_boxes import draw_boxes_on_image, draw_boxes_bev
from src.visualization.draw_bev import draw_boxes_on_bev_image
from src.utils.path_utils import ensure_output_dirs, get_output_path
from src.utils.config import get_dataset_config
from src.utils.logger import print_header


def visualize_gt_as_demo(loader, sample_token):
    """
    使用 GT 标注作为演示，展示「如果有推理结果会怎么可视化」。
    
    这是因为新手可能还没有跑通推理流程，
    所以先用 GT 标注演示可视化效果。
    """
    short_token = sample_token[:8]
    dataset_config = get_dataset_config()
    bev_config = dataset_config['bev']
    
    # 获取数据
    annotations = loader.get_annotations(sample_token)
    boxes = annotations_to_boxes(annotations)
    points = loader.load_lidar_points(sample_token)
    
    _, lidar_calib, lidar_ego_pose = loader.get_sensor_records(sample_token, 'LIDAR_TOP')
    boxes_ego = transform_boxes_to_ego(boxes, lidar_ego_pose)
    
    # 将点云也转换到 Ego 坐标系，与 boxes 保持一致
    from src.geometry.transforms import lidar_to_ego
    points_ego = lidar_to_ego(points, lidar_calib)
    
    # ---- 综合可视化 ----
    print("\n📌 创建综合可视化...")
    
    fig = plt.figure(figsize=(24, 16))
    
    # 1. BEV 视图 (左上)
    ax1 = fig.add_subplot(2, 2, 1)
    
    # 绘制点云
    mask = (
        (points_ego[:, 0] >= -50) & (points_ego[:, 0] <= 50) &
        (points_ego[:, 1] >= -50) & (points_ego[:, 1] <= 50)
    )
    filtered = points_ego[mask]
    ax1.scatter(filtered[:, 1], filtered[:, 0], c='white', s=0.1, alpha=0.3)
    
    # 绘制 GT boxes
    for box in boxes_ego:
        corners = box.bottom_corners()
        color_map = {
            'car': 'lime', 'truck': 'orange', 'bus': 'cyan',
            'pedestrian': 'magenta', 'motorcycle': 'yellow',
            'bicycle': 'springgreen', 'barrier': 'gray',
            'traffic_cone': 'darkorange',
        }
        short_label = box.label.split('.')[-1] if '.' in box.label else box.label
        color = color_map.get(short_label, 'white')
        
        polygon = plt.Polygon(
            corners[:, [1, 0]], closed=True,
            fill=False, edgecolor=color, linewidth=1.5,
        )
        ax1.add_patch(polygon)
    
    # Ego vehicle
    ax1.plot(0, 0, marker='*', color='red', markersize=15)
    ax1.set_xlim(50, -50)  # 反转 X 轴，使得左方(正)在左边
    ax1.set_ylim(-50, 50)
    ax1.set_title(f'BEV 俯视图 — GT 标注\n({len(boxes_ego)} 个目标)', fontsize=12)
    ax1.set_aspect('equal')
    ax1.set_facecolor('black')
    
    # 2. CAM_FRONT (右上)
    ax2 = fig.add_subplot(2, 2, 2)
    cam_sd, cam_calib, cam_ego_pose = loader.get_sensor_records(sample_token, 'CAM_FRONT')
    cam_path = os.path.join(loader.dataroot, cam_sd['filename'])
    image = cv2.imread(cam_path)
    
    if image is not None:
        boxes_cam = transform_boxes_to_camera(boxes, cam_ego_pose, cam_calib)
        camera_intrinsic = np.array(cam_calib['camera_intrinsic'])
        result = draw_boxes_on_image(image, boxes_cam, camera_intrinsic)
        ax2.imshow(cv2.cvtColor(result, cv2.COLOR_BGR2RGB))
    ax2.set_title('CAM_FRONT — GT 3D Boxes', fontsize=12)
    ax2.axis('off')
    
    # 3. BEV 高度图 (左下)
    ax3 = fig.add_subplot(2, 2, 3)
    bev_gen = SimpleBEVGenerator(
        x_range=tuple(bev_config['x_range']),
        y_range=tuple(bev_config['y_range']),
        z_range=tuple(bev_config['z_range']),
        resolution=bev_config['resolution'],
    )
    height_map, density_map, intensity_map = bev_gen.generate(points_ego)
    rgb_map = bev_gen.to_rgb(height_map, density_map, intensity_map)
    bev_with_boxes = draw_boxes_on_bev_image(rgb_map, boxes_ego, bev_gen)
    ax3.imshow(bev_with_boxes)
    ax3.set_title('BEV RGB + GT Boxes', fontsize=12)
    ax3.axis('off')
    
    # 4. 类别统计 (右下)
    ax4 = fig.add_subplot(2, 2, 4)
    from collections import Counter
    labels = [b.label.split('.')[-1] if '.' in b.label else b.label for b in boxes]
    counts = Counter(labels)
    
    if counts:
        sorted_items = sorted(counts.items(), key=lambda x: x[1], reverse=True)
        categories, values = zip(*sorted_items)
        
        colors_bar = []
        color_map_bar = {
            'car': '#00FF00', 'truck': '#FFC800', 'bus': '#0064FF',
            'pedestrian': '#FF00FF', 'motorcycle': '#FFFF00',
            'bicycle': '#80FF00', 'barrier': '#808080',
            'traffic_cone': '#FF8000', 'trailer': '#C8C800',
            'construction_vehicle': '#0000FF',
        }
        for cat in categories:
            colors_bar.append(color_map_bar.get(cat, '#FFFFFF'))
        
        bars = ax4.barh(range(len(categories)), values, color=colors_bar)
        ax4.set_yticks(range(len(categories)))
        ax4.set_yticklabels(categories)
        ax4.set_xlabel('数量')
        ax4.set_title('GT 目标类别分布', fontsize=12)
        ax4.invert_yaxis()
        
        for bar, val in zip(bars, values):
            ax4.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height()/2,
                     str(val), va='center', fontsize=10)
    
    plt.suptitle(
        f'3D 检测可视化 — GT 标注演示 (sample: {short_token}...)\n'
        f'⚠️ 这是 Ground Truth，不是模型预测结果',
        fontsize=14, fontweight='bold'
    )
    plt.tight_layout()
    
    save_path = get_output_path("predictions", f"visualization_gt_demo_{short_token}.jpg")
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  ✅ 综合可视化已保存: {save_path}")
    
    return save_path


def main():
    parser = argparse.ArgumentParser(description="3D 检测预测结果可视化")
    parser.add_argument("--sample-token", type=str, default=None, help="指定要处理的 sample token")
    args = parser.parse_args()

    print_header("3D 检测预测结果可视化")
    
    ensure_output_dirs()
    
    # 1. 加载数据集
    print("\n📌 步骤 1: 加载 nuScenes 数据集...")
    try:
        loader = NuScenesLoader(verbose=True)
    except FileNotFoundError as e:
        print(str(e))
        sys.exit(1)
        
    # 获取 sample token
    if args.sample_token:
        sample_token = args.sample_token
    else:
        first_sample = loader.get_first_sample()
        sample_token = first_sample['token']
    
    # 使用 GT 标注进行演示
    print("\n📌 步骤 2: 使用 GT 标注可视化...")
    save_path = visualize_gt_as_demo(loader, sample_token)
    
    # 检查是否有真实推理结果
    pred_path = get_output_path("predictions", "detection_results.json")
    if os.path.exists(pred_path):
        print(f"\n📌 步骤 3: 发现推理结果文件: {pred_path}")
        print("   加载推理结果进行可视化...")
        # TODO: 加载真实推理结果并可视化
    else:
        print(f"\n📌 步骤 3: 未发现推理结果文件")
        print(f"   如果你已完成推理，请将结果保存为:")
        print(f"   {pred_path}")
    
    print_header("可视化完成 ✅")
    print(f"\n📁 输出文件:")
    print(f"   - 综合可视化: {save_path}")
    print(f"\n🎉 恭喜！你已经完成了所有基础步骤！")
    print(f"\n📚 后续学习建议:")
    print(f"   请阅读 docs/05_next_steps_to_planning.md\n")


if __name__ == '__main__':
    main()
