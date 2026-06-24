"""
config.py — 配置文件加载工具
==============================
统一加载 configs/ 下的 YAML 配置文件。
所有脚本通过此模块读取配置，确保路径和参数不写死在代码里。

使用示例:
    from src.utils.config import get_paths_config
    paths = get_paths_config()
    dataroot = paths['nuscenes_dataroot']
"""

import os
import yaml


def _get_project_root():
    """
    获取项目根目录路径。
    
    通过当前文件位置向上回溯到项目根目录。
    当前文件位于: src/utils/config.py
    项目根目录是: 向上 3 级目录
    """
    current_file = os.path.abspath(__file__)
    # src/utils/config.py -> src/utils -> src -> project_root
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
    return project_root


def load_config(config_name):
    """
    加载指定名称的 YAML 配置文件。
    
    参数:
        config_name (str): 配置文件名，不需要 .yaml 后缀
                          例如: "paths", "dataset", "model"
    
    返回:
        dict: 配置文件内容
    
    异常:
        FileNotFoundError: 配置文件不存在时抛出
    """
    project_root = _get_project_root()
    
    # 如果没有 .yaml 后缀，自动添加
    if not config_name.endswith('.yaml') and not config_name.endswith('.yml'):
        config_name = config_name + '.yaml'
    
    config_path = os.path.join(project_root, 'configs', config_name)
    
    if not os.path.exists(config_path):
        raise FileNotFoundError(
            f"配置文件不存在: {config_path}\n"
            f"请检查 configs/ 目录下是否有 {config_name} 文件。"
        )
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    return config


def get_paths_config():
    """
    加载路径配置 (configs/paths.yaml)。
    
    返回:
        dict: 包含 nuscenes_dataroot, nuscenes_version, output_root 等路径
    """
    return load_config('paths')


def get_dataset_config():
    """
    加载数据集配置 (configs/dataset.yaml)。
    
    返回:
        dict: 包含 camera_channels, lidar_channel, bev 参数等
    """
    return load_config('dataset')


def get_model_config():
    """
    加载模型配置 (configs/model.yaml)。
    
    返回:
        dict: 包含 baseline_model, detection_framework 等
    """
    return load_config('model')


def get_project_root():
    """
    获取项目根目录路径（公开接口）。
    
    返回:
        str: 项目根目录的绝对路径
    """
    return _get_project_root()
