"""
path_utils.py — 路径工具
=========================
管理输出目录的创建和路径拼接。
确保所有输出统一保存到 outputs/ 目录下对应的子目录。

使用示例:
    from src.utils.path_utils import ensure_output_dirs, get_output_path
    ensure_output_dirs()  # 创建所有输出目录
    path = get_output_path("images", "sample_cameras_001.jpg")
"""

import os
from .config import get_paths_config, get_project_root


def ensure_output_dirs():
    """
    创建所有输出目录（如果不存在）。
    
    会创建以下目录:
        outputs/images/       — 摄像头图像、可视化图片
        outputs/bev/          — BEV 鸟瞰图
        outputs/projections/  — LiDAR 投影到相机的图片
        outputs/predictions/  — 3D 检测推理结果
    """
    paths_config = get_paths_config()
    project_root = get_project_root()
    
    output_dirs = [
        paths_config.get('output_images', 'outputs/images'),
        paths_config.get('output_bev', 'outputs/bev'),
        paths_config.get('output_projections', 'outputs/projections'),
        paths_config.get('output_predictions', 'outputs/predictions'),
    ]
    
    for d in output_dirs:
        full_path = os.path.join(project_root, d)
        os.makedirs(full_path, exist_ok=True)


def get_output_path(subdir, filename):
    """
    获取输出文件的完整路径。
    
    参数:
        subdir (str): 子目录名，如 "images", "bev", "projections", "predictions"
        filename (str): 文件名，如 "sample_cameras_001.jpg"
    
    返回:
        str: 输出文件的完整绝对路径
    
    示例:
        >>> get_output_path("images", "sample.jpg")
        "/path/to/project/outputs/images/sample.jpg"
    """
    paths_config = get_paths_config()
    project_root = get_project_root()
    
    # 根据 subdir 映射到配置中的路径
    subdir_mapping = {
        'images': paths_config.get('output_images', 'outputs/images'),
        'bev': paths_config.get('output_bev', 'outputs/bev'),
        'projections': paths_config.get('output_projections', 'outputs/projections'),
        'predictions': paths_config.get('output_predictions', 'outputs/predictions'),
    }
    
    output_dir = subdir_mapping.get(subdir, os.path.join('outputs', subdir))
    full_dir = os.path.join(project_root, output_dir)
    os.makedirs(full_dir, exist_ok=True)
    
    return os.path.join(full_dir, filename)


def get_nuscenes_dataroot():
    """
    获取 nuScenes 数据集根目录路径。
    
    返回:
        str: nuScenes 数据集的绝对路径
    
    异常:
        如果路径不存在，打印警告但不抛出异常
    """
    paths_config = get_paths_config()
    dataroot = paths_config['nuscenes_dataroot']
    
    if not os.path.exists(dataroot):
        print(f"\n⚠️  警告: nuScenes 数据目录不存在: {dataroot}")
        print(f"   请下载 nuScenes mini 数据集并解压到该路径。")
        print(f"   下载地址: https://www.nuscenes.org/nuscenes#download")
        print(f"   或修改 configs/paths.yaml 中的 nuscenes_dataroot\n")
    
    return dataroot


def get_nuscenes_version():
    """
    获取 nuScenes 数据集版本名称。
    
    返回:
        str: 版本名，如 "v1.0-mini"
    """
    paths_config = get_paths_config()
    return paths_config.get('nuscenes_version', 'v1.0-mini')
