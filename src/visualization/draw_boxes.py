"""
draw_boxes.py — 3D Box 可视化模块
====================================
在相机图像和 BEV 平面上绘制 3D 标注框。
"""

import os
import cv2
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyArrowPatch
from typing import List, Dict, Tuple, Optional

import sys
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from src.geometry.boxes import Box3D
from src.utils.config import get_dataset_config


# 获取类别颜色
def _get_class_color(label: str) -> Tuple[int, int, int]:
    """
    获取类别对应的颜色（BGR 格式）。
    
    参数:
        label (str): 类别名，如 "vehicle.car"
    
    返回:
        tuple: (B, G, R) 颜色
    """
    try:
        dataset_config = get_dataset_config()
        class_colors = dataset_config.get('class_colors', {})
    except Exception:
        class_colors = {}
    
    # 从完整类别名中提取短名
    # 例如: "vehicle.car" → "car"
    short_name = label.split('.')[-1] if '.' in label else label
    
    if short_name in class_colors:
        return tuple(class_colors[short_name])
    
    # 默认颜色
    default_colors = {
        'car': (0, 255, 0),
        'truck': (0, 200, 255),
        'bus': (255, 100, 0),
        'pedestrian': (255, 0, 255),
        'motorcycle': (255, 255, 0),
        'bicycle': (128, 255, 0),
        'barrier': (128, 128, 128),
        'traffic_cone': (0, 128, 255),
    }
    
    return default_colors.get(short_name, (0, 255, 255))


def draw_box_on_image(
    image: np.ndarray,
    box: Box3D,
    camera_intrinsic: np.ndarray,
    color: Tuple[int, int, int] = None,
    thickness: int = 2,
) -> np.ndarray:
    """
    在相机图像上绘制 3D Box 的投影。
    
    注意: box 必须已经在 Camera 坐标系下！
    
    3D box 投影到图像上后是一个类似的透视图：
    
        7 -------- 6
       /|         /|
      4 -------- 5 |
      | |        | |
      | 3 -------| 2
      |/         |/
      0 -------- 1
    
    参数:
        image (np.ndarray): 图像 (H, W, 3) BGR
        box (Box3D): Camera 坐标系下的 3D box
        camera_intrinsic (np.ndarray): 3x3 相机内参矩阵
        color (tuple): BGR 颜色
        thickness (int): 线宽
    
    返回:
        np.ndarray: 绘制了 box 的图像
    """
    result = image.copy()
    
    if color is None:
        color = _get_class_color(box.label)
    
    # 检查 box 是否在相机前方
    if box.center[2] <= 0:
        return result
    
    # 获取 8 个角点的图像坐标
    corners_3d = box.corners()
    
    # 过滤掉在相机后方的角点
    if np.any(corners_3d[:, 2] <= 0):
        return result
    
    corners_2d = box.project_to_image(camera_intrinsic)
    corners_2d = corners_2d.astype(int)
    
    img_h, img_w = image.shape[:2]
    
    # 检查角点是否在图像范围内
    if np.all(corners_2d[:, 0] < 0) or np.all(corners_2d[:, 0] >= img_w):
        return result
    if np.all(corners_2d[:, 1] < 0) or np.all(corners_2d[:, 1] >= img_h):
        return result
    
    # 绘制 12 条边
    # 底面: 0-1, 1-2, 2-3, 3-0
    # 顶面: 4-5, 5-6, 6-7, 7-4
    # 连接: 0-4, 1-5, 2-6, 3-7
    edges = [
        (0, 1), (1, 2), (2, 3), (3, 0),  # 底面
        (4, 5), (5, 6), (6, 7), (7, 4),  # 顶面
        (0, 4), (1, 5), (2, 6), (3, 7),  # 连接
    ]
    
    for i, j in edges:
        pt1 = tuple(corners_2d[i])
        pt2 = tuple(corners_2d[j])
        cv2.line(result, pt1, pt2, color, thickness)
    
    # 绘制前面（朝向）用不同颜色强调
    # 前面由角点 1, 2, 6, 5 组成
    front_edges = [(1, 2), (2, 6), (6, 5), (5, 1)]
    front_color = (0, 0, 255)  # 红色表示前方
    for i, j in front_edges:
        pt1 = tuple(corners_2d[i])
        pt2 = tuple(corners_2d[j])
        cv2.line(result, pt1, pt2, front_color, thickness + 1)
    
    # 添加类别标签
    label_short = box.label.split('.')[-1] if '.' in box.label else box.label
    label_pos = (corners_2d[4][0], corners_2d[4][1] - 5)
    cv2.putText(result, label_short, label_pos,
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA)
    
    return result


