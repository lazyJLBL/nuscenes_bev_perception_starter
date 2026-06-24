"""
transforms.py — 坐标系转换核心模块
=====================================
实现自动驾驶中所有关键的坐标系转换函数。

坐标系变换链（从 LiDAR 点到图像像素的完整链路）:
    LiDAR 坐标系
        ↓ (calibrated_sensor: LiDAR → Ego)
    Ego Vehicle 坐标系
        ↓ (ego_pose: Ego → Global)
    全局坐标系 (Global)
        ↓ (ego_pose⁻¹: Global → Ego，注意这里用 Camera 时刻的 ego_pose)
    Ego Vehicle 坐标系（Camera 时刻）
        ↓ (calibrated_sensor⁻¹: Ego → Camera)
    Camera 坐标系
        ↓ (camera_intrinsic: 3D → 2D)
    图像像素坐标系

关键概念:
    - 齐次坐标: 在 3D 坐标 [x, y, z] 后加 1 变成 [x, y, z, 1]，便于用 4x4 矩阵同时表示旋转和平移
    - 四元数 (Quaternion): [w, x, y, z] 格式，表示 3D 旋转，比欧拉角更稳定
    - 变换矩阵: 4x4 矩阵，包含 3x3 旋转矩阵和 3x1 平移向量
"""

import numpy as np
from pyquaternion import Quaternion
from typing import List, Tuple, Optional


def transform_matrix(
    translation: List[float],
    rotation: List[float],
    inverse: bool = False
) -> np.ndarray:
    """
    构建 4x4 齐次变换矩阵。
    
    变换矩阵的结构:
        ┌         ┐
        │ R  t    │   R: 3x3 旋转矩阵
        │ 0  1    │   t: 3x1 平移向量
        └         ┘
    
    参数:
        translation (list): [x, y, z] 平移向量
        rotation (list): [w, x, y, z] 四元数旋转
        inverse (bool): 是否返回逆矩阵
                        True: 从目标坐标系到源坐标系的变换
                        False: 从源坐标系到目标坐标系的变换
    
    返回:
        np.ndarray: 4x4 齐次变换矩阵
    
    示例:
        >>> # 构建 LiDAR 到 Ego 的变换矩阵
        >>> T = transform_matrix(cal_sensor['translation'], cal_sensor['rotation'])
        >>> # 构建 Ego 到 LiDAR 的逆变换矩阵  
        >>> T_inv = transform_matrix(cal_sensor['translation'], cal_sensor['rotation'], inverse=True)
    """
    # 初始化 4x4 单位矩阵
    tm = np.eye(4)
    
    # 从四元数构造旋转矩阵
    # Quaternion 类接受 [w, x, y, z] 格式的四元数
    rotation_matrix = Quaternion(rotation).rotation_matrix  # 3x3
    
    if inverse:
        # 逆变换: T⁻¹ = [R^T  -R^T·t]
        #                [0      1    ]
        # R 是正交矩阵，所以 R⁻¹ = R^T（转置）
        tm[:3, :3] = rotation_matrix.T
        tm[:3, 3] = -(rotation_matrix.T @ np.array(translation))
    else:
        # 正变换: T = [R  t]
        #             [0  1]
        tm[:3, :3] = rotation_matrix
        tm[:3, 3] = np.array(translation)
    
    return tm


def get_sensor_to_ego_transform(calibrated_sensor_record: dict) -> np.ndarray:
    """
    获取 传感器坐标系 → Ego Vehicle 坐标系 的变换矩阵。
    
    calibrated_sensor 记录了传感器安装在车上的位置和朝向。
    
    参数:
        calibrated_sensor_record (dict): nuScenes calibrated_sensor 表的一条记录
            包含 'translation' 和 'rotation' 字段
    
    返回:
        np.ndarray: 4x4 变换矩阵 (Sensor → Ego)
    """
    return transform_matrix(
        calibrated_sensor_record['translation'],
        calibrated_sensor_record['rotation'],
        inverse=False,
    )


def get_ego_to_sensor_transform(calibrated_sensor_record: dict) -> np.ndarray:
    """
    获取 Ego Vehicle 坐标系 → 传感器坐标系 的变换矩阵（逆变换）。
    
    参数:
        calibrated_sensor_record (dict): nuScenes calibrated_sensor 表的一条记录
    
    返回:
        np.ndarray: 4x4 变换矩阵 (Ego → Sensor)
    """
    return transform_matrix(
        calibrated_sensor_record['translation'],
        calibrated_sensor_record['rotation'],
        inverse=True,
    )


