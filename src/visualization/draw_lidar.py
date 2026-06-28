"""
draw_lidar.py — LiDAR 点云可视化
==================================
提供 LiDAR 点云的俯视图（Top-down / BEV 视角）可视化功能。

LiDAR 坐标系说明:
    - X 轴: 车辆前方
    - Y 轴: 车辆左方
    - Z 轴: 车辆上方
    
    俯视图中:
    - 横轴对应 Y 轴（左右方向）
    - 纵轴对应 X 轴（前后方向）
"""

import os
import numpy as np
import matplotlib.pyplot as plt
from typing import Optional, Tuple

from src.utils.plotting import configure_matplotlib_chinese

configure_matplotlib_chinese()


def visualize_lidar_topdown(
    points: np.ndarray,
    x_range: Tuple[float, float] = (-50, 50),
    y_range: Tuple[float, float] = (-50, 50),
    z_range: Tuple[float, float] = (-5, 3),
    point_size: float = 0.3,
    save_path: Optional[str] = None,
    show: bool = False,
    title: str = "LiDAR 俯视图 (Top-down View)",
    color_by: str = 'height',
) -> None:
    """
    可视化 LiDAR 点云的俯视图。
    
    参数:
        points (np.ndarray): 形状 (N, 5) 的点云，列为 [x, y, z, intensity, ring]
        x_range (tuple): X 轴范围（米），前后方向
        y_range (tuple): Y 轴范围（米），左右方向
        z_range (tuple): Z 轴范围（米），上下方向
        point_size (float): 点的大小
        save_path (str, optional): 保存路径
        show (bool): 是否弹窗显示
        title (str): 图像标题
        color_by (str): 着色方式，'height'（高度）, 'intensity'（强度）, 'distance'（距离）
    """
    # 过滤范围内的点
    mask = (
        (points[:, 0] >= x_range[0]) & (points[:, 0] <= x_range[1]) &
        (points[:, 1] >= y_range[0]) & (points[:, 1] <= y_range[1]) &
        (points[:, 2] >= z_range[0]) & (points[:, 2] <= z_range[1])
    )
    filtered = points[mask]
    
    if len(filtered) == 0:
        print("  ⚠️ 过滤后没有点云数据")
        return
    
    # 选择着色方式
    if color_by == 'height':
        # 按高度着色：低处蓝色，高处红色
        colors = filtered[:, 2]
        cmap = 'jet'
        clabel = '高度 (m)'
    elif color_by == 'intensity':
        # 按反射强度着色
        colors = filtered[:, 3]
        cmap = 'hot'
        clabel = '反射强度'
    elif color_by == 'distance':
        # 按到原点的距离着色
        colors = np.sqrt(filtered[:, 0]**2 + filtered[:, 1]**2)
        cmap = 'viridis'
        clabel = '距离 (m)'
    else:
        colors = filtered[:, 2]
        cmap = 'jet'
        clabel = '高度 (m)'
    
    # 绘制俯视图
    fig, ax = plt.subplots(1, 1, figsize=(10, 10))
    
    # 在俯视图中: 横轴=Y（左右），纵轴=X（前后）
    scatter = ax.scatter(
        filtered[:, 1],   # Y 轴 -> 图像水平方向
        filtered[:, 0],   # X 轴 -> 图像垂直方向
        c=colors,
        cmap=cmap,
        s=point_size,
        alpha=0.8,
    )
    
    # 标注 ego vehicle 位置（原点）
    ax.plot(0, 0, marker='*', color='red', markersize=15, label='Ego Vehicle')
    
    # 画坐标轴方向指示
    ax.annotate('前方 (Front)', xy=(0, x_range[1] * 0.9),
                fontsize=10, ha='center', color='white',
                bbox=dict(boxstyle='round', facecolor='green', alpha=0.7))
    
    ax.set_xlim(y_range)
    ax.invert_xaxis()  # 反转 X 轴，使得 Y=50(左)在图像左边，Y=-50(右)在图像右边
    ax.set_ylim(x_range)
    ax.set_xlabel('Y (左 ← → 右)', fontsize=12)
    ax.set_ylabel('X (后 ← → 前)', fontsize=12)
    ax.set_title(f"{title}\n({len(filtered)} 个点)", fontsize=14)
    ax.set_aspect('equal')
    ax.set_facecolor('black')
    ax.legend(loc='lower right', fontsize=10)
    
    # 添加颜色条
    cbar = plt.colorbar(scatter, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label(clabel, fontsize=11)
    
    plt.tight_layout()
    
    if save_path:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        plt.savefig(save_path, dpi=150, bbox_inches='tight', facecolor='white')
        print(f"  ✅ LiDAR 俯视图已保存: {save_path}")
    
    if show:
        plt.show()
    else:
        plt.close()


def visualize_lidar_3views(
    points: np.ndarray,
    save_path: Optional[str] = None,
    show: bool = False,
) -> None:
    """
    可视化 LiDAR 点云的三视图（俯视、前视、侧视）。
    
    参数:
        points (np.ndarray): 形状 (N, 5) 的点云
        save_path (str, optional): 保存路径
        show (bool): 是否弹窗显示
    """
    fig, axes = plt.subplots(1, 3, figsize=(24, 7))
    
    point_size = 0.1
    colors = points[:, 2]  # 按高度着色
    
    # 俯视图 (Top-down): XY 平面
    axes[0].scatter(points[:, 1], points[:, 0], c=colors, cmap='jet', s=point_size, alpha=0.5)
    axes[0].set_title('俯视图 (Top-down)', fontsize=13)
    axes[0].set_xlabel('Y (米)')
    axes[0].set_ylabel('X (米)')
    axes[0].set_aspect('equal')
    axes[0].set_xlim(axes[0].get_xlim()[::-1])  # 反转 Y 轴（图的横轴）
    axes[0].set_facecolor('black')
    
    # 前视图 (Front): YZ 平面
    axes[1].scatter(points[:, 1], points[:, 2], c=colors, cmap='jet', s=point_size, alpha=0.5)
    axes[1].set_title('前视图 (Front)', fontsize=13)
    axes[1].set_xlabel('Y (米)')
    axes[1].set_ylabel('Z (米)')
    axes[1].set_aspect('equal')
    axes[1].set_xlim(axes[1].get_xlim()[::-1])  # 反转 Y 轴（图的横轴）
    axes[1].set_facecolor('black')
    
    # 侧视图 (Side): XZ 平面
    axes[2].scatter(points[:, 0], points[:, 2], c=colors, cmap='jet', s=point_size, alpha=0.5)
    axes[2].set_title('侧视图 (Side)', fontsize=13)
    axes[2].set_xlabel('X (米)')
    axes[2].set_ylabel('Z (米)')
    axes[2].set_aspect('equal')
    axes[2].set_facecolor('black')
    
    plt.suptitle('LiDAR 点云三视图', fontsize=15, fontweight='bold')
    plt.tight_layout()
    
    if save_path:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        plt.savefig(save_path, dpi=150, bbox_inches='tight', facecolor='white')
        print(f"  ✅ LiDAR 三视图已保存: {save_path}")
    
    if show:
        plt.show()
    else:
        plt.close()
