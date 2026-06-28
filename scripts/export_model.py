"""
scripts/export_model.py — 独立打包导出训练好的 3D 检测模型
==========================================================
读取最新训练的 checkpoint，结合配置信息，打包为一个自包含的 model_exported.pth 文件。
（注：07_train_baseline.py 在训练结束时也会自动执行此逻辑）

运行命令:
    python scripts/export_model.py --checkpoint outputs/predictions/train_results/latest.pth
"""

import sys
import os
import argparse
import torch

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from src.utils.config import get_model_config

def parse_args():
    parser = argparse.ArgumentParser(description="Export Trained Simple PointPillars Model")
    parser.add_argument("--checkpoint", type=str, default=None, help="Path to checkpoint file to export")
    parser.add_argument("--out", type=str, default=None, help="Output file path (default: model_exported.pth in same dir)")
    return parser.parse_args()

def main():
    args = parse_args()
    model_cfg = get_model_config()
    det_cfg = model_cfg.get('detection', {})
    pp_cfg = model_cfg.get('pointpillars', {})

    work_dir = os.path.join(PROJECT_ROOT, det_cfg.get('work_dir', 'outputs/predictions/train_results'))
    
    ckpt_path = args.checkpoint if args.checkpoint else os.path.join(work_dir, "latest.pth")
    if not os.path.exists(ckpt_path):
        print(f"❌ 找不到 checkpoint: {ckpt_path}")
        print("请先完成模型训练！")
        return

    out_path = args.out if args.out else os.path.join(os.path.dirname(ckpt_path), "model_exported.pth")

    print(f"⏳ 正在读取 Checkpoint: {ckpt_path}...")
    checkpoint = torch.load(ckpt_path, map_location='cpu', weights_only=False)
    
    if 'model_state_dict' in checkpoint:
        state_dict = checkpoint['model_state_dict']
        classes = checkpoint.get('classes', ['car', 'pedestrian', 'bicycle', 'bus', 'truck'])
        epoch = checkpoint.get('epoch', 'unknown')
        loss = checkpoint.get('loss', 'unknown')
    else:
        state_dict = checkpoint
        classes = ['car', 'pedestrian', 'bicycle', 'bus', 'truck']
        epoch = 'unknown'
        loss = 'unknown'

    export_dict = {
        'model_state_dict': state_dict,
        'model_config': {
            'point_cloud_range': pp_cfg.get('point_cloud_range', [-51.2, -51.2, -5.0, 51.2, 51.2, 3.0]),
            'voxel_size': pp_cfg.get('voxel_size', [0.2, 0.2, 8.0]),
            'num_classes': len(classes),
            'classes': classes,
        },
        'training_info': {
            'epochs_trained': epoch,
            'final_loss': loss,
        }
    }

    torch.save(export_dict, out_path)
    print(f"✅ 模型打包导出成功！")
    print(f"📦 导出路径: {out_path}")
    print(f"   - 包含的类别: {classes}")
    print(f"   - 训练 Epoch: {epoch}")

if __name__ == '__main__':
    main()
