"""
08_inference_baseline.py — 3D 检测 Baseline 推理与评估
==========================================================
加载训练好的 Simple PointPillars 模型，对验证集进行推理，并使用 nuScenes 官方评估器进行评估。

运行命令:
    python scripts/08_inference_baseline.py --execute
"""

import sys
import os
import argparse
import torch
from torch.utils.data import DataLoader

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from src.utils.logger import print_header, print_separator
from src.utils.config import get_paths_config, get_model_config
from nuscenes.nuscenes import NuScenes

from src.detection.simple_pillars import SimplePointPillars
from src.detection.nuscenes_dataset import NuScenesDetDataset, collate_fn
from src.detection.train_utils import inference, run_nuscenes_eval

def parse_args():
    parser = argparse.ArgumentParser(description="Inference Simple PointPillars")
    parser.add_argument("--execute", action="store_true", help="Execute real inference")
    parser.add_argument("--checkpoint", type=str, default=None, help="Path to checkpoint file")
    return parser.parse_args()

def main():
    args = parse_args()
    print_header("3D 检测 Baseline 推理与评估")

    if not args.execute:
        print("""
📌 提示: 当前为预览模式。
请使用 --execute 参数运行，以真正执行推理流程。

运行命令:
    python scripts/08_inference_baseline.py --execute
""")
        return

    paths_cfg = get_paths_config()
    model_cfg = get_model_config()
    det_cfg = model_cfg.get('detection', {})
    pp_cfg = model_cfg.get('pointpillars', {})

    dataroot = paths_cfg.get('nuscenes_dataroot')
    version = paths_cfg.get('nuscenes_version', 'v1.0-mini')
    tokens_file = os.path.join(PROJECT_ROOT, "nuscenes_mini_val_tokens.pkl")

    if not os.path.exists(tokens_file):
        print(f"❌ 找不到 tokens 文件: {tokens_file}")
        print("请先运行: python scripts/06_prepare_detection_baseline.py --execute")
        return

    work_dir = os.path.join(PROJECT_ROOT, det_cfg.get('work_dir', 'outputs/predictions/train_results'))

    # 优先加载导出的模型
    exported_path = os.path.join(work_dir, "model_exported.pth")
    ckpt_path = args.checkpoint if args.checkpoint else (
        exported_path if os.path.exists(exported_path) else os.path.join(work_dir, "latest.pth")
    )

    if not os.path.exists(ckpt_path):
        print(f"❌ 找不到 checkpoint: {ckpt_path}")
        print("请先运行: python scripts/07_train_baseline.py --execute")
        return

    device_str = det_cfg.get('device', 'auto')
    if device_str == 'auto':
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    else:
        device = torch.device(device_str)

    classes = ['car', 'pedestrian', 'bicycle', 'bus', 'truck']

    print(f"📌 运行配置:")
    print(f"   - 设备: {device}")
    print(f"   - Checkpoint: {ckpt_path}")
    print_separator()

    # 1. Load dataset
    print("⏳ 初始化 NuScenes...")
    nusc = NuScenes(version=version, dataroot=dataroot, verbose=False)

    print("⏳ 初始化 Val Dataset...")
    val_dataset = NuScenesDetDataset(
        nusc=nusc,
        tokens_file=tokens_file,
        classes=classes,
        point_cloud_range=pp_cfg.get('point_cloud_range', [-51.2, -51.2, -5.0, 51.2, 51.2, 3.0]),
        voxel_size=pp_cfg.get('voxel_size', [0.2, 0.2, 8.0]),
        training=False
    )

    val_loader = DataLoader(
        val_dataset,
        batch_size=1,
        shuffle=False,
        num_workers=0,
        collate_fn=collate_fn
    )

    # 2. Init model
    print("⏳ 初始化 Model 并加载权重...")
    model = SimplePointPillars(
        point_cloud_range=pp_cfg.get('point_cloud_range', [-51.2, -51.2, -5.0, 51.2, 51.2, 3.0]),
        voxel_size=pp_cfg.get('voxel_size', [0.2, 0.2, 8.0]),
        num_classes=len(classes),
        classes=classes
    ).to(device)

    checkpoint = torch.load(ckpt_path, map_location=device, weights_only=False)
    if 'model_state_dict' in checkpoint:
        model.load_state_dict(checkpoint['model_state_dict'])
        print(f"   ✅ 已加载导出模型 (epochs: {checkpoint.get('training_info', {}).get('epochs', '?')})")
    else:
        model.load_state_dict(checkpoint)

    # 3. Inference
    out_dir = os.path.dirname(os.path.join(PROJECT_ROOT, det_cfg.get('prediction_file', 'outputs/predictions/detection_results.json')))
    os.makedirs(out_dir, exist_ok=True)

    pred_file = os.path.join(PROJECT_ROOT, det_cfg.get('prediction_file', 'outputs/predictions/detection_results.json'))

    print_separator()
    inference(model, val_loader, device, classes, pred_file)

    # 4. Evaluation
    print_separator()
    eval_set = 'mini_val' if 'mini' in version else 'val'
    run_nuscenes_eval(nusc, pred_file, eval_set, out_dir)

    print_separator()
    print("🎉 推理与评估完成！")

if __name__ == '__main__':
    main()
