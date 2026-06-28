"""
03_project_lidar_to_camera.py — LiDAR 投影到相机脚本
======================================================
将 LiDAR 点云投影到 CAM_FRONT 等相机图像上。

运行命令:
    python scripts/03_project_lidar_to_camera.py

输出:
    outputs/projections/lidar_to_cam_front_<token>.jpg
    outputs/projections/lidar_to_all_cams_<token>.jpg
"""

import sys
import os
import cv2
import argparse

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from src.dataset.nuscenes_loader import NuScenesLoader
from src.geometry.projection import (
    project_lidar_to_camera_image,
    visualize_lidar_projection,
    draw_lidar_on_image,
)
from src.utils.path_utils import ensure_output_dirs, get_output_path
from src.utils.config import get_dataset_config
from src.utils.logger import print_header
from src.utils.plotting import configure_matplotlib_chinese

import numpy as np
import matplotlib.pyplot as plt

configure_matplotlib_chinese()


def main():
    parser = argparse.ArgumentParser(description="LiDAR 投影到相机图像")
    parser.add_argument("--sample-token", type=str, default=None, help="指定要处理的 sample token")
    args = parser.parse_args()

    print_header("LiDAR 投影到相机图像")
    
    ensure_output_dirs()
    dataset_config = get_dataset_config()
    
    # 加载数据集
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
        
    short_token = sample_token[:8]
    
    print(f"   使用 sample token: {sample_token}")
    
    # 加载 LiDAR 点云
    print("\n📌 步骤 2: 加载 LiDAR 点云...")
    points = loader.load_lidar_points(sample_token)
    print(f"   加载了 {points.shape[0]} 个 LiDAR 点")
    
    # 获取 LiDAR 传感器记录
    lidar_sd, lidar_calib, lidar_ego_pose = loader.get_sensor_records(
        sample_token, 'LIDAR_TOP'
    )
    
    # ---- 投影到 CAM_FRONT ----
    print("\n📌 步骤 3: 投影 LiDAR 到 CAM_FRONT...")
    cam_sd, cam_calib, cam_ego_pose = loader.get_sensor_records(
        sample_token, 'CAM_FRONT'
    )
    
    # 读取相机图像
    cam_path = os.path.join(loader.dataroot, cam_sd['filename'])
    image = cv2.imread(cam_path)
    
    if image is None:
        print(f"  ❌ 无法读取图像: {cam_path}")
        sys.exit(1)
    
    img_h, img_w = image.shape[:2]
    print(f"   图像尺寸: {img_w} x {img_h}")
    
    # 执行投影
    pixel_coords, depths = project_lidar_to_camera_image(
        points=points,
        lidar_calib=lidar_calib,
        lidar_ego_pose=lidar_ego_pose,
        camera_calib=cam_calib,
        camera_ego_pose=cam_ego_pose,
        image_shape=(img_h, img_w),
    )
    
    print(f"   投影到图像上的点数: {len(pixel_coords)}")
    if len(depths) > 0:
        print(f"   深度范围: [{depths.min():.1f}, {depths.max():.1f}] 米")
    
    # 保存结果
    save_path = get_output_path("projections", f"lidar_to_cam_front_{short_token}.jpg")
    visualize_lidar_projection(
        image=image,
        pixel_coords=pixel_coords,
        depths=depths,
        save_path=save_path,
        title=f"LiDAR → CAM_FRONT (sample: {short_token}...)",
    )
    
    # ---- 投影到所有 6 个摄像头 ----
    print("\n📌 步骤 4: 投影 LiDAR 到所有 6 个摄像头...")
    
    camera_channels = dataset_config['camera_channels']
    fig, axes = plt.subplots(2, 3, figsize=(24, 10))
    
    layout = [
        ['CAM_FRONT_LEFT', 'CAM_FRONT', 'CAM_FRONT_RIGHT'],
        ['CAM_BACK_LEFT',  'CAM_BACK',  'CAM_BACK_RIGHT'],
    ]
    
    for row_idx, row_cams in enumerate(layout):
        for col_idx, cam_name in enumerate(row_cams):
            ax = axes[row_idx][col_idx]
            
            # 获取传感器记录
            cam_sd_i, cam_calib_i, cam_ego_pose_i = loader.get_sensor_records(
                sample_token, cam_name
            )
            
            # 读取图像
            cam_path_i = os.path.join(loader.dataroot, cam_sd_i['filename'])
            img_i = cv2.imread(cam_path_i)
            
            if img_i is None:
                ax.set_title(f'{cam_name}\n(图像读取失败)')
                ax.axis('off')
                continue
            
            img_h_i, img_w_i = img_i.shape[:2]
            
            # 投影
            px, dp = project_lidar_to_camera_image(
                points=points,
                lidar_calib=lidar_calib,
                lidar_ego_pose=lidar_ego_pose,
                camera_calib=cam_calib_i,
                camera_ego_pose=cam_ego_pose_i,
                image_shape=(img_h_i, img_w_i),
            )
            
            # 绘制
            result_i = draw_lidar_on_image(img_i, px, dp)
            ax.imshow(cv2.cvtColor(result_i, cv2.COLOR_BGR2RGB))
            ax.set_title(f'{cam_name} ({len(px)} 个点)', fontsize=11)
            ax.axis('off')
    
    plt.suptitle(f'LiDAR 投影到 6 个环视摄像头 (sample: {short_token}...)',
                 fontsize=15, fontweight='bold')
    plt.tight_layout()
    
    save_all = get_output_path("projections", f"lidar_to_all_cams_{short_token}.jpg")
    plt.savefig(save_all, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  ✅ 6 摄像头投影图已保存: {save_all}")
    
    print_header("LiDAR 投影完成 ✅")
    print(f"\n📁 输出文件:")
    print(f"   - CAM_FRONT 投影: outputs/projections/lidar_to_cam_front_{short_token}.jpg")
    print(f"   - 全部摄像头投影: outputs/projections/lidar_to_all_cams_{short_token}.jpg")
    print(f"\n下一步: 运行 python scripts/04_visualize_3d_boxes.py\n")


if __name__ == '__main__':
    main()
