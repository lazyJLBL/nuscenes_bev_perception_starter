"""
draw_bev.py — BEV 可视化模块
===============================
可视化 BEV（鸟瞰图）的各个通道和叠加标注框的效果。
"""

import os
import cv2
import numpy as np
import matplotlib.pyplot as plt
from typing import List, Optional, Tuple

import sys
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from src.geometry.boxes import Box3D
from src.bev.simple_bev import SimpleBEVGenerator
from src.utils.plotting import configure_matplotlib_chinese

configure_matplotlib_chinese()


def visualize_bev_channels(
    height_map: np.ndarray,
    density_map: np.ndarray,
    intensity_map: np.ndarray,
    rgb_map: np.ndarray,
    save_path: Optional[str] = None,
    show: bool = False,
    title: str = "BEV 三通道可视化",
) -> None:
    """
    分别可视化 BEV 的三个通道和合成 RGB。
    
    参数:
        height_map: 高度图
        density_map: 密度图
        intensity_map: 强度图
        rgb_map: RGB 合成图
        save_path: 保存路径
        show: 是否弹窗显示
        title: 标题
    """
    fig, axes = plt.subplots(1, 4, figsize=(24, 6))
    
    # 高度图
    im0 = axes[0].imshow(height_map, cmap='jet')
    axes[0].set_title('高度图 (Height Map)\nR 通道', fontsize=12)
    axes[0].axis('off')
    plt.colorbar(im0, ax=axes[0], fraction=0.046, pad=0.04, label='高度 (m)')
    
    # 密度图（使用对数显示）
    density_log = np.log1p(density_map)
    im1 = axes[1].imshow(density_log, cmap='hot')
    axes[1].set_title('密度图 (Density Map)\nG 通道', fontsize=12)
    axes[1].axis('off')
    plt.colorbar(im1, ax=axes[1], fraction=0.046, pad=0.04, label='log(1+点数)')
    
    # 强度图
    im2 = axes[2].imshow(intensity_map, cmap='gray')
    axes[2].set_title('强度图 (Intensity Map)\nB 通道', fontsize=12)
    axes[2].axis('off')
    plt.colorbar(im2, ax=axes[2], fraction=0.046, pad=0.04, label='反射强度')
    
    # RGB 合成图
    axes[3].imshow(rgb_map)
    axes[3].set_title('RGB 合成图\n(R=高度, G=密度, B=强度)', fontsize=12)
    axes[3].axis('off')
    
    plt.suptitle(title, fontsize=15, fontweight='bold')
    plt.tight_layout()
    
    if save_path:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"  ✅ BEV 通道图已保存: {save_path}")
    
    if show:
        plt.show()
    else:
        plt.close()


def draw_boxes_on_bev_image(
    bev_image: np.ndarray,
    boxes: List[Box3D],
    bev_generator: SimpleBEVGenerator,
    thickness: int = 2,
) -> np.ndarray:
    """
    在 BEV RGB 图像上绘制 3D box。
    
    参数:
        bev_image (np.ndarray): BEV RGB 图像 (H, W, 3)
        boxes (list[Box3D]): Ego 坐标系下的 box 列表
        bev_generator (SimpleBEVGenerator): BEV 生成器（用于坐标转换）
        thickness (int): 线宽
    
    返回:
        np.ndarray: 叠加了 box 的 BEV 图像
    """
    result = bev_image.copy()
    
    # 类别颜色映射
    color_map = {
        'car': (0, 255, 0),
        'truck': (0, 200, 255),
        'bus': (255, 100, 0),
        'pedestrian': (255, 0, 255),
        'motorcycle': (255, 255, 0),
        'bicycle': (128, 255, 0),
        'barrier': (128, 128, 128),
        'traffic_cone': (0, 128, 255),
    }
    
    for box in boxes:
        # 获取底面角点
        corners = box.bottom_corners()
        
        # 检查是否在 BEV 范围内
        if (corners[:, 0].max() < bev_generator.x_range[0] or
            corners[:, 0].min() > bev_generator.x_range[1] or
            corners[:, 1].max() < bev_generator.y_range[0] or
            corners[:, 1].min() > bev_generator.y_range[1]):
            continue
        
        # 转换为像素坐标
        pixel_corners = []
        for c in corners:
            row, col = bev_generator.world_to_pixel(c[0], c[1])
            pixel_corners.append([col, row])  # OpenCV 需要 (x, y) = (col, row)
        
        pixel_corners = np.array(pixel_corners, dtype=np.int32)
        
        # 获取颜色
        short_label = box.label.split('.')[-1] if '.' in box.label else box.label
        color = color_map.get(short_label, (0, 255, 255))
        
        # 绘制四边形
        cv2.polylines(result, [pixel_corners], True, color, thickness)
        
        # 绘制朝向线（前面中点到中心）
        front_mid = ((pixel_corners[1] + pixel_corners[2]) / 2).astype(int)
        center_px = np.array(bev_generator.world_to_pixel(box.center[0], box.center[1]))
        center_px = np.array([center_px[1], center_px[0]])  # (col, row)
        cv2.arrowedLine(result, tuple(center_px), tuple(front_mid), (0, 0, 255), 1)
    
    return result