def draw_boxes_on_image(
    image: np.ndarray,
    boxes: List[Box3D],
    camera_intrinsic: np.ndarray,
    thickness: int = 2,
) -> np.ndarray:
    """
    在相机图像上绘制多个 3D Box。
    
    参数:
        image (np.ndarray): 图像 (BGR)
        boxes (list[Box3D]): Camera 坐标系下的 box 列表
        camera_intrinsic (np.ndarray): 3x3 相机内参矩阵
        thickness (int): 线宽
    
    返回:
        np.ndarray: 绘制了所有 box 的图像
    """
    result = image.copy()
    
    for box in boxes:
        result = draw_box_on_image(result, box, camera_intrinsic, thickness=thickness)
    
    return result


def draw_boxes_bev(
    boxes: List[Box3D],
    x_range: Tuple[float, float] = (-50, 50),
    y_range: Tuple[float, float] = (-50, 50),
    figsize: Tuple[int, int] = (10, 10),
    save_path: Optional[str] = None,
    show: bool = False,
    title: str = "3D Boxes BEV 俯视图",
    points: Optional[np.ndarray] = None,
) -> None:
    """
    在 BEV 俯视图上绘制 3D Box。
    
    参数:
        boxes (list[Box3D]): Ego 坐标系或 LiDAR 坐标系下的 box 列表
        x_range (tuple): X 轴范围（米）
        y_range (tuple): Y 轴范围（米）
        figsize (tuple): 图像大小
        save_path (str, optional): 保存路径
        show (bool): 是否弹窗显示
        title (str): 标题
        points (np.ndarray, optional): 背景点云 (N, 3+)
    """
    fig, ax = plt.subplots(1, 1, figsize=figsize)
    
    # 绘制背景点云（如果有）
    if points is not None:
        mask = (
            (points[:, 0] >= x_range[0]) & (points[:, 0] <= x_range[1]) &
            (points[:, 1] >= y_range[0]) & (points[:, 1] <= y_range[1])
        )
        filtered = points[mask]
        ax.scatter(filtered[:, 1], filtered[:, 0],
                   c='white', s=0.1, alpha=0.3)
    
    # 绘制 ego vehicle（原点处的红色三角形）
    ego_triangle = plt.Polygon(
        [[0, 2], [-1, -1], [1, -1]], 
        closed=True, fill=True, facecolor='red', edgecolor='red', alpha=0.8
    )
    ax.add_patch(ego_triangle)
    
    # 绘制每个 box
    for box in boxes:
        # 获取底面角点（BEV 只需要 xy 坐标）
        corners = box.bottom_corners()
        
        # 检查 box 是否在显示范围内
        if (corners[:, 0].max() < x_range[0] or corners[:, 0].min() > x_range[1] or
            corners[:, 1].max() < y_range[0] or corners[:, 1].min() > y_range[1]):
            continue
        
        # 获取颜色
        color_bgr = _get_class_color(box.label)
        color_rgb = (color_bgr[2] / 255, color_bgr[1] / 255, color_bgr[0] / 255)
        
        # 绘制底面矩形（在 BEV 中: 横轴=Y, 纵轴=X）
        # 角点顺序: 0 -> 1 -> 2 -> 3 -> 0
        polygon = plt.Polygon(
            corners[:, [1, 0]],  # 交换 x, y 以适应 BEV 视角
            closed=True,
            fill=False,
            edgecolor=color_rgb,
            linewidth=2,
        )
        ax.add_patch(polygon)
        
        # 绘制朝向箭头（从中心指向前方）
        center = box.center
        front_mid = (corners[1] + corners[2]) / 2  # 前面中点
        
        ax.annotate('',
            xy=(front_mid[1], front_mid[0]),
            xytext=(center[1], center[0]),
            arrowprops=dict(arrowstyle='->', color=color_rgb, lw=1.5),
        )
        
        # 添加类别标签
        label_short = box.label.split('.')[-1] if '.' in box.label else box.label
        ax.text(center[1], center[0] + 1, label_short,
                fontsize=6, ha='center', color=color_rgb)
    
    ax.set_xlim(y_range)
    ax.invert_xaxis()  # 反转 X 轴，使得 Y=50(左)在图像左边，Y=-50(右)在图像右边
    ax.set_ylim(x_range)
    ax.set_xlabel('Y (左 ← → 右)', fontsize=12)
    ax.set_ylabel('X (后 ← → 前)', fontsize=12)
    ax.set_title(title, fontsize=14)
    ax.set_aspect('equal')
    ax.set_facecolor('black')
    ax.grid(True, alpha=0.2, color='gray')
    
    plt.tight_layout()
    
    if save_path:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        plt.savefig(save_path, dpi=150, bbox_inches='tight', facecolor='white')
        print(f"  ✅ BEV Box 图已保存: {save_path}")
    
    if show:
        plt.show()
    else:
        plt.close()
