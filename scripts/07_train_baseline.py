"""
07_train_baseline.py — 训练 3D 检测 Baseline
===============================================
使用 MMDetection3D 训练 PointPillars 模型。

运行命令:
    python scripts/07_train_baseline.py

注意:
    1. 必须先运行 scripts/06_prepare_detection_baseline.py 准备数据
    2. 需要 GPU 支持（建议至少 8GB 显存）
    3. 使用 nuScenes mini 训练仅用于验证流程，不代表真实性能
    4. 如果显卡资源不足，可以减少 batch_size 或 epochs
"""

import sys
import os
import subprocess

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from src.utils.logger import print_header
from src.utils.config import get_paths_config, get_model_config


def check_prerequisites():
    """检查训练前提条件"""
    print("\n📌 检查前提条件...")
    
    # 检查 PyTorch 和 CUDA
    try:
        import torch
        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            gpu_mem = torch.cuda.get_device_properties(0).total_mem / 1024**3
            print(f"  ✅ GPU: {gpu_name} ({gpu_mem:.1f} GB)")
        else:
            print("  ⚠️  无 GPU 可用")
            print("     CPU 训练非常慢，建议:")
            print("     1. 减小 batch_size 到 1")
            print("     2. 减少 epochs 到 1-2")
            print("     3. 或使用预训练模型直接推理")
    except ImportError:
        print("  ❌ PyTorch 未安装")
        return False
    
    # 检查 MMDetection3D
    try:
        import mmdet3d
        print(f"  ✅ MMDetection3D: {mmdet3d.__version__}")
    except ImportError:
        print("  ❌ MMDetection3D 未安装")
        print("     请先运行 python scripts/06_prepare_detection_baseline.py")
        return False
    
    # 检查数据
    paths = get_paths_config()
    dataroot = paths['nuscenes_dataroot']
    if not os.path.exists(dataroot):
        print(f"  ❌ 数据目录不存在: {dataroot}")
        return False
    print(f"  ✅ 数据目录: {dataroot}")
    
    return True


def get_train_command():
    """
    生成 MMDetection3D 训练命令。
    
    返回:
        str: 训练命令字符串
    """
    paths = get_paths_config()
    model_config = get_model_config()
    dataroot = paths['nuscenes_dataroot']
    
    # MMDetection3D 的 PointPillars nuScenes 配置文件路径
    # 这个路径是相对于 mmdetection3d 安装目录的
    config_file = "configs/pointpillars/pointpillars_hv_fpn_sst_secfpn_8xb4-2x_nus-3d.py"
    
    # 工作目录（保存训练日志和模型）
    work_dir = os.path.join(PROJECT_ROOT, "outputs", "predictions", "train_results")
    
    cmd = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  📋 MMDetection3D 训练命令:

  # 方式 1: 单 GPU 训练
  cd <mmdetection3d 安装目录>
  python tools/train.py \\
      {config_file} \\
      --work-dir {work_dir}

  # 方式 2: 使用 MIM 训练（推荐，不需要进入 mmdet3d 目录）
  mim train mmdet3d \\
      {config_file} \\
      --work-dir {work_dir}

  # 方式 3: 如果显存不足，减少 batch_size
  # 修改配置文件中的 train_dataloader.batch_size = 1

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  💡 训练注意事项:
  1. nuScenes mini 只有 10 个场景，训练结果不具有代表性
  2. 完整 nuScenes 训练通常需要 8x GPU, 训练数十个 epoch
  3. mini 数据集训练仅用于验证流程是否跑通
  4. 如果遇到 OOM（显存不足），请减少 batch_size
  5. 训练日志和模型权重将保存到: {work_dir}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  📋 OpenPCDet 训练命令（备选方案）:

  cd <OpenPCDet 安装目录>
  python tools/train.py \\
      --cfg_file tools/cfgs/nuscenes_models/cbgs_pillar0075_res2d_centerpoint.yaml \\
      --batch_size 4 \\
      --epochs 20

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    return cmd


def main():
    print_header("训练 3D 检测 Baseline")
    
    print("""
📋 本脚本帮助你运行 PointPillars 训练。

⚠️  重要提示:
   - 使用 nuScenes mini 训练仅用于验证流程跑通
   - mini 数据集只有 10 个场景、约 400 个样本
   - 训练出来的模型性能不能代表真实水平
   - 真实训练需要完整 nuScenes 数据集（300GB+）和多 GPU

💻 GPU vs CPU:
   - GPU 训练: 通常几小时到几十小时（取决于数据量和 GPU 数量）
   - CPU 训练: 可能需要数天，不建议用于完整数据集
   - 建议: 至少有一块 8GB 以上显存的 GPU
""")
    
    if not check_prerequisites():
        print("\n❌ 前提条件不满足，请先解决上述问题。")
        sys.exit(1)
    
    cmd = get_train_command()
    print(cmd)
    
    print_header("训练指南输出完成")
    print("\n请按照上方命令在终端中运行训练。")
    print("训练完成后，运行 python scripts/08_inference_baseline.py 进行推理。\n")


if __name__ == '__main__':
    main()
