"""
boxes.py — 3D 标注框处理模块
===============================
处理 nuScenes 的 3D 标注框（bounding box），支持坐标系转换和角点计算。

3D Box 的表示:
    - center: [x, y, z] 中心点坐标（全局坐标系）
    - size: [width, length, height]
        - width (W):  Y 方向
        - length (L): X 方向  
        - height (H): Z 方向
    - orientation: Quaternion [w, x, y, z]
        - 绕 Z 轴的旋转角度称为 yaw 角

3D Box 的 8 个角点编号:
        7 -------- 6
       /|         /|
      4 -------- 5 |     Z(上)
      | |        | |     |
      | 3 -------| 2     |_____ X(前)
      |/         |/     /
      0 -------- 1     Y(左)
"""

import numpy as np
from pyquaternion import Quaternion
from typing import List, Tuple

from .transforms import (
    transform_matrix,
    get_global_to_ego_transform,
    get_ego_to_sensor_transform,
    apply_transform,
    camera_to_image,
)


class Box3D:
    """
    3D 标注框类。
    
    封装 nuScenes 的 sample_annotation 数据，提供:
        - 角点计算
        - 坐标系转换
        - 底面角点（用于 BEV 显示）
        - 投影到图像平面
    
    使用示例:
        box = Box3D.from_annotation(ann_record)
        corners = box.corners()  # 8 个角点
        box_ego = box.transform_to_ego(ego_pose_record)
    """
    
    def __init__(self, center, size, orientation, label='unknown', score=1.0):
        """
        参数:
            center (list/np.ndarray): [x, y, z] 中心点坐标
            size (list/np.ndarray): [width, length, height]
            orientation (Quaternion): 旋转四元数
            label (str): 类别名称
            score (float): 置信度分数
        """
        self.center = np.array(center, dtype=np.float64)
        self.size = np.array(size, dtype=np.float64)
        self.orientation = orientation if isinstance(orientation, Quaternion) else Quaternion(orientation)
        self.label = label
        self.score = score
    
    @classmethod
    def from_annotation(cls, ann_record: dict) -> 'Box3D':
        """
        从 nuScenes sample_annotation 记录创建 Box3D。
        
        参数:
            ann_record (dict): nuScenes sample_annotation 记录
        
        返回:
            Box3D: 3D 标注框对象
        """
        return cls(
            center=ann_record['translation'],
            size=ann_record['size'],
            orientation=Quaternion(ann_record['rotation']),
            label=ann_record.get('category_name', 'unknown'),
        )
    
    @property
    def yaw(self) -> float:
        """
        获取 yaw 角（绕 Z 轴的旋转角度，弧度）。
        
        yaw 角是自动驾驶中最常用的朝向表示:
            - 0°: 朝向 X 轴正方向（正前方）
            - 90°: 朝向 Y 轴正方向（左方）
            - -90°: 朝向 Y 轴负方向（右方）
            - 180°: 朝向 X 轴负方向（后方）
        """
        # 从四元数提取 yaw 角
        # yaw_pitch_roll 返回 (yaw, pitch, roll)
        return self.orientation.yaw_pitch_roll[0]
    
    def corners(self) -> np.ndarray:
        """
        计算 3D Box 的 8 个角点坐标。
        
        返回:
            np.ndarray: 形状 (8, 3) 的角点坐标
            
        角点编号（俯视图）:
            3 ---- 2     
            |      |     前方 → X
            0 ---- 1     左方 → Y
        
        底面: 0,1,2,3 (z = center_z - h/2)
        顶面: 4,5,6,7 (z = center_z + h/2)
        """
        w, l, h = self.size  # width(Y), length(X), height(Z)
        
        # 在 box 局部坐标系中定义 8 个角点（中心在原点）
        # nuScenes 的 size 定义: [width(Y), length(X), height(Z)]
        x_half = l / 2
        y_half = w / 2
        z_half = h / 2
        
        corners = np.array([
            [-x_half, -y_half, -z_half],  # 0: 右后下
            [ x_half, -y_half, -z_half],  # 1: 右前下
            [ x_half,  y_half, -z_half],  # 2: 左前下
            [-x_half,  y_half, -z_half],  # 3: 左后下
            [-x_half, -y_half,  z_half],  # 4: 右后上
            [ x_half, -y_half,  z_half],  # 5: 右前上
            [ x_half,  y_half,  z_half],  # 6: 左前上
            [-x_half,  y_half,  z_half],  # 7: 左后上
        ])
        
        # 应用旋转
        rotation_matrix = self.orientation.rotation_matrix
        corners = (rotation_matrix @ corners.T).T
        
        # 应用平移
        corners += self.center
        
        return corners
    
    def bottom_corners(self) -> np.ndarray:
        """
        获取底面的 4 个角点（用于 BEV 俯视图显示）。
        
        返回:
            np.ndarray: 形状 (4, 3) 的角点坐标
        """
        all_corners = self.corners()
        return all_corners[:4]  # 底面角点: 0, 1, 2, 3
    
    def copy(self) -> 'Box3D':
        """创建副本"""
        return Box3D(
            center=self.center.copy(),
            size=self.size.copy(),
            orientation=Quaternion(self.orientation),
            label=self.label,
            score=self.score,
        )
    
    def translate(self, translation: np.ndarray):
        """平移 box"""
        self.center += np.array(translation)
    
    def rotate(self, quaternion: Quaternion):
        """旋转 box（绕原点）"""
        self.center = quaternion.rotation_matrix @ self.center
        self.orientation = quaternion * self.orientation
    
    def transform(self, transform_mat: np.ndarray):
        """
        应用 4x4 变换矩阵到 box。
        
        参数:
            transform_mat (np.ndarray): 4x4 齐次变换矩阵
        """
        # 变换中心点
        center_homo = np.append(self.center, 1.0)
        self.center = (transform_mat @ center_homo)[:3]
        
        # 变换旋转（提取变换矩阵中的旋转部分）
        rot_mat = transform_mat[:3, :3]
        self.orientation = Quaternion(matrix=rot_mat) * self.orientation
    
    def project_to_image(self, camera_intrinsic: np.ndarray) -> np.ndarray:
        """
        将 3D box 的 8 个角点投影到图像平面。
        
        注意: box 必须已经在 Camera 坐标系下！
        
        参数:
            camera_intrinsic (np.ndarray): 3x3 相机内参矩阵
        
        返回:
            np.ndarray: 形状 (8, 2) 的图像坐标 [u, v]
        """
        corners_3d = self.corners()
        projected = camera_to_image(corners_3d, camera_intrinsic)
        return projected[:, :2]  # 只返回 u, v


