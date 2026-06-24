"""
projection.py — LiDAR 到相机的投影模块
=========================================
将 LiDAR 点云投影到相机图像上，并进行可视化。

这是自动驾驶感知中最经典的操作之一：
将 3D 空间中的点映射到 2D 图像平面。

投影流程:
    1. 将 LiDAR 点从 LiDAR 坐标系转换到 Camera 坐标系
    2. 过滤掉相机后方的点（z <= 0）
    3. 使用相机内参将 3D 点投影到 2D 图像平面
    4. 过滤掉图像范围外的点
    5. 按深度给点上色
"""

import os
import cv2
import numpy as np
import matplotlib.pyplot as plt
from typing import Tuple, Optional

from .transforms import lidar_to_camera, camera_to_image


def project_lidar_to_camera_image(
    points: np.ndarray,
    lidar_calib: dict,
    lidar_ego_pose: dict,
    camera_calib: dict,
    camera_ego_pose: dict,
    image_shape: Tuple[int, int] = (900, 1600),
    min_depth: float = 1.0,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    将 LiDAR 点云投影到相机图像平面。
    
    参数:
        points (np.ndarray): LiDAR 点云 (N, 5) [x, y, z, intensity, ring]
        lidar_calib (dict): LiDAR 的 calibrated_sensor 记录
        lidar_ego_pose (dict): LiDAR 时刻的 ego_pose
        camera_calib (dict): Camera 的 calibrated_sensor 记录
        camera_ego_pose (dict): Camera 时刻的 ego_pose
        image_shape (tuple): 图像尺寸 (height, width)
        min_depth (float): 最小深度阈值（米），过滤太近的点
    
    返回:
        tuple:
            - pixel_coords (np.ndarray): 像素坐标 (M, 2)，[u, v]
            - depths (np.ndarray): 对应的深度值 (M,)
    """
    img_h, img_w = image_shape
    
    # ---- 步骤 1: LiDAR → Camera 坐标系 ----
    # 完整变换链: LiDAR → Ego → Global → Ego(cam) → Camera
    points_camera = lidar_to_camera(
        points, lidar_calib, lidar_ego_pose, camera_calib, camera_ego_pose
    )
    
    # ---- 步骤 2: 过滤相机后方的点 ----
    # Camera 坐标系中，Z 轴朝前
    # Z <= 0 的点在相机后方，无法成像
    front_mask = points_camera[:, 2] > min_depth
    points_camera = points_camera[front_mask]
    
    if len(points_camera) == 0:
        return np.array([]).reshape(0, 2), np.array([])
    
    # ---- 步骤 3: 投影到图像平面 ----
    camera_intrinsic = np.array(camera_calib['camera_intrinsic'])
    projected = camera_to_image(points_camera, camera_intrinsic)
    
    # projected[:, 0] = u (水平像素坐标)
    # projected[:, 1] = v (垂直像素坐标)
    # projected[:, 2] = depth (深度)
    
    # ---- 步骤 4: 过滤图像范围外的点 ----
    u = projected[:, 0]
    v = projected[:, 1]
    depths = projected[:, 2]
    
    image_mask = (
        (u >= 0) & (u < img_w) &
        (v >= 0) & (v < img_h) &
        (depths > 0)
    )
    
    pixel_coords = projected[image_mask, :2]  # (M, 2)
    depths = depths[image_mask]               # (M,)
    
    return pixel_coords, depths


def draw_lidar_on_image(
    image: np.ndarray,
    pixel_coords: np.ndarray,
    depths: np.ndarray,
    point_size: int = 2,
    alpha: float = 0.8,
    depth_range: Tuple[float, float] = (1.0, 60.0),
) -> np.ndarray:
    """
    将 LiDAR 投影点绘制在相机图像上。
    
    使用深度值为点上色: 近处蓝色 → 远处红色（类似热力图）
    
    参数:
        image (np.ndarray): 相机图像 (H, W, 3) BGR 格式
        pixel_coords (np.ndarray): 像素坐标 (M, 2)
        depths (np.ndarray): 深度值 (M,)
        point_size (int): 点的大小
        alpha (float): 透明度
        depth_range (tuple): 深度显示范围 (min, max)
    
    返回:
        np.ndarray: 叠加了 LiDAR 点的图像
    """
    result = image.copy()
    
    if len(pixel_coords) == 0:
        return result
    
    # 将深度归一化到 [0, 1]
    d_min, d_max = depth_range
    normalized = np.clip((depths - d_min) / (d_max - d_min), 0, 1)
    
    # 使用 HSV 颜色映射: 近处红色(0) → 远处蓝色(240)
    # OpenCV HSV: H=[0,180], S=[0,255], V=[0,255]
    for i in range(len(pixel_coords)):
        u, v = int(pixel_coords[i, 0]), int(pixel_coords[i, 1])
        
        # 深度映射到色调: 近处红色，远处蓝色
        hue = int((1 - normalized[i]) * 120)  # 0(红) → 120(绿)
        color_hsv = np.array([[[hue, 255, 255]]], dtype=np.uint8)
        color_bgr = cv2.cvtColor(color_hsv, cv2.COLOR_HSV2BGR)[0, 0].tolist()
        
        cv2.circle(result, (u, v), point_size, color_bgr, -1)
    
    return result


def visualize_lidar_projection(
    image: np.ndarray,
    pixel_coords: np.ndarray,
    depths: np.ndarray,
    save_path: Optional[str] = None,
    show: bool = False,
    title: str = "LiDAR 投影到相机图像",
) -> np.ndarray:
    """
    可视化 LiDAR 投影结果。
    
    参数:
        image (np.ndarray): 相机图像 (BGR)
        pixel_coords (np.ndarray): 像素坐标 (M, 2)
        depths (np.ndarray): 深度值 (M,)
        save_path (str, optional): 保存路径
        show (bool): 是否弹窗显示
        title (str): 标题
    
    返回:
        np.ndarray: 叠加了投影点的图像
    """
    # 绘制 LiDAR 点
    result = draw_lidar_on_image(image, pixel_coords, depths)
    
    if save_path or show:
        fig, axes = plt.subplots(1, 2, figsize=(20, 6))
        
        # 原图
        axes[0].imshow(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        axes[0].set_title('原始相机图像', fontsize=13)
        axes[0].axis('off')
        
        # 叠加投影的图
        axes[1].imshow(cv2.cvtColor(result, cv2.COLOR_BGR2RGB))
        axes[1].set_title(f'{title} ({len(pixel_coords)} 个点)', fontsize=13)
        axes[1].axis('off')
        
        plt.suptitle(title, fontsize=15, fontweight='bold')
        plt.tight_layout()
        
        if save_path:
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"  ✅ LiDAR 投影图已保存: {save_path}")
        
        if show:
            plt.show()
        else:
            plt.close()
    
    return result
