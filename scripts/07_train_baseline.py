"""
07_train_baseline.py — 训练 3D 检测 Baseline (真实版)
==========================================================
使用 Focal Loss + SmoothL1 + 方向分类损失训练 SimplePointPillars。

运行命令:
    python scripts/07_train_baseline.py --execute --epochs 5 --batch-size 2
"""

import sys
import os
import argparse
import json
import time
import torch
from torch.utils.data import DataLoader

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from src.utils.logger import print_header, print_separator
from src.utils.config import get_paths_config, get_model_config
from nuscenes.nuscenes import NuScenes

from src.detection.simple_pillars import SimplePointPillars
from src.detection.nuscenes_dataset import NuScenesDetDataset, collate_fn
from src.detection.train_utils import train_one_epoch

def parse_args():
    parser = argparse.ArgumentParser(description="Train Simple PointPillars")
    parser.add_argument("--execute", action="store_true", help="Execute real training")
    parser.add_argument("--epochs", type=int, default=None, help="Number of epochs to train")
    parser.add_argument("--batch-size", type=int, default=None, help="Batch size")
    parser.add_argument("--workers", type=int, default=None, help="Number of dataloader workers")
    return parser.parse_args()

def main():
    args = parse_args()
    print_header("3D 检测 Baseline 训练 (真实 Focal Loss 版)")

    if not args.execute:
        print("""
📌 提示: 当前为预览模式。
请使用 --execute 参数运行，以真正执行训练流程。

运行命令示例:
    python scripts/07_train_baseline.py --execute --epochs 5 --batch-size 2
""")
        return

    paths_cfg = get_paths_config()
    model_cfg = get_model_config()
    det_cfg = model_cfg.get('detection', {})
    pp_cfg = model_cfg.get('pointpillars', {})

    # Merge args
    epochs = args.epochs if args.epochs is not None else det_cfg.get('epochs', 5)
    batch_size = args.batch_size if args.batch_size is not None else det_cfg.get('batch_size', 2)
    workers = args.workers if args.workers is not None else det_cfg.get('workers', 0)

    dataroot = paths_cfg.get('nuscenes_dataroot')
    version = paths_cfg.get('nuscenes_version', 'v1.0-mini')
    tokens_file = os.path.join(PROJECT_ROOT, "nuscenes_mini_train_tokens.pkl")

    if not os.path.exists(tokens_file):
        print(f"❌ 找不到 tokens 文件: {tokens_file}")
        print("请先运行: python scripts/06_prepare_detection_baseline.py --execute")
        return

    device_str = det_cfg.get('device', 'auto')
    if device_str == 'auto':
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    else:
        device = torch.device(device_str)

    classes = ['car', 'pedestrian', 'bicycle', 'bus', 'truck']

    print(f"📌 运行配置:")
    print(f"   - 设备: {device}")
    print(f"   - Epochs: {epochs}")
    print(f"   - Batch Size: {batch_size}")
    print(f"   - Workers: {workers}")
    print(f"   - 检测类别: {classes}")
    print_separator()

    # 1. Load dataset
    print("⏳ 初始化 NuScenes...")
    nusc = NuScenes(version=version, dataroot=dataroot, verbose=False)

    print("⏳ 初始化 Dataset...")
    train_dataset = NuScenesDetDataset(
        nusc=nusc,
        tokens_file=tokens_file,
        classes=classes,
        point_cloud_range=pp_cfg.get('point_cloud_range', [-51.2, -51.2, -5.0, 51.2, 51.2, 3.0]),
        voxel_size=pp_cfg.get('voxel_size', [0.2, 0.2, 8.0]),
        training=True
    )

    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True,
        num_workers=workers,
        collate_fn=collate_fn,
        drop_last=True
    )

    # 2. Init model (传入 classes 以便生成正确的 anchor 尺寸)
    print("⏳ 初始化 Model...")
    model = SimplePointPillars(
        point_cloud_range=pp_cfg.get('point_cloud_range', [-51.2, -51.2, -5.0, 51.2, 51.2, 3.0]),
        voxel_size=pp_cfg.get('voxel_size', [0.2, 0.2, 8.0]),
        num_classes=len(classes),
        classes=classes
    ).to(device)

    total_params = sum(p.numel() for p in model.parameters())
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"   - 模型参数量: {total_params:,} (可训练: {trainable_params:,})")
    print(f"   - 特征图尺寸: {model.feature_map_size}")
    print(f"   - Anchor 总数: {model.anchors.shape[0]:,}")

    optimizer = torch.optim.Adam(model.parameters(), lr=det_cfg.get('learning_rate', 0.001))

    # 3. Training Loop
    work_dir = os.path.join(PROJECT_ROOT, det_cfg.get('work_dir', 'outputs/predictions/train_results'))
    os.makedirs(work_dir, exist_ok=True)

    print_separator()
    print("🚀 开始训练...")

    best_loss = float('inf')
    for epoch in range(epochs):
        print(f"\n--- Epoch {epoch+1}/{epochs} ---")
        start_time = time.time()

        metrics = train_one_epoch(model, optimizer, train_loader, device, epoch+1)

        elapsed = time.time() - start_time
        print(f"  ⏱️ 耗时: {elapsed:.1f}s")

        # Save checkpoint
        ckpt_path = os.path.join(work_dir, f"epoch_{epoch+1}.pth")
        torch.save({
            'epoch': epoch + 1,
            'model_state_dict': model.state_dict(),
            'optimizer_state_dict': optimizer.state_dict(),
            'loss': metrics['loss'],
            'classes': classes,
            'point_cloud_range': pp_cfg.get('point_cloud_range', [-51.2, -51.2, -5.0, 51.2, 51.2, 3.0]),
            'voxel_size': pp_cfg.get('voxel_size', [0.2, 0.2, 8.0]),
        }, ckpt_path)
        print(f"  💾 Checkpoint: {ckpt_path}")

        if metrics['loss'] < best_loss:
            best_loss = metrics['loss']
            best_path = os.path.join(work_dir, "best.pth")
            torch.save(model.state_dict(), best_path)
            print(f"  ⭐ Best model saved! (loss={best_loss:.4f})")

    # Save final model as latest
    latest_path = os.path.join(work_dir, "latest.pth")
    torch.save(model.state_dict(), latest_path)

    # 导出自包含的模型文件
    export_path = os.path.join(work_dir, "model_exported.pth")
    torch.save({
        'model_state_dict': model.state_dict(),
        'model_config': {
            'point_cloud_range': pp_cfg.get('point_cloud_range', [-51.2, -51.2, -5.0, 51.2, 51.2, 3.0]),
            'voxel_size': pp_cfg.get('voxel_size', [0.2, 0.2, 8.0]),
            'num_classes': len(classes),
            'classes': classes,
        },
        'training_info': {
            'epochs': epochs,
            'final_loss': metrics['loss'],
            'best_loss': best_loss,
        }
    }, export_path)
    print(f"\n📦 Exported model: {export_path}")

    # Save training status
    status = {
        "status": "completed",
        "epochs": epochs,
        "final_loss": metrics['loss'],
        "best_loss": best_loss,
        "checkpoint": latest_path,
        "exported_model": export_path,
    }
    with open(os.path.join(work_dir, "training_status.json"), "w") as f:
        json.dump(status, f, indent=4)

    print_separator()
    print("🎉 训练完成！")
    print(f"   模型文件: {export_path}")
    print(f"   下一步: python scripts/08_inference_baseline.py --execute")

if __name__ == '__main__':
    main()
