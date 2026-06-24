"""
01_check_nuscenes_data.py — nuScenes 数据检查脚本
===================================================
运行此脚本验证 nuScenes mini 数据集已正确加载。

运行命令:
    python scripts/01_check_nuscenes_data.py

此脚本会:
    1. 加载 nuScenes mini 数据集
    2. 打印数据集基本信息（scene、sample、annotation 数量等）
    3. 打印第一个 scene 的信息
    4. 打印第一个 sample 的详细信息
    5. 打印该 sample 的传感器数据路径
    6. 打印该 sample 的前 5 个标注框
"""

import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from src.dataset.nuscenes_loader import NuScenesLoader
from src.dataset.nuscenes_info import (
    print_sample_info,
    print_scene_info,
    print_annotation_info,
    print_sensor_info,
)
from src.utils.logger import print_header


def main():
    print_header("nuScenes 数据检查")
    
    # ---- 1. 加载数据集 ----
    print("\n📌 步骤 1: 加载 nuScenes 数据集...")
    try:
        loader = NuScenesLoader(verbose=True)
    except FileNotFoundError as e:
        print(str(e))
        print("\n💡 提示: 请先下载 nuScenes mini 数据集。")
        print("   下载地址: https://www.nuscenes.org/nuscenes#download")
        print("   选择 'Mini' 版本（约 4GB）")
        sys.exit(1)
    
    # ---- 2. 打印数据集信息 ----
    print("\n📌 步骤 2: 数据集基本信息")
    loader.print_dataset_info()
    
    # ---- 3. 打印第一个 scene ----
    print("\n📌 步骤 3: 第一个 Scene 信息")
    print_scene_info(loader.nusc, scene_index=0)
    
    # ---- 4. 获取第一个 sample 并打印详细信息 ----
    print("\n📌 步骤 4: 第一个 Sample 详细信息")
    first_sample = loader.get_first_sample()
    sample_token = first_sample['token']
    print_sample_info(loader.nusc, sample_token)
    
    # ---- 5. 打印传感器数据路径 ----
    print("\n📌 步骤 5: 传感器数据路径")
    all_paths = loader.get_sample_data_paths(sample_token)
    print(f"\n   该 sample 共有 {len(all_paths)} 个传感器数据:")
    for sensor, path in all_paths.items():
        exists = "✅" if os.path.exists(path) else "❌"
        print(f"   {exists} {sensor:20s} -> {os.path.basename(path)}")
    
    # ---- 6. 摄像头图像路径 ----
    print("\n📌 步骤 6: 6 个环视摄像头图像路径")
    cam_paths = loader.get_camera_data(sample_token)
    for cam_name, cam_path in cam_paths.items():
        exists = "✅" if os.path.exists(cam_path) else "❌"
        print(f"   {exists} {cam_name:20s} -> {os.path.basename(cam_path)}")
    
    # ---- 7. LiDAR 数据 ----
    print("\n📌 步骤 7: LiDAR 点云数据")
    lidar_path = loader.get_lidar_data(sample_token)
    if os.path.exists(lidar_path):
        import numpy as np
        points = np.fromfile(lidar_path, dtype=np.float32).reshape(-1, 5)
        print(f"   ✅ LiDAR 文件: {os.path.basename(lidar_path)}")
        print(f"   点云数量:      {points.shape[0]}")
        print(f"   数据维度:      {points.shape[1]} (x, y, z, intensity, ring_index)")
        print(f"   X 范围:        [{points[:, 0].min():.1f}, {points[:, 0].max():.1f}] 米")
        print(f"   Y 范围:        [{points[:, 1].min():.1f}, {points[:, 1].max():.1f}] 米")
        print(f"   Z 范围:        [{points[:, 2].min():.1f}, {points[:, 2].max():.1f}] 米")
    else:
        print(f"   ❌ LiDAR 文件不存在: {lidar_path}")
    
    # ---- 8. 标注框信息 ----
    print("\n📌 步骤 8: 3D 标注框信息")
    annotations = loader.get_annotations(sample_token)
    print(f"\n   该 sample 共有 {len(annotations)} 个标注框:")
    
    # 只打印前 5 个
    for i, ann in enumerate(annotations[:5]):
        print(f"\n   标注框 {i+1}:")
        print_annotation_info(loader.nusc, ann)
    
    if len(annotations) > 5:
        print(f"\n   ... 还有 {len(annotations) - 5} 个标注框未显示")
    
    # ---- 9. 传感器详细信息 ----
    print("\n📌 步骤 9: 传感器信息链 (以 CAM_FRONT 和 LIDAR_TOP 为例)")
    print_sensor_info(loader.nusc, sample_token, 'CAM_FRONT')
    print_sensor_info(loader.nusc, sample_token, 'LIDAR_TOP')
    
    # ---- 10. 完整 sample detail ----
    print("\n📌 步骤 10: Sample 完整摘要")
    detail = loader.get_sample_detail(sample_token)
    print(f"   摄像头 tokens: {len(detail['camera_tokens'])} 个")
    print(f"   LiDAR token:   {detail['lidar_token']}")
    print(f"   Ego poses:     {len(detail['ego_poses'])} 个传感器的位姿")
    print(f"   标定信息:      {len(detail['calibrated_sensors'])} 个传感器的标定")
    print(f"   标注框数:      {detail['annotation_count']}")
    
    print_header("数据检查完成 ✅")
    print("\n下一步: 运行 python scripts/02_visualize_samples.py 可视化样本\n")


if __name__ == '__main__':
    main()