def get_ego_to_global_transform(ego_pose_record: dict) -> np.ndarray:
    """
    获取 Ego Vehicle 坐标系 → 全局坐标系 的变换矩阵。
    
    ego_pose 记录了某个时刻车辆在全局坐标系中的位姿。
    
    参数:
        ego_pose_record (dict): nuScenes ego_pose 表的一条记录
            包含 'translation' 和 'rotation' 字段
    
    返回:
        np.ndarray: 4x4 变换矩阵 (Ego → Global)
    """
    return transform_matrix(
        ego_pose_record['translation'],
        ego_pose_record['rotation'],
        inverse=False,
    )


def get_global_to_ego_transform(ego_pose_record: dict) -> np.ndarray:
    """
    获取 全局坐标系 → Ego Vehicle 坐标系 的变换矩阵（逆变换）。
    
    参数:
        ego_pose_record (dict): nuScenes ego_pose 表的一条记录
    
    返回:
        np.ndarray: 4x4 变换矩阵 (Global → Ego)
    """
    return transform_matrix(
        ego_pose_record['translation'],
        ego_pose_record['rotation'],
        inverse=True,
    )


def apply_transform(points: np.ndarray, transform_mat: np.ndarray) -> np.ndarray:
    """
    将变换矩阵应用到点云上。
    
    参数:
        points (np.ndarray): 形状 (N, 3) 或 (N, 4+) 的点云，只使用前 3 列
        transform_mat (np.ndarray): 4x4 齐次变换矩阵
    
    返回:
        np.ndarray: 变换后的点云，形状 (N, 3)
    
    实现细节:
        1. 将 3D 点扩展为齐次坐标 [x, y, z, 1]
        2. 乘以 4x4 变换矩阵
        3. 取前 3 个分量得到变换后的坐标
    """
    n_points = points.shape[0]
    
    # 取前 3 列（x, y, z）
    xyz = points[:, :3]
    
    # 扩展为齐次坐标: [x, y, z] -> [x, y, z, 1]
    ones = np.ones((n_points, 1))
    xyz_homo = np.hstack([xyz, ones])  # (N, 4)
    
    # 变换: [4x4] @ [4xN] -> [4xN] -> [Nx4]
    transformed = (transform_mat @ xyz_homo.T).T  # (N, 4)
    
    # 保留原来的其它维度（如 intensity, ring）
    if points.shape[1] > 3:
        res = points.copy()
        res[:, :3] = transformed[:, :3]
        return res
    
    # 如果只有 3 列，直接返回
    return transformed[:, :3]


def lidar_to_ego(
    points: np.ndarray,
    lidar_calibrated_sensor: dict
) -> np.ndarray:
    """
    将点从 LiDAR 坐标系转换到 Ego Vehicle 坐标系。
    
    参数:
        points (np.ndarray): LiDAR 坐标系下的点云 (N, 3+)
        lidar_calibrated_sensor (dict): LiDAR 的 calibrated_sensor 记录
    
    返回:
        np.ndarray: Ego 坐标系下的点云 (N, 3)
    """
    T_sensor_to_ego = get_sensor_to_ego_transform(lidar_calibrated_sensor)
    return apply_transform(points, T_sensor_to_ego)


def ego_to_global(
    points: np.ndarray,
    ego_pose: dict
) -> np.ndarray:
    """
    将点从 Ego Vehicle 坐标系转换到全局坐标系。
    
    参数:
        points (np.ndarray): Ego 坐标系下的点云 (N, 3+)
        ego_pose (dict): ego_pose 记录
    
    返回:
        np.ndarray: 全局坐标系下的点云 (N, 3)
    """
    T_ego_to_global = get_ego_to_global_transform(ego_pose)
    return apply_transform(points, T_ego_to_global)


def global_to_ego(
    points: np.ndarray,
    ego_pose: dict
) -> np.ndarray:
    """
    将点从全局坐标系转换到 Ego Vehicle 坐标系。
    
    参数:
        points (np.ndarray): 全局坐标系下的点云 (N, 3+)
        ego_pose (dict): ego_pose 记录
    
    返回:
        np.ndarray: Ego 坐标系下的点云 (N, 3)
    """
    T_global_to_ego = get_global_to_ego_transform(ego_pose)
    return apply_transform(points, T_global_to_ego)


def ego_to_camera(
    points: np.ndarray,
    camera_calibrated_sensor: dict
) -> np.ndarray:
    """
    将点从 Ego Vehicle 坐标系转换到 Camera 坐标系。
    
    注意: 这是 calibrated_sensor 的逆变换！
    因为 calibrated_sensor 定义的是 Sensor → Ego，
    而我们需要 Ego → Sensor（Camera）。
    
    参数:
        points (np.ndarray): Ego 坐标系下的点云 (N, 3+)
        camera_calibrated_sensor (dict): Camera 的 calibrated_sensor 记录
    
    返回:
        np.ndarray: Camera 坐标系下的点云 (N, 3)
    """
    T_ego_to_camera = get_ego_to_sensor_transform(camera_calibrated_sensor)
    return apply_transform(points, T_ego_to_camera)


