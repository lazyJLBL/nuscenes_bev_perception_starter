"""
00_check_environment.py — 环境检查脚本
========================================
运行此脚本检查你的开发环境是否满足项目要求。

运行命令:
    python scripts/00_check_environment.py

检查内容:
    1. Python 版本（需要 3.8+）
    2. PyTorch 是否可用
    3. CUDA / GPU 是否可用
    4. nuscenes-devkit 是否安装
    5. OpenCV 是否安装
    6. 其他核心依赖
    7. nuScenes 数据路径是否存在
"""

import sys
import os

# 将项目根目录添加到 Python 路径，使得 src 包可以被导入
# 这是因为我们从 scripts/ 目录运行脚本，需要能找到 src/
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)


def check_python_version():
    """检查 Python 版本"""
    version = sys.version_info
    version_str = f"{version.major}.{version.minor}.{version.micro}"
    
    if version.major == 3 and version.minor >= 8:
        print(f"  ✅ Python 版本: {version_str}")
        return True
    else:
        print(f"  ❌ Python 版本: {version_str} （需要 3.8 或以上）")
        return False


def check_pytorch():
    """检查 PyTorch 是否可用"""
    try:
        import torch
        print(f"  ✅ PyTorch 版本: {torch.__version__}")
        return True
    except ImportError:
        print("  ❌ PyTorch 未安装")
        print("     请参考 https://pytorch.org 安装 PyTorch")
        print("     示例 (CUDA 11.8): pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118")
        print("     示例 (CPU only):  pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu")
        return False


def check_cuda():
    """检查 CUDA 是否可用"""
    try:
        import torch
        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            cuda_version = torch.version.cuda
            print(f"  ✅ CUDA 可用: {cuda_version}")
            print(f"     GPU 设备: {gpu_name}")
            print(f"     GPU 显存: {torch.cuda.get_device_properties(0).total_mem / 1024**3:.1f} GB")
            return True
        else:
            print("  ⚠️  CUDA 不可用（将使用 CPU）")
            print("     可视化部分（脚本 00-05）不需要 GPU")
            print("     训练部分（脚本 07-08）建议使用 GPU，但也可以用 CPU（会很慢）")
            return False
    except ImportError:
        print("  ⚠️  PyTorch 未安装，无法检查 CUDA")
        return False


def check_nuscenes_devkit():
    """检查 nuscenes-devkit 是否安装"""
    try:
        import nuscenes
        print(f"  ✅ nuscenes-devkit 已安装")
        return True
    except ImportError:
        print("  ❌ nuscenes-devkit 未安装")
        print("     安装命令: pip install nuscenes-devkit")
        return False


def check_opencv():
    """检查 OpenCV 是否安装"""
    try:
        import cv2
        print(f"  ✅ OpenCV 版本: {cv2.__version__}")
        return True
    except ImportError:
        print("  ❌ OpenCV 未安装")
        print("     安装命令: pip install opencv-python")
        return False


def check_other_deps():
    """检查其他核心依赖"""
    deps = {
        'numpy': 'numpy',
        'matplotlib': 'matplotlib',
        'pyquaternion': 'pyquaternion',
        'yaml': 'PyYAML',
        'tqdm': 'tqdm',
        'PIL': 'Pillow',
    }
    
    all_ok = True
    for module_name, pip_name in deps.items():
        try:
            mod = __import__(module_name)
            version = getattr(mod, '__version__', '未知')
            print(f"  ✅ {pip_name}: {version}")
        except ImportError:
            print(f"  ❌ {pip_name} 未安装 -> pip install {pip_name}")
            all_ok = False
    
    return all_ok


def check_data_path():
    """检查 nuScenes 数据路径是否存在"""
    try:
        from src.utils.config import get_paths_config
        paths = get_paths_config()
        dataroot = paths['nuscenes_dataroot']
        version = paths.get('nuscenes_version', 'v1.0-mini')
        
        if os.path.exists(dataroot):
            print(f"  ✅ 数据根目录存在: {dataroot}")
            
            # 检查 v1.0-mini 子目录
            version_dir = os.path.join(dataroot, version)
            if os.path.exists(version_dir):
                print(f"  ✅ 数据版本目录存在: {version_dir}")
            else:
                print(f"  ⚠️  数据版本目录不存在: {version_dir}")
                print(f"     请确认 nuScenes {version} 数据已正确解压")
            
            # 检查 samples 目录
            samples_dir = os.path.join(dataroot, 'samples')
            if os.path.exists(samples_dir):
                print(f"  ✅ samples 目录存在")
            else:
                print(f"  ⚠️  samples 目录不存在")
                print(f"     nuScenes 数据可能未完整解压")
            
            return True
        else:
            print(f"  ❌ 数据根目录不存在: {dataroot}")
            print(f"     请下载 nuScenes mini 数据集:")
            print(f"     https://www.nuscenes.org/nuscenes#download")
            print(f"     下载后解压到: {dataroot}")
            print(f"     或修改 configs/paths.yaml 中的 nuscenes_dataroot")
            return False
    except Exception as e:
        print(f"  ❌ 无法检查数据路径: {e}")
        return False


def main():
    """主函数：执行所有环境检查"""
    print("=" * 70)
    print("  nuScenes BEV Perception Starter — 环境检查")
    print("=" * 70)
    
    results = {}
    
    print("\n📌 1. Python 版本检查:")
    results['python'] = check_python_version()
    
    print("\n📌 2. PyTorch 检查:")
    results['pytorch'] = check_pytorch()
    
    print("\n📌 3. CUDA / GPU 检查:")
    results['cuda'] = check_cuda()
    
    print("\n📌 4. nuscenes-devkit 检查:")
    results['nuscenes'] = check_nuscenes_devkit()
    
    print("\n📌 5. OpenCV 检查:")
    results['opencv'] = check_opencv()
    
    print("\n📌 6. 其他依赖检查:")
    results['other'] = check_other_deps()
    
    print("\n📌 7. 数据路径检查:")
    results['data'] = check_data_path()
    
    # 总结
    print("\n" + "=" * 70)
    print("  检查总结")
    print("=" * 70)
    
    # 必须通过的项
    essential = ['python', 'nuscenes', 'opencv', 'other']
    essential_ok = all(results.get(k, False) for k in essential)
    
    if essential_ok:
        print("\n  ✅ 核心依赖已就绪！")
    else:
        print("\n  ❌ 部分核心依赖缺失，请安装后重试。")
        print("     快速安装: pip install -r requirements.txt")
    
    if results.get('pytorch') and results.get('cuda'):
        print("  ✅ GPU 环境就绪，可以运行所有脚本（包括训练）。")
    elif results.get('pytorch') and not results.get('cuda'):
        print("  ⚠️  无 GPU，可以运行可视化脚本（00-05），训练脚本会很慢。")
    else:
        print("  ⚠️  PyTorch 未安装，可视化脚本仍可运行，但训练脚本需要 PyTorch。")
    
    if results.get('data'):
        print("  ✅ 数据路径已配置。")
    else:
        print("  ⚠️  数据路径未就绪，请下载 nuScenes mini 并配置 configs/paths.yaml。")
    
    print("\n" + "=" * 70)


if __name__ == '__main__':
    main()
