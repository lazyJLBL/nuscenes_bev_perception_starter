"""
06_prepare_detection_baseline.py — 准备 3D 检测 Baseline 数据
==========================================================
为自包含的 Simple PointPillars 检测器准备数据（切分 train/val splits）。

运行命令:
    python scripts/06_prepare_detection_baseline.py --execute
"""

import sys
import os
import argparse
import pickle
from tqdm import tqdm

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from src.utils.logger import print_header, print_separator
from src.utils.config import get_paths_config
from nuscenes.nuscenes import NuScenes
from nuscenes.utils.splits import create_splits_scenes

def parse_args():
    parser = argparse.ArgumentParser(description="Prepare data for Simple PointPillars")
    parser.add_argument("--execute", action="store_true", help="Execute data preparation")
    return parser.parse_args()

def prepare_data():
    paths = get_paths_config()
    dataroot = paths.get('nuscenes_dataroot')
    version = paths.get('nuscenes_version', 'v1.0-mini')
    
    print(f"📌 加载 nuScenes 数据集: {dataroot} ({version})")
    nusc = NuScenes(version=version, dataroot=dataroot, verbose=True)
    
    print("\n📌 生成 Train / Val Splits")
    # v1.0-mini 使用 mini_train 和 mini_val
    split_name = 'mini_train' if 'mini' in version else 'train'
    val_split_name = 'mini_val' if 'mini' in version else 'val'
    
    splits = create_splits_scenes()
    train_scenes = splits[split_name]
    val_scenes = splits[val_split_name]
    
    train_tokens = []
    val_tokens = []
    
    print("正在收集 Sample Tokens...")
    for scene in nusc.scene:
        scene_name = scene['name']
        is_train = scene_name in train_scenes
        is_val = scene_name in val_scenes
        
        if not is_train and not is_val:
            continue
            
        current_sample_token = scene['first_sample_token']
        while current_sample_token != '':
            if is_train:
                train_tokens.append(current_sample_token)
            else:
                val_tokens.append(current_sample_token)
                
            sample = nusc.get('sample', current_sample_token)
            current_sample_token = sample['next']
            
    print(f"收集到 {len(train_tokens)} 个训练样本")
    print(f"收集到 {len(val_tokens)} 个验证样本")
    
    # Save tokens
    train_file = os.path.join(PROJECT_ROOT, "nuscenes_mini_train_tokens.pkl")
    val_file = os.path.join(PROJECT_ROOT, "nuscenes_mini_val_tokens.pkl")
    
    with open(train_file, "wb") as f:
        pickle.dump(train_tokens, f)
    with open(val_file, "wb") as f:
        pickle.dump(val_tokens, f)
        
    print(f"\n✅ 数据准备完成，Token 列表已保存至:")
    print(f"   - {train_file}")
    print(f"   - {val_file}")

def main():
    args = parse_args()
    print_header("3D 检测 Baseline 准备")
    
    if not args.execute:
        print("""
📌 提示: 当前为预览模式。
请使用 --execute 参数运行，以真正执行数据准备流程（提取 train/val splits 并保存为 pkl 文件）。

运行命令:
    python scripts/06_prepare_detection_baseline.py --execute
""")
        return
        
    prepare_data()

if __name__ == '__main__':
    main()

