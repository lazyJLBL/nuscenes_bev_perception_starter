"""
simple_bev.py — 简单 BEV（鸟瞰图）生成模块
===============================================
从 LiDAR 点云生成简单的 BEV 表示。

BEV 是什么:
    BEV = Bird's Eye View（鸟瞰图），即从上往下看的视角。
    在自动驾驶中，BEV 提供了一个统一的 2D 平面，
    方便进行目标检测、轨迹预测和路径规划。

生成的 BEV 包含三个通道:
    1. Height Map（高度图）: 每个网格中最高点的高度
    2. Density Map（密度图）: 每个网格中的点数
    3. Intensity Map（强度图）: 每个网格中点的平均反射强度
"""

import numpy as np
from typing import Tuple, Optional


class SimpleBEVGenerator:
    """
    简单 BEV 生成器。
    
    将 3D 点云投影到 2D 网格（鸟瞰图），生成高度/密度/强度三通道表示。
    
    使用示例:
        bev_gen = SimpleBEVGenerator(
            x_range=(-50, 50),
            y_range=(-50, 50),
            z_range=(-5, 3),
            resolution=0.2,
        )
        height, density, intensity = bev_gen.generate(points)
        rgb = bev_gen.to_rgb(height, density, intensity)
    """
    
    def __init__(
        self,
        x_range: Tuple[float, float] = (-50.0, 50.0),
        y_range: Tuple[float, float] = (-50.0, 50.0),
        z_range: Tuple[float, float] = (-5.0, 3.0),
        resolution: float = 0.2,
    ):
        """
        参数:
            x_range (tuple): X 轴范围（米），前后方向
            y_range (tuple): Y 轴范围（米），左右方向
            z_range (tuple): Z 轴范围（米），上下方向
            resolution (float): BEV 分辨率（米/像素）
                               例如 0.2 表示每个像素代表 0.2m x 0.2m
        """
        self.x_range = x_range
        self.y_range = y_range
        self.z_range = z_range
        self.resolution = resolution
        
        # 计算 BEV 图像尺寸
        # 例如: x_range=(-50,50), resolution=0.2 → width = 100/0.2 = 500 像素
        self.bev_width = int((y_range[1] - y_range[0]) / resolution)   # Y 方向 → 图像宽度
        self.bev_height = int((x_range[1] - x_range[0]) / resolution)  # X 方向 → 图像高度
        
        print(f"  BEV 参数:")
        print(f"    X 范围: {x_range} 米")
        print(f"    Y 范围: {y_range} 米")
        print(f"    Z 范围: {z_range} 米")
        print(f"    分辨率: {resolution} 米/像素")
        print(f"    BEV 图像尺寸: {self.bev_width} x {self.bev_height} 像素")
    
    def _filter_points(self, points: np.ndarray) -> np.ndarray:
        """
        过滤范围内的点。
        
        参数:
            points (np.ndarray): 原始点云 (N, 5)
        
        返回:
            np.ndarray: 过滤后的点云
        """
        mask = (
            (points[:, 0] >= self.x_range[0]) & (points[:, 0] < self.x_range[1]) &
            (points[:, 1] >= self.y_range[0]) & (points[:, 1] < self.y_range[1]) &
            (points[:, 2] >= self.z_range[0]) & (points[:, 2] < self.z_range[1])
        )
        return points[mask]
    
    def _point_to_pixel(self, points: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        将 3D 点坐标转换为 BEV 图像的像素坐标。
        
        坐标映射:
            X(前后) → 图像行 (row)，注意：前方在图像上方，所以需要翻转
            Y(左右) → 图像列 (col)
        
        参数:
            points (np.ndarray): 点云 (N, 5)
        
        返回:
            tuple: (row_indices, col_indices)
        """
        # X 方向: 前方 → 图像上方（row=0）
        # 所以 row = (x_max - x) / resolution
        rows = ((self.x_range[1] - points[:, 0]) / self.resolution).astype(int)
        
        # Y 方向: 左方(正) → 图像左方(col=0)
        # cols = (y_max - y) / resolution  
        cols = ((self.y_range[1] - points[:, 1]) / self.resolution).astype(int)
        
        # 裁剪到有效范围
        rows = np.clip(rows, 0, self.bev_height - 1)
        cols = np.clip(cols, 0, self.bev_width - 1)
        
        return rows, cols
    
    def generate(self, points: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        从点云生成 BEV 三通道表示。
        
        参数:
            points (np.ndarray): 点云 (N, 5) [x, y, z, intensity, ring]
        
        返回:
            tuple: (height_map, density_map, intensity_map)
                - height_map (np.ndarray): 高度图 (H, W)，每个像素为该区域最高点的高度
                - density_map (np.ndarray): 密度图 (H, W)，每个像素为该区域的点数
                - intensity_map (np.ndarray): 强度图 (H, W)，每个像素为该区域点的平均反射强度
        """
        # 过滤范围内的点
        filtered = self._filter_points(points)
        
        if len(filtered) == 0:
            print("  ⚠️ 过滤后没有点云，返回空 BEV")
            return (
                np.zeros((self.bev_height, self.bev_width)),
                np.zeros((self.bev_height, self.bev_width)),
                np.zeros((self.bev_height, self.bev_width)),
            )
        
        print(f"  使用 {len(filtered)} / {len(points)} 个点生成 BEV")
        
        # 获取像素坐标
        rows, cols = self._point_to_pixel(filtered)
        
        # ---- 高度图 (Height Map) ----
        # 每个像素取该区域内最高点的 Z 坐标
        height_map = np.full((self.bev_height, self.bev_width), self.z_range[0], dtype=np.float32)
        np.maximum.at(height_map, (rows, cols), filtered[:, 2])
        
        # ---- 密度图 (Density Map) ----
        # 每个像素统计该区域内的点数
        density_map = np.zeros((self.bev_height, self.bev_width), dtype=np.float32)
        np.add.at(density_map, (rows, cols), 1)
        
        # ---- 强度图 (Intensity Map) ----
        # 每个像素取该区域内点的平均反射强度
        intensity_sum = np.zeros((self.bev_height, self.bev_width), dtype=np.float32)
        np.add.at(intensity_sum, (rows, cols), filtered[:, 3])
        
        # 避免除以 0
        intensity_map = np.zeros_like(intensity_sum)
        valid = density_map > 0
        intensity_map[valid] = intensity_sum[valid] / density_map[valid]
        
        return height_map, density_map, intensity_map
    
    def to_rgb(
        self,
        height_map: np.ndarray,
        density_map: np.ndarray,
        intensity_map: np.ndarray,
    ) -> np.ndarray:
        """
        将三通道 BEV 合成为 RGB 图像。
        
        通道映射:
            R: 高度（归一化）   — 高处亮，低处暗
            G: 密度（对数归一化）— 点多亮，点少暗
            B: 强度（归一化）   — 高反射亮，低反射暗
        
        参数:
            height_map: 高度图
            density_map: 密度图
            intensity_map: 强度图
        
        返回:
            np.ndarray: RGB 图像 (H, W, 3)，值域 [0, 255]
        """
        # 归一化高度
        h_min, h_max = self.z_range
        height_norm = np.clip((height_map - h_min) / (h_max - h_min), 0, 1)
        
        # 对数归一化密度（密度变化范围大，用对数压缩）
        density_log = np.log1p(density_map)  # log(1 + x) 避免 log(0)
        d_max = density_log.max() if density_log.max() > 0 else 1
        density_norm = density_log / d_max
        
        # 归一化强度
        i_max = intensity_map.max() if intensity_map.max() > 0 else 1
        intensity_norm = np.clip(intensity_map / i_max, 0, 1)
        
        # 合成 RGB
        rgb = np.stack([
            (height_norm * 255).astype(np.uint8),
            (density_norm * 255).astype(np.uint8),
            (intensity_norm * 255).astype(np.uint8),
        ], axis=-1)
        
        return rgb
    
    def world_to_pixel(self, x: float, y: float) -> Tuple[int, int]:
        """
        将世界坐标（米）转换为 BEV 图像像素坐标。
        
        参数:
            x (float): X 坐标（米）
            y (float): Y 坐标（米）
        
        返回:
            tuple: (row, col) 像素坐标
        """
        row = int((self.x_range[1] - x) / self.resolution)
        col = int((self.y_range[1] - y) / self.resolution)
        row = np.clip(row, 0, self.bev_height - 1)
        col = np.clip(col, 0, self.bev_width - 1)
        return row, col