def camera_to_image(
    points_camera: np.ndarray,
    camera_intrinsic: np.ndarray
) -> np.ndarray:
    """
    将 Camera 坐标系下的 3D 点投影到 2D 图像平面。
    
    相机内参矩阵 K 的结构:
        ┌             ┐
        │ fx  0   cx  │   fx, fy: 焦距（像素）
        │ 0   fy  cy  │   cx, cy: 主点（图像中心）
        │ 0   0   1   │
        └             ┘
    
    投影公式:
        [u]     1    [fx  0  cx] [X]
        [v] = ──── × [0  fy  cy] [Y]
        [1]    Z     [0  0   1 ] [Z]
    
    参数:
        points_camera (np.ndarray): Camera 坐标系下的 3D 点 (N, 3+)
        camera_intrinsic (np.ndarray): 3x3 相机内参矩阵
    
    返回:
        np.ndarray: 图像坐标 (N, 3)，第三列为深度值 Z
                    前两列 (u, v) 为像素坐标
    """
    if points_camera.ndim != 2 or points_camera.shape[1] < 3:
        raise ValueError(f"points_camera 的形状必须为 (N, 3+) 但实际为 {points_camera.shape}")

    # 确保内参矩阵是 numpy 数组
    K = np.array(camera_intrinsic)
    
    # 只取前 3 列 xyz 参与投影
    xyz = points_camera[:, :3]
    
    # 投影: [3x3] @ [3xN] -> [3xN] -> [Nx3]
    projected = (K @ xyz.T).T  # (N, 3)
    
    # 从原始 Camera 坐标获取真实深度 Z，不使用 projected 中的修改值
    depths = points_camera[:, 2:3]  # (N, 1)
    
    # 避免除以 0
    depth_for_div = np.where(np.abs(depths) < 1e-6, 1e-6, depths)
    
    # 归一化: u, v = X/Z, Y/Z
    uv = projected[:, 0:2] / depth_for_div
    
    # 拼接返回 [u, v, depth]
    return np.hstack((uv, depths))


def lidar_to_camera(
    points: np.ndarray,
    lidar_calib: dict,
    lidar_ego_pose: dict,
    camera_calib: dict,
    camera_ego_pose: dict,
) -> np.ndarray:
    """
    将 LiDAR 点云转换到 Camera 坐标系。
    
    完整变换链:
        LiDAR → Ego(LiDAR时刻) → Global → Ego(Camera时刻) → Camera
    
    注意: 虽然对于 keyframe（sample），LiDAR 和 Camera 的 ego_pose 几乎相同，
    但为了严格正确，我们仍然经过完整的变换链。
    
    参数:
        points (np.ndarray): LiDAR 坐标系下的点云 (N, 3+)
        lidar_calib (dict): LiDAR 的 calibrated_sensor 记录
        lidar_ego_pose (dict): LiDAR 对应时刻的 ego_pose 记录
        camera_calib (dict): Camera 的 calibrated_sensor 记录
        camera_ego_pose (dict): Camera 对应时刻的 ego_pose 记录
    
    返回:
        np.ndarray: Camera 坐标系下的点云 (N, 3)
    """
    # 步骤 1: LiDAR → Ego (LiDAR 时刻)
    points_ego = lidar_to_ego(points, lidar_calib)
    
    # 步骤 2: Ego (LiDAR 时刻) → Global
    points_global = ego_to_global(points_ego, lidar_ego_pose)
    
    # 步骤 3: Global → Ego (Camera 时刻)
    points_ego_cam = global_to_ego(points_global, camera_ego_pose)
    
    # 步骤 4: Ego (Camera 时刻) → Camera
    points_camera = ego_to_camera(points_ego_cam, camera_calib)
    
    return points_camera


def project_lidar_to_image(
    points_camera: np.ndarray,
    camera_intrinsic: np.ndarray,
) -> np.ndarray:
    """
    将 Camera 坐标系下的点投影到图像平面。
    
    这是 camera_to_image 的别名，提供更直观的函数名。
    
    参数:
        points_camera (np.ndarray): Camera 坐标系下的 3D 点 (N, 3)
        camera_intrinsic (np.ndarray): 3x3 相机内参矩阵
    
    返回:
        np.ndarray: 图像坐标 (N, 3): [u, v, depth]
    """
    return camera_to_image(points_camera, camera_intrinsic)
