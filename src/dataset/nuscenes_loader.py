"""
nuscenes_loader.py — nuScenes 数据加载器
==========================================
封装 nuscenes-devkit，提供简洁的数据访问接口。

核心功能:
    - 加载 nuScenes 数据集（默认 v1.0-mini）
    - 获取 sample 的所有传感器数据路径
    - 获取 6 个环视摄像头图像路径
    - 获取 LiDAR 点云路径
    - 获取 sample 的 3D 标注框

关键概念（给新手的说明）:
    - nuScenes 数据以"表"的形式组织，类似数据库
    - scene: 一段 20 秒左右的驾驶场景
    - sample: 一个关键帧（keyframe），每 0.5 秒一个
    - sample_data: 某个传感器在某个时刻的数据
    - sample_annotation: 一个 3D 标注框
    - ego_pose: 车辆自身在全局坐标系下的位姿
    - calibrated_sensor: 传感器相对于车辆的标定信息
"""

import os
import numpy as np
from typing import Dict, List, Tuple, Optional

# nuscenes-devkit 是 nuScenes 官方提供的 Python 开发工具包
from nuscenes.nuscenes import NuScenes

import sys
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from src.utils.config import get_paths_config, get_dataset_config


class NuScenesLoader:
    """
    nuScenes 数据加载器。
    
    封装 nuscenes-devkit 的 NuScenes 类，提供更简洁的接口。
    
    使用示例:
        loader = NuScenesLoader()
        loader.print_dataset_info()
        
        sample = loader.get_first_sample()
        cam_paths = loader.get_camera_data(sample['token'])
        lidar_path = loader.get_lidar_data(sample['token'])
    """
    
    def __init__(self, dataroot=None, version=None, verbose=True):
        """
        初始化 NuScenes 数据加载器。
        
        参数:
            dataroot (str, optional): nuScenes 数据根目录，默认从 configs/paths.yaml 读取
            version (str, optional): 数据集版本，默认从 configs/paths.yaml 读取
            verbose (bool): 是否打印加载信息
        """
        paths_config = get_paths_config()
        
        self.dataroot = dataroot or paths_config['nuscenes_dataroot']
        self.version = version or paths_config.get('nuscenes_version', 'v1.0-mini')
        
        # 检查数据目录
        if not os.path.exists(self.dataroot):
            raise FileNotFoundError(
                f"\n❌ nuScenes 数据目录不存在: {self.dataroot}\n"
                f"请按照以下步骤操作:\n"
                f"1. 前往 https://www.nuscenes.org/nuscenes#download 下载 nuScenes mini\n"
                f"2. 解压到: {self.dataroot}\n"
                f"3. 或修改 configs/paths.yaml 中的 nuscenes_dataroot\n"
            )
        
        # 加载 nuScenes 数据集
        # NuScenes 类会读取所有 JSON 表文件并建立索引
        if verbose:
            print(f"正在加载 nuScenes {self.version} 数据集...")
            print(f"数据路径: {self.dataroot}")
        
        self.nusc = NuScenes(
            version=self.version,
            dataroot=self.dataroot,
            verbose=verbose
        )
        
        # 加载数据集配置
        self.dataset_config = get_dataset_config()
        self.camera_channels = self.dataset_config['camera_channels']
        self.lidar_channel = self.dataset_config['lidar_channel']
    
    def print_dataset_info(self):
        """
        打印数据集基本信息。
        
        输出内容:
            - scene（场景）数量
            - sample（关键帧）数量
            - sample_data（传感器数据）数量
            - sample_annotation（标注框）数量
        """
        print("\n📊 nuScenes 数据集信息:")
        print(f"   版本:              {self.version}")
        print(f"   数据路径:          {self.dataroot}")
        print(f"   场景 (scene) 数:   {len(self.nusc.scene)}")
        print(f"   关键帧 (sample) 数: {len(self.nusc.sample)}")
        print(f"   传感器数据 (sample_data) 数: {len(self.nusc.sample_data)}")
        print(f"   标注框 (sample_annotation) 数: {len(self.nusc.sample_annotation)}")
        print(f"   地图 (map) 数:     {len(self.nusc.map)}")
        print(f"   传感器 (sensor) 数: {len(self.nusc.sensor)}")
        print(f"   传感器标定 (calibrated_sensor) 数: {len(self.nusc.calibrated_sensor)}")
        print(f"   自车位姿 (ego_pose) 数: {len(self.nusc.ego_pose)}")
    
    def get_first_sample(self):
        """
        获取数据集中第一个 sample（关键帧）。
        
        返回:
            dict: sample 记录，包含 token、timestamp、data 等字段
        """
        return self.nusc.sample[0]
    
    def get_sample_by_token(self, sample_token: str):
        """
        通过 token 获取 sample。
        
        参数:
            sample_token (str): sample 的唯一标识符
        
        返回:
            dict: sample 记录
        """
        return self.nusc.get('sample', sample_token)
    
    def get_sample_data_paths(self, sample_token: str) -> Dict[str, str]:
        """
        获取某个 sample 的所有传感器文件路径。
        
        参数:
            sample_token (str): sample token
        
        返回:
            dict: {传感器名: 文件绝对路径}
            
        示例返回:
            {
                'CAM_FRONT': '/data/nuscenes/samples/CAM_FRONT/xxx.jpg',
                'CAM_FRONT_LEFT': '/data/nuscenes/samples/CAM_FRONT_LEFT/xxx.jpg',
                ...
                'LIDAR_TOP': '/data/nuscenes/samples/LIDAR_TOP/xxx.bin',
            }
        """
        sample = self.nusc.get('sample', sample_token)
        paths = {}
        
        # sample['data'] 是一个字典: {传感器名: sample_data_token}
        for sensor_name, sd_token in sample['data'].items():
            # 通过 sample_data token 获取文件名
            sd_record = self.nusc.get('sample_data', sd_token)
            # 拼接完整路径
            file_path = os.path.join(self.dataroot, sd_record['filename'])
            paths[sensor_name] = file_path
        
        return paths
    
    def get_camera_data(self, sample_token: str) -> Dict[str, str]:
        """
        获取 6 个环视摄像头图像路径。
        
        参数:
            sample_token (str): sample token
        
        返回:
            dict: {摄像头名: 图像文件路径}
            
        返回的 6 个摄像头:
            CAM_FRONT       - 正前方
            CAM_FRONT_LEFT  - 左前方
            CAM_FRONT_RIGHT - 右前方
            CAM_BACK        - 正后方
            CAM_BACK_LEFT   - 左后方
            CAM_BACK_RIGHT  - 右后方
        """
        all_paths = self.get_sample_data_paths(sample_token)
        camera_paths = {}
        
        for cam_name in self.camera_channels:
            if cam_name in all_paths:
                camera_paths[cam_name] = all_paths[cam_name]
            else:
                print(f"  ⚠️ 摄像头 {cam_name} 的数据未找到")
        
        return camera_paths
    
    def get_lidar_data(self, sample_token: str) -> str:
        """
        获取 LiDAR 点云文件路径。
        
        参数:
            sample_token (str): sample token
        
        返回:
            str: LiDAR 点云文件的绝对路径（.pcd.bin 格式）
            
        nuScenes LiDAR 数据格式说明:
            - 文件格式: .pcd.bin（二进制文件）
            - 每个点 5 个 float32 值: x, y, z, intensity, ring_index
            - x, y, z: 点在 LiDAR 坐标系下的三维坐标（单位: 米）
            - intensity: 反射强度
            - ring_index: 激光线束编号
        """
        all_paths = self.get_sample_data_paths(sample_token)
        lidar_path = all_paths.get(self.lidar_channel, None)
        
        if lidar_path is None:
            raise ValueError(f"未找到 {self.lidar_channel} 数据")
        
        return lidar_path
    
    def load_lidar_points(self, sample_token: str) -> np.ndarray:
        """
        加载 LiDAR 点云数据。
        
        参数:
            sample_token (str): sample token
        
        返回:
            np.ndarray: 形状为 (N, 5) 的点云数组
                        列分别为 [x, y, z, intensity, ring_index]
        """
        lidar_path = self.get_lidar_data(sample_token)
        
        if not os.path.exists(lidar_path):
            raise FileNotFoundError(f"LiDAR 文件不存在: {lidar_path}")
        
        # nuScenes 的 LiDAR 数据是 float32 二进制文件
        # 每个点有 5 个值: x, y, z, intensity, ring_index
        points = np.fromfile(lidar_path, dtype=np.float32).reshape(-1, 5)
        
        return points
    
    def get_annotations(self, sample_token: str) -> List[dict]:
        """
        获取某个 sample 的所有 3D 标注框。
        
        参数:
            sample_token (str): sample token
        
        返回:
            list[dict]: 标注框记录列表，每个记录包含:
                - token: 标注框唯一标识
                - sample_token: 所属 sample
                - instance_token: 物体实例标识（同一物体在不同帧有相同的 instance_token）
                - category_name: 类别名，如 "vehicle.car"
                - translation: [x, y, z] 中心点坐标（全局坐标系）
                - size: [width, length, height] 尺寸（米）
                - rotation: [w, x, y, z] 四元数旋转
                - visibility_token: 可见性级别
                - num_lidar_pts: box 内的 LiDAR 点数
                - num_radar_pts: box 内的 Radar 点数
        """
        sample = self.nusc.get('sample', sample_token)
        annotations = []
        
        # sample['anns'] 是标注框 token 的列表
        for ann_token in sample['anns']:
            ann_record = self.nusc.get('sample_annotation', ann_token)
            annotations.append(ann_record)
        
        return annotations
    
    def get_sample_detail(self, sample_token: str) -> dict:
        """
        获取 sample 的详细信息，包括所有传感器的 token。
        
        参数:
            sample_token (str): sample token
        
        返回:
            dict: 包含以下内容:
                - sample: sample 记录
                - camera_tokens: {摄像头名: sample_data_token}
                - lidar_token: LiDAR 的 sample_data_token
                - ego_poses: {传感器名: ego_pose 记录}
                - calibrated_sensors: {传感器名: calibrated_sensor 记录}
                - annotation_count: 标注框数量
        """
        sample = self.nusc.get('sample', sample_token)
        
        detail = {
            'sample': sample,
            'camera_tokens': {},
            'lidar_token': None,
            'ego_poses': {},
            'calibrated_sensors': {},
            'annotation_count': len(sample['anns']),
        }
        
        for sensor_name, sd_token in sample['data'].items():
            sd_record = self.nusc.get('sample_data', sd_token)
            
            # 获取 ego_pose（车辆在全局坐标系中的位姿）
            ego_pose = self.nusc.get('ego_pose', sd_record['ego_pose_token'])
            detail['ego_poses'][sensor_name] = ego_pose
            
            # 获取 calibrated_sensor（传感器相对于车辆的标定信息）
            cal_sensor = self.nusc.get('calibrated_sensor', sd_record['calibrated_sensor_token'])
            detail['calibrated_sensors'][sensor_name] = cal_sensor
            
            if sensor_name in self.camera_channels:
                detail['camera_tokens'][sensor_name] = sd_token
            elif sensor_name == self.lidar_channel:
                detail['lidar_token'] = sd_token
        
        return detail
    
    def get_sensor_records(self, sample_token: str, sensor_channel: str):
        """
        获取指定传感器的完整记录链。
        
        参数:
            sample_token (str): sample token
            sensor_channel (str): 传感器通道名，如 "CAM_FRONT", "LIDAR_TOP"
        
        返回:
            tuple: (sample_data_record, calibrated_sensor_record, ego_pose_record)
            
        这三个记录构成了从传感器坐标系到全局坐标系的完整变换链:
            传感器坐标系 --(calibrated_sensor)--> 车辆坐标系 --(ego_pose)--> 全局坐标系
        """
        sample = self.nusc.get('sample', sample_token)
        sd_token = sample['data'][sensor_channel]
        sd_record = self.nusc.get('sample_data', sd_token)
        
        cal_sensor = self.nusc.get('calibrated_sensor', sd_record['calibrated_sensor_token'])
        ego_pose = self.nusc.get('ego_pose', sd_record['ego_pose_token'])
        
        return sd_record, cal_sensor, ego_pose
