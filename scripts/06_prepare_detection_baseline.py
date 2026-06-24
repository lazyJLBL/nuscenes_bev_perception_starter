"""
06_prepare_detection_baseline.py — 准备 3D 检测 Baseline
==========================================================
帮助用户准备 3D 检测 baseline（PointPillars on nuScenes）。

此脚本不会自动安装 MMDetection3D，而是:
    1. 检查 MMDetection3D 是否已安装
    2. 如果未安装，打印详细的安装指南
    3. 如果已安装，准备 nuScenes 数据的 info 文件
    4. 提供 OpenPCDet 作为备选方案

运行命令:
    python scripts/06_prepare_detection_baseline.py
"""

import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from src.utils.logger import print_header, print_separator
from src.utils.config import get_paths_config


def check_mmdet3d():
    """检查 MMDetection3D 是否已安装"""
    try:
        import mmdet3d
        print(f"  ✅ MMDetection3D 已安装: {mmdet3d.__version__}")
        return True
    except ImportError:
        print("  ❌ MMDetection3D 未安装")
        return False


def check_mmengine():
    """检查 MMEngine 是否已安装"""
    try:
        import mmengine
        print(f"  ✅ MMEngine 已安装: {mmengine.__version__}")
        return True
    except ImportError:
        print("  ❌ MMEngine 未安装")
        return False


def check_mmcv():
    """检查 MMCV 是否已安装"""
    try:
        import mmcv
        print(f"  ✅ MMCV 已安装: {mmcv.__version__}")
        return True
    except ImportError:
        print("  ❌ MMCV 未安装")
        return False


def check_mmdet():
    """检查 MMDetection 是否已安装"""
    try:
        import mmdet
        print(f"  ✅ MMDetection 已安装: {mmdet.__version__}")
        return True
    except ImportError:
        print("  ❌ MMDetection 未安装")
        return False


def print_mmdet3d_install_guide():
    """打印 MMDetection3D 安装指南"""
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║                  MMDetection3D 安装指南                             ║
╚══════════════════════════════════════════════════════════════════════╝

⚠️  MMDetection3D 的安装较为复杂，需要严格匹配版本。
以下是推荐的安装步骤（基于 PyTorch 2.0 + CUDA 11.8）:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📌 方案 A: 使用 MIM 安装（推荐）

  # 步骤 1: 安装 OpenMIM（OpenMMLab 的包管理工具）
  pip install -U openmim

  # 步骤 2: 安装 MMEngine
  mim install mmengine

  # 步骤 3: 安装 MMCV（需要匹配 PyTorch 和 CUDA 版本）
  mim install "mmcv>=2.0.0"

  # 步骤 4: 安装 MMDetection
  mim install "mmdet>=3.0.0"

  # 步骤 5: 安装 MMDetection3D
  mim install "mmdet3d>=1.1.0"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📌 方案 B: 从源码安装（如果 MIM 安装失败）

  # 步骤 1: 安装依赖
  pip install -U openmim
  mim install mmengine
  mim install "mmcv>=2.0.0"
  mim install "mmdet>=3.0.0"

  # 步骤 2: 克隆 MMDetection3D
  git clone https://github.com/open-mmlab/mmdetection3d.git
  cd mmdetection3d
  pip install -v -e .

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📌 方案 C: 使用 OpenPCDet（如果 MMDetection3D 安装失败）

  OpenPCDet 是另一个优秀的 3D 检测框架，安装相对简单。

  git clone https://github.com/open-mmlab/OpenPCDet.git
  cd OpenPCDet
  pip install -r requirements.txt
  python setup.py develop

  OpenPCDet 也支持 PointPillars 和 nuScenes 数据集。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 常见问题:
  1. MMCV 编译失败 → 确认 CUDA 版本和 PyTorch 版本匹配
  2. 版本冲突 → 建议在新的 conda 环境中安装
  3. Windows 编译问题 → 推荐使用 Linux 或 WSL2
  4. 显存不足 → 减少 batch_size 或使用 mini 数据集
""")


def prepare_nuscenes_data():
    """准备 nuScenes 数据的 info 文件（供 MMDetection3D 使用）"""
    paths = get_paths_config()
    dataroot = paths['nuscenes_dataroot']
    version = paths.get('nuscenes_version', 'v1.0-mini')
    
    print(f"\n📌 准备 nuScenes 数据 info 文件...")
    print(f"   数据路径: {dataroot}")
    print(f"   版本:     {version}")
    
    try:
        # MMDetection3D 提供了数据准备脚本
        print(f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  使用 MMDetection3D 的数据准备命令:

  # 在 mmdetection3d 目录下运行:
  python tools/create_data.py nuscenes \\
      --root-path {dataroot} \\
      --out-dir {dataroot} \\
      --extra-tag nuscenes \\
      --version {version}

  这会在 {dataroot} 目录下生成:
    - nuscenes_infos_train.pkl
    - nuscenes_infos_val.pkl
    - nuscenes_dbinfos_train.pkl
    - nuscenes_gt_database/ (GT 数据库，用于数据增强)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  如果使用 OpenPCDet，数据准备命令为:

  # 在 OpenPCDet 目录下运行:
  python -m pcdet.datasets.nuscenes.nuscenes_dataset \\
      --func create_nuscenes_infos \\
      --cfg_file tools/cfgs/dataset_configs/nuscenes_dataset.yaml \\
      --version {version}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""")
    except Exception as e:
        print(f"  ⚠️ 数据准备过程中出错: {e}")


def main():
    print_header("3D 检测 Baseline 准备")
    
    print("""
📋 Baseline 选择说明:
   本项目使用 PointPillars 作为 3D 检测 baseline。
   
   为什么选择 PointPillars?
   1. 结构简单，容易理解
   2. 推理速度快
   3. 是许多后续工作的基础
   4. nuScenes 官方提供了预训练模型
   
   框架选择:
   - 首选: MMDetection3D (生态完善，社区活跃)
   - 备选: OpenPCDet (安装更简单)
""")
    
    # 检查依赖
    print("📌 步骤 1: 检查依赖...")
    print()
    
    has_mmengine = check_mmengine()
    has_mmcv = check_mmcv()
    has_mmdet = check_mmdet()
    has_mmdet3d = check_mmdet3d()
    
    print()
    
    if has_mmdet3d:
        print("  🎉 MMDetection3D 环境就绪！")
        print("\n📌 步骤 2: 准备数据...")
        prepare_nuscenes_data()
    else:
        print("  ⚠️ MMDetection3D 未完整安装。")
        print_mmdet3d_install_guide()
        print("\n  安装完成后，重新运行此脚本。")
        print("  或者，你也可以跳过训练步骤，只使用预训练模型进行推理。")
    
    print_header("Baseline 准备完成")
    print(f"\n下一步:")
    if has_mmdet3d:
        print(f"   1. 先运行数据准备命令（见上方说明）")
        print(f"   2. 然后运行 python scripts/07_train_baseline.py")
    else:
        print(f"   1. 按照上方指南安装 MMDetection3D")
        print(f"   2. 重新运行 python scripts/06_prepare_detection_baseline.py")
        print(f"   3. 或者直接运行 python scripts/08_inference_baseline.py 使用预训练模型")
    print()


if __name__ == '__main__':
    main()
