"""
02_visualize_samples.py — 样本可视化脚本
==========================================
可视化 nuScenes 样本的 6 个环视摄像头图像和 LiDAR 点云俯视图。

运行命令:
    python scripts/02_visualize_samples.py

输出:
    outputs/images/sample_cameras_<token>.jpg  — 6 个环视摄像头图像
    outputs/images/sample_lidar_topdown_<token>.jpg — LiDAR 俯视图
"""

import sys
import os
import argparse

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from src.dataset.nuscenes_loader import NuScenesLoader
from src.visualization.draw_camera import visualize_cameras
from src.visualization.draw_lidar import visualize_lidar_topdown, visualize_lidar_3views
from src.utils.path_utils import ensure_output_dirs, get_output_path
from src.utils.logger import print_header


def main():
    parser = argparse.ArgumentParser(description="nuScenes 样本可视化")
    parser.add_argument("--sample-token", type=str, default=None, help="指定要可视化的 sample token")
    args = parser.parse_args()

    print_header("nuScenes 样本可视化")
    
    # 创建输出目录
    ensure_output_dirs()
    
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
    
    short_token = sample_token[:8]  # 取前 8 位作为文件名后缀
    
    print(f"\n   使用 sample token: {sample_token}")
    
    # ---- 可视化 6 个环视摄像头 ----
    print("\n📌 步骤 2: 可视化 6 个环视摄像头图像...")
    camera_paths = loader.get_camera_data(sample_token)
    
    save_path = get_output_path("images", f"sample_cameras_{short_token}.jpg")
    visualize_cameras(
        camera_paths=camera_paths,
        save_path=save_path,
        show=False,
        title=f"nuScenes 6 环视摄像头 (sample: {short_token}...)",
    )
    
    # ---- 可视化 LiDAR 俯视图 ----
    print("\n📌 步骤 3: 可视化 LiDAR 点云俯视图...")
    points = loader.load_lidar_points(sample_token)
    print(f"   加载了 {points.shape[0]} 个 LiDAR 点")
    
    # 按高度着色的俯视图
    save_path = get_output_path("images", f"sample_lidar_topdown_{short_token}.jpg")
    visualize_lidar_topdown(
        points=points,
        save_path=save_path,
        show=False,
        title=f"LiDAR 俯视图 — 按高度着色 (sample: {short_token}...)",
        color_by='height',
    )
    
    # 按强度着色的俯视图
    save_path_intensity = get_output_path("images", f"sample_lidar_intensity_{short_token}.jpg")
    visualize_lidar_topdown(
        points=points,
        save_path=save_path_intensity,
        show=False,
        title=f"LiDAR 俯视图 — 按反射强度着色 (sample: {short_token}...)",
        color_by='intensity',
    )
    
    # 三视图
    save_path_3view = get_output_path("images", f"sample_lidar_3views_{short_token}.jpg")
    visualize_lidar_3views(
        points=points,
        save_path=save_path_3view,
        show=False,
    )
    
    print_header("样本可视化完成 ✅")
    print("\n📁 输出文件:")
    print(f"   - 摄像头图像: outputs/images/sample_cameras_{short_token}.jpg")
    print(f"   - LiDAR 高度图: outputs/images/sample_lidar_topdown_{short_token}.jpg")
    print(f"   - LiDAR 强度图: outputs/images/sample_lidar_intensity_{short_token}.jpg")
    print(f"   - LiDAR 三视图: outputs/images/sample_lidar_3views_{short_token}.jpg")
    print(f"\n下一步: 运行 python scripts/03_project_lidar_to_camera.py\n")


if __name__ == '__main__':
    main()
