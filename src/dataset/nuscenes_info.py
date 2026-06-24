"""
nuscenes_info.py — nuScenes 数据集信息打印工具
================================================
提供格式化的数据集信息打印功能，帮助新手了解 nuScenes 的数据结构。
"""

import os
from typing import Optional


def print_sample_info(nusc, sample_token: str):
    """
    格式化打印一个 sample 的详细信息。
    
    参数:
        nusc: NuScenes 对象
        sample_token (str): sample token
    """
    sample = nusc.get('sample', sample_token)
    
    print(f"\n📋 Sample 详细信息:")
    print(f"   Token:     {sample['token']}")
    print(f"   时间戳:    {sample['timestamp']}")
    print(f"   场景 Token: {sample['scene_token']}")
    print(f"   标注框数:  {len(sample['anns'])}")
    
    # 打印所有传感器数据
    print(f"\n   传感器数据:")
    for sensor_name, sd_token in sample['data'].items():
        sd_record = nusc.get('sample_data', sd_token)
        print(f"   - {sensor_name:20s} -> {sd_record['filename']}")


def print_scene_info(nusc, scene_index: int = 0):
    """
    格式化打印一个 scene 的详细信息。
    
    参数:
        nusc: NuScenes 对象  
        scene_index (int): scene 索引
    """
    scene = nusc.scene[scene_index]
    
    print(f"\n🎬 Scene 详细信息:")
    print(f"   名称:      {scene['name']}")
    print(f"   描述:      {scene['description']}")
    print(f"   Token:     {scene['token']}")
    print(f"   样本数:    {scene['nbr_samples']}")
    print(f"   第一帧 Token: {scene['first_sample_token']}")
    print(f"   最后帧 Token: {scene['last_sample_token']}")


def print_annotation_info(nusc, ann_record: dict):
    """
    格式化打印一个标注框的信息。
    
    参数:
        nusc: NuScenes 对象
        ann_record (dict): sample_annotation 记录
    """
    print(f"   - 类别: {ann_record['category_name']}")
    print(f"     中心: [{ann_record['translation'][0]:.2f}, "
          f"{ann_record['translation'][1]:.2f}, "
          f"{ann_record['translation'][2]:.2f}]")
    print(f"     尺寸 (宽×长×高): [{ann_record['size'][0]:.2f}, "
          f"{ann_record['size'][1]:.2f}, "
          f"{ann_record['size'][2]:.2f}]")
    print(f"     LiDAR 点数: {ann_record['num_lidar_pts']}")
    print(f"     Radar 点数: {ann_record['num_radar_pts']}")


def print_sensor_info(nusc, sample_token: str, sensor_channel: str):
    """
    打印某个传感器的完整信息链。
    
    参数:
        nusc: NuScenes 对象
        sample_token (str): sample token
        sensor_channel (str): 传感器通道名
    """
    sample = nusc.get('sample', sample_token)
    sd_token = sample['data'][sensor_channel]
    sd_record = nusc.get('sample_data', sd_token)
    cal_sensor = nusc.get('calibrated_sensor', sd_record['calibrated_sensor_token'])
    ego_pose = nusc.get('ego_pose', sd_record['ego_pose_token'])
    
    print(f"\n🔧 传感器 {sensor_channel} 信息链:")
    print(f"   sample_data token:       {sd_token}")
    print(f"   文件名:                  {sd_record['filename']}")
    print(f"   calibrated_sensor token: {sd_record['calibrated_sensor_token']}")
    print(f"   ego_pose token:          {sd_record['ego_pose_token']}")
    
    print(f"\n   传感器标定 (calibrated_sensor):")
    print(f"   - 平移 (translation): {cal_sensor['translation']}")
    print(f"   - 旋转 (rotation):    {cal_sensor['rotation']}")
    if cal_sensor.get('camera_intrinsic'):
        print(f"   - 相机内参 (camera_intrinsic): 3x3 矩阵")
    
    print(f"\n   自车位姿 (ego_pose):")
    print(f"   - 平移 (translation): [{ego_pose['translation'][0]:.2f}, "
          f"{ego_pose['translation'][1]:.2f}, {ego_pose['translation'][2]:.2f}]")
    print(f"   - 旋转 (rotation):    [{ego_pose['rotation'][0]:.4f}, "
          f"{ego_pose['rotation'][1]:.4f}, "
          f"{ego_pose['rotation'][2]:.4f}, "
          f"{ego_pose['rotation'][3]:.4f}]")