def annotations_to_boxes(annotations: List[dict]) -> List[Box3D]:
    """
    将 nuScenes 标注列表转换为 Box3D 对象列表。
    
    参数:
        annotations (list): nuScenes sample_annotation 记录列表
    
    返回:
        list[Box3D]: Box3D 对象列表
    """
    return [Box3D.from_annotation(ann) for ann in annotations]


def transform_boxes_to_ego(
    boxes: List[Box3D],
    ego_pose_record: dict
) -> List[Box3D]:
    """
    将 boxes 从全局坐标系转换到 Ego 坐标系。
    
    参数:
        boxes (list[Box3D]): 全局坐标系下的 box 列表
        ego_pose_record (dict): ego_pose 记录
    
    返回:
        list[Box3D]: Ego 坐标系下的 box 列表
    """
    T_global_to_ego = get_global_to_ego_transform(ego_pose_record)
    
    result = []
    for box in boxes:
        b = box.copy()
        b.transform(T_global_to_ego)
        result.append(b)
    
    return result


def transform_boxes_to_camera(
    boxes: List[Box3D],
    ego_pose_record: dict,
    camera_calib_record: dict
) -> List[Box3D]:
    """
    将 boxes 从全局坐标系转换到 Camera 坐标系。
    
    变换链: Global → Ego → Camera
    
    参数:
        boxes (list[Box3D]): 全局坐标系下的 box 列表
        ego_pose_record (dict): ego_pose 记录
        camera_calib_record (dict): Camera 的 calibrated_sensor 记录
    
    返回:
        list[Box3D]: Camera 坐标系下的 box 列表
    """
    T_global_to_ego = get_global_to_ego_transform(ego_pose_record)
    T_ego_to_cam = get_ego_to_sensor_transform(camera_calib_record)
    
    T_global_to_cam = T_ego_to_cam @ T_global_to_ego
    
    result = []
    for box in boxes:
        b = box.copy()
        b.transform(T_global_to_cam)
        result.append(b)
    
    return result
