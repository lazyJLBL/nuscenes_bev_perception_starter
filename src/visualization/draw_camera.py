"""
draw_camera.py — 摄像头图像可视化
===================================
将 nuScenes 的 6 个环视摄像头图像拼接成一张大图。

6 个摄像头的排列方式（对应真实车辆上的安装位置）:
    ┌──────────┬──────────┬──────────┐
    │ FRONT_L  │  FRONT   │ FRONT_R  │
    ├──────────┼──────────┼──────────┤
    │  BACK_L  │  BACK    │  BACK_R  │
    └──────────┴──────────┴──────────┘
"""

import os
import cv2
import numpy as np
import matplotlib.pyplot as plt
from typing import Dict, Optional

from src.utils.plotting import configure_matplotlib_chinese

configure_matplotlib_chinese()


# 6 个摄像头的显示布局（2行3列）
CAMERA_LAYOUT = [
    ['CAM_FRONT_LEFT', 'CAM_FRONT', 'CAM_FRONT_RIGHT'],
    ['CAM_BACK_LEFT',  'CAM_BACK',  'CAM_BACK_RIGHT'],
]

# 摄像头中文名称映射
CAMERA_NAMES_CN = {
    'CAM_FRONT':       '前方 (Front)',
    'CAM_FRONT_LEFT':  '左前方 (Front Left)',
    'CAM_FRONT_RIGHT': '右前方 (Front Right)',
    'CAM_BACK':        '后方 (Back)',
    'CAM_BACK_LEFT':   '左后方 (Back Left)',
    'CAM_BACK_RIGHT':  '右后方 (Back Right)',
}


def visualize_cameras(
    camera_paths: Dict[str, str],
    save_path: Optional[str] = None,
    show: bool = False,
    figsize: tuple = (18, 8),
    title: str = "nuScenes 6 环视摄像头"
) -> np.ndarray:
    """
    可视化 6 个环视摄像头图像。
    
    参数:
        camera_paths (dict): {摄像头名: 图像文件路径}
        save_path (str, optional): 保存路径
        show (bool): 是否弹窗显示
        figsize (tuple): 图像大小
        title (str): 总标题
    
    返回:
        np.ndarray: 拼接后的图像（OpenCV BGR 格式）
    """
    fig, axes = plt.subplots(2, 3, figsize=figsize)
    fig.suptitle(title, fontsize=16, fontweight='bold')
    
    for row_idx, row_cams in enumerate(CAMERA_LAYOUT):
        for col_idx, cam_name in enumerate(row_cams):
            ax = axes[row_idx][col_idx]
            
            if cam_name in camera_paths and os.path.exists(camera_paths[cam_name]):
                # 读取图像（OpenCV 默认 BGR，matplotlib 需要 RGB）
                img = cv2.imread(camera_paths[cam_name])
                if img is not None:
                    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                    ax.imshow(img_rgb)
                else:
                    ax.text(0.5, 0.5, '图像读取失败', ha='center', va='center', 
                            transform=ax.transAxes, fontsize=12)
            else:
                ax.text(0.5, 0.5, '图像文件不存在', ha='center', va='center',
                        transform=ax.transAxes, fontsize=12, color='red')
            
            # 设置子图标题
            cam_label = CAMERA_NAMES_CN.get(cam_name, cam_name)
            ax.set_title(cam_label, fontsize=11)
            ax.axis('off')
    
    plt.tight_layout()
    
    if save_path:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"  ✅ 摄像头图像已保存: {save_path}")
    
    if show:
        plt.show()
    else:
        plt.close()
    
    return None


def visualize_single_camera(
    image_path: str,
    camera_name: str = "",
    save_path: Optional[str] = None,
    show: bool = False,
) -> np.ndarray:
    """
    可视化单个摄像头图像。
    
    参数:
        image_path (str): 图像文件路径
        camera_name (str): 摄像头名称
        save_path (str, optional): 保存路径
        show (bool): 是否弹窗显示
    
    返回:
        np.ndarray: 图像（BGR 格式）
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"图像文件不存在: {image_path}")
    
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"无法读取图像: {image_path}")
    
    if save_path or show:
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        plt.figure(figsize=(12, 6))
        plt.imshow(img_rgb)
        plt.title(f"{CAMERA_NAMES_CN.get(camera_name, camera_name)}", fontsize=14)
        plt.axis('off')
        
        if save_path:
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
        
        if show:
            plt.show()
        else:
            plt.close()
    
    return img
