"""
05_generate_simple_bev.py — 简单 BEV 生成脚本
=================================================
从 LiDAR 点云生成 BEV（鸟瞰图），并叠加 3D 标注框。

运行命令:
    python scripts/05_generate_simple_bev.py

输出:
    outputs/bev/simple_bev_channels_<token>.jpg — BEV 三通道可视化
    outputs/bev/simple_bev_<token>.jpg          — BEV RGB 合成图
    outputs/bev/simple_bev_boxes_<token>.jpg    — BEV + 3D boxes
"""

import sys
import os
import cv2

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from src.dataset.nuscenes_loader import NuScenesLoader
from src.bev.simple_bev import SimpleBEVGenerator
from src.geometry.boxes import annotations_to_boxes, transform_boxes_to_ego
from src.visualization.draw_bev import visualize_bev_channels, draw_boxes_on_bev_image
from src.utils.path_utils import ensure_output_dirs, get_output_path
from src.utils.config import get_dataset_config
from src.utils.logger import print_header

import numpy as np
import matplotlib.pyplot as plt


def main():
    print_header("简单 BEV 生成")
    
    ensure_output_dirs()
    dataset_config = get_dataset_config()
    bev_config = dataset_config['bev']
    
    # 加载数据集
    print("\n📌 步骤 1: 加载 nuScenes 数据集...")
    try:
        loader = NuScenesLoader(verbose=True)
    except FileNotFoundError as e:
        print(str(e))
        sys.exit(1)
    
    # 获取第一个 sample
    first_sample = loader.get_first_sample()
    sample_token = first_sample['token']
    short_token = sample_token[:8]
    
    # 加载 LiDAR 点云
    print("\n📌 步骤 2: 加载 LiDAR 点云...")
    points = loader.load_lidar_points(sample_token)
    print(f"   加载了 {points.shape[0]} 个 LiDAR 点")
    
    # 获取传感器数据
    _, lidar_calib, lidar_ego_pose = loader.get_sensor_records(sample_token, 'LIDAR_TOP')
    
    # 转换点云到 Ego 坐标系（为了与 Ego 坐标系下的 boxes 匹配）
    from src.geometry.transforms import lidar_to_ego
    points_ego = lidar_to_ego(points, lidar_calib)
    
    # 创建 BEV 生成器
    print("\n📌 步骤 3: 创建 BEV 生成器...")
    bev_gen = SimpleBEVGenerator(
        x_range=tuple(bev_config['x_range']),
        y_range=tuple(bev_config['y_range']),
        z_range=tuple(bev_config['z_range']),
        resolution=bev_config['resolution'],
    )
    
    # 生成 BEV 三通道
    print("\n📌 步骤 4: 生成 BEV 三通道...")
    height_map, density_map, intensity_map = bev_gen.generate(points_ego)
    
    print(f"   高度图 — 范围: [{height_map.min():.2f}, {height_map.max():.2f}]")
    print(f"   密度图 — 最大点数: {density_map.max():.0f}")
    print(f"   强度图 — 范围: [{intensity_map.min():.2f}, {intensity_map.max():.2f}]")
    
    # 合成 RGB
    rgb_map = bev_gen.to_rgb(height_map, density_map, intensity_map)
    
    # 可视化三通道
    save_channels = get_output_path("bev", f"simple_bev_channels_{short_token}.jpg")
    visualize_bev_channels(
        height_map, density_map, intensity_map, rgb_map,
        save_path=save_channels,
        title=f"BEV 三通道可视化 (sample: {short_token}...)",
    )
    
    # 保存 RGB BEV
    save_rgb = get_output_path("bev", f"simple_bev_{short_token}.jpg")
    fig, ax = plt.subplots(1, 1, figsize=(10, 10))
    ax.imshow(rgb_map)
    ax.set_title(f'BEV RGB 合成图 (sample: {short_token}...)', fontsize=14)
    ax.axis('off')
    plt.tight_layout()
    plt.savefig(save_rgb, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  ✅ BEV RGB 图已保存: {save_rgb}")
    
    # ---- 叠加 3D boxes ----
    print("\n📌 步骤 5: 在 BEV 上叠加 3D boxes...")
    
    # 获取标注框
    annotations = loader.get_annotations(sample_token)
    boxes = annotations_to_boxes(annotations)
    
    # 转换到 Ego 坐标系
    _, _, lidar_ego_pose = loader.get_sensor_records(sample_token, 'LIDAR_TOP')
    boxes_ego = transform_boxes_to_ego(boxes, lidar_ego_pose)
    
    # 在 BEV 上绘制 boxes
    bev_with_boxes = draw_boxes_on_bev_image(rgb_map, boxes_ego, bev_gen)
    
    save_boxes = get_output_path("bev", f"simple_bev_boxes_{short_token}.jpg")
    fig, axes = plt.subplots(1, 2, figsize=(20, 10))
    
    axes[0].imshow(rgb_map)
    axes[0].set_title('BEV RGB（无标注）', fontsize=13)
    axes[0].axis('off')
    
    axes[1].imshow(bev_with_boxes)
    axes[1].set_title(f'BEV + 3D Boxes ({len(boxes_ego)} 个)', fontsize=13)
    axes[1].axis('off')
    
    plt.suptitle(f'BEV 鸟瞰图 (sample: {short_token}...)', fontsize=15, fontweight='bold')
    plt.tight_layout()
    plt.savefig(save_boxes, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  ✅ BEV + Boxes 图已保存: {save_boxes}")
    
    print_header("BEV 生成完成 ✅")
    print(f"\n📁 输出文件:")
    print(f"   - BEV 三通道: outputs/bev/simple_bev_channels_{short_token}.jpg")
    print(f"   - BEV RGB:    outputs/bev/simple_bev_{short_token}.jpg")
    print(f"   - BEV+Boxes:  outputs/bev/simple_bev_boxes_{short_token}.jpg")
    print(f"\n下一步: 运行 python scripts/06_prepare_detection_baseline.py\n")


if __name__ == '__main__':
    main()
