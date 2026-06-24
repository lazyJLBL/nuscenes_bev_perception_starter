"""
04_visualize_3d_boxes.py — 3D Box 可视化脚本
===============================================
在 BEV 俯视图和相机图像中绘制 3D 标注框。

运行命令:
    python scripts/04_visualize_3d_boxes.py

输出:
    outputs/bev/boxes_bev_<token>.jpg        — BEV 俯视图中的 3D boxes
    outputs/images/boxes_cam_front_<token>.jpg — CAM_FRONT 图像中的 3D boxes
"""

import sys
import os
import cv2
import numpy as np

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from src.dataset.nuscenes_loader import NuScenesLoader
from src.geometry.boxes import Box3D, annotations_to_boxes, transform_boxes_to_ego, transform_boxes_to_camera
from src.visualization.draw_boxes import draw_boxes_on_image, draw_boxes_bev
from src.utils.path_utils import ensure_output_dirs, get_output_path
from src.utils.logger import print_header


def main():
    print_header("3D Box 可视化")
    
    ensure_output_dirs()
    
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
    
    # 获取标注框
    print("\n📌 步骤 2: 获取 3D 标注框...")
    annotations = loader.get_annotations(sample_token)
    boxes = annotations_to_boxes(annotations)
    print(f"   共 {len(boxes)} 个标注框")
    
    # 打印类别统计
    from collections import Counter
    labels = [b.label.split('.')[-1] for b in boxes]
    label_counts = Counter(labels)
    print(f"   类别分布:")
    for label, count in label_counts.most_common():
        print(f"     {label}: {count}")
    
    # ---- BEV 可视化 (Ego 坐标系) ----
    print("\n📌 步骤 3: BEV 俯视图中绘制 3D boxes...")
    
    # 获取 LiDAR 的 ego_pose（用于将 global boxes 转换到 ego 坐标系）
    _, lidar_calib, lidar_ego_pose = loader.get_sensor_records(sample_token, 'LIDAR_TOP')
    
    # 将 boxes 从 Global 转换到 Ego 坐标系
    boxes_ego = transform_boxes_to_ego(boxes, lidar_ego_pose)
    
    # 加载 LiDAR 点云作为背景
    points = loader.load_lidar_points(sample_token)
    
    save_bev = get_output_path("bev", f"boxes_bev_{short_token}.jpg")
    draw_boxes_bev(
        boxes=boxes_ego,
        save_path=save_bev,
        title=f"3D Boxes BEV 俯视图 (sample: {short_token}...)",
        points=points,
    )
    
    # ---- 相机图像可视化 ----
    print("\n📌 步骤 4: 在 CAM_FRONT 图像中绘制 3D boxes...")
    
    cam_sd, cam_calib, cam_ego_pose = loader.get_sensor_records(sample_token, 'CAM_FRONT')
    camera_intrinsic = np.array(cam_calib['camera_intrinsic'])
    
    # 将 boxes 从 Global 转换到 Camera 坐标系
    boxes_cam = transform_boxes_to_camera(boxes, cam_ego_pose, cam_calib)
    
    # 读取相机图像
    cam_path = os.path.join(loader.dataroot, cam_sd['filename'])
    image = cv2.imread(cam_path)
    
    if image is not None:
        # 绘制 boxes
        result = draw_boxes_on_image(image, boxes_cam, camera_intrinsic)
        
        save_cam = get_output_path("images", f"boxes_cam_front_{short_token}.jpg")
        
        # 用 matplotlib 保存（原图 vs 带 boxes 的图）
        import matplotlib.pyplot as plt
        fig, axes = plt.subplots(1, 2, figsize=(20, 6))
        
        axes[0].imshow(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        axes[0].set_title('原始图像', fontsize=13)
        axes[0].axis('off')
        
        axes[1].imshow(cv2.cvtColor(result, cv2.COLOR_BGR2RGB))
        axes[1].set_title(f'3D Boxes 投影 ({len(boxes_cam)} 个)', fontsize=13)
        axes[1].axis('off')
        
        plt.suptitle(f'3D Box 可视化 — CAM_FRONT (sample: {short_token}...)',
                     fontsize=15, fontweight='bold')
        plt.tight_layout()
        plt.savefig(save_cam, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"  ✅ CAM_FRONT box 图已保存: {save_cam}")
    else:
        print(f"  ❌ 无法读取图像: {cam_path}")
    
    print_header("3D Box 可视化完成 ✅")
    print(f"\n📁 输出文件:")
    print(f"   - BEV boxes: outputs/bev/boxes_bev_{short_token}.jpg")
    print(f"   - CAM_FRONT boxes: outputs/images/boxes_cam_front_{short_token}.jpg")
    print(f"\n下一步: 运行 python scripts/05_generate_simple_bev.py\n")


if __name__ == '__main__':
    main()
