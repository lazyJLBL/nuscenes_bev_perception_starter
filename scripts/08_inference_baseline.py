"""
08_inference_baseline.py — 推理 3D 检测 Baseline
====================================================
使用 MMDetection3D 的预训练模型或训练好的模型进行推理。

运行命令:
    python scripts/08_inference_baseline.py

此脚本支持两种推理方式:
    1. 使用 MMDetection3D 预训练模型（推荐新手使用）
    2. 使用自己训练的模型
"""

import sys
import os
import json
import numpy as np

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from src.utils.logger import print_header
from src.utils.config import get_paths_config
from src.utils.path_utils import ensure_output_dirs, get_output_path


def try_mmdet3d_inference():
    """尝试使用 MMDetection3D 进行推理"""
    try:
        from mmdet3d.apis import init_model, inference_detector
        return True
    except ImportError:
        return False


def print_inference_guide():
    """打印推理指南"""
    paths = get_paths_config()
    dataroot = paths['nuscenes_dataroot']
    output_dir = os.path.join(PROJECT_ROOT, "outputs", "predictions")
    
    print(f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  📋 MMDetection3D 推理方式:

  # 方式 1: 使用 MIM 下载预训练模型并推理

  # 下载 PointPillars 预训练权重:
  mim download mmdet3d \\
      --config pointpillars_hv_fpn_sst_secfpn_8xb4-2x_nus-3d \\
      --dest {output_dir}

  # 使用预训练模型推理:
  cd <mmdetection3d 安装目录>
  python tools/test.py \\
      configs/pointpillars/pointpillars_hv_fpn_sst_secfpn_8xb4-2x_nus-3d.py \\
      <下载的 checkpoint.pth> \\
      --work-dir {output_dir}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  # 方式 2: 使用自己训练的模型推理

  cd <mmdetection3d 安装目录>
  python tools/test.py \\
      configs/pointpillars/pointpillars_hv_fpn_sst_secfpn_8xb4-2x_nus-3d.py \\
      {output_dir}/train_results/latest.pth \\
      --work-dir {output_dir}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  # 方式 3: 单张点云推理 (demo)

  cd <mmdetection3d 安装目录>
  python demo/pcd_demo.py \\
      <某个 .bin 点云文件路径> \\
      configs/pointpillars/pointpillars_hv_fpn_sst_secfpn_8xb4-2x_nus-3d.py \\
      <checkpoint.pth> \\
      --out-dir {output_dir}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  📋 OpenPCDet 推理方式（备选）:

  cd <OpenPCDet 安装目录>
  python tools/test.py \\
      --cfg_file tools/cfgs/nuscenes_models/cbgs_pillar0075_res2d_centerpoint.yaml \\
      --ckpt <checkpoint.pth> \\
      --batch_size 1

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""")


def demo_inference_output():
    """
    演示推理输出的数据结构。
    
    即使 MMDetection3D 未安装，也可以展示推理结果的格式，
    让用户理解输出数据的含义。
    """
    ensure_output_dirs()
    
    print("\n📌 3D 检测推理结果格式说明:")
    print("""
  一个 3D 检测模型的推理结果通常包含:

  对于每个检测到的目标:
    - label:       类别 (car, pedestrian, truck, ...)
    - score:       置信度分数 (0~1)
    - translation: [x, y, z] 3D 中心点坐标
    - size:        [w, l, h] 3D 尺寸 (宽, 长, 高)
    - rotation:    [w, x, y, z] 四元数旋转
    - velocity:    [vx, vy] 速度 (可选)

  示例 (JSON 格式):
""")
    
    # 生成示例结果（注意：这是模拟数据，仅用于说明格式）
    sample_results = {
        "description": "此为示例格式，非真实推理结果",
        "format": "nuScenes detection submission format",
        "results": {
            "<sample_token>": [
                {
                    "sample_token": "<sample_token>",
                    "translation": [100.0, 200.0, 1.5],
                    "size": [1.8, 4.5, 1.6],
                    "rotation": [1.0, 0.0, 0.0, 0.0],
                    "velocity": [0.0, 0.0],
                    "detection_name": "car",
                    "detection_score": 0.85,
                    "attribute_name": "vehicle.moving"
                }
            ]
        }
    }
    
    # 保存示例结果
    output_path = get_output_path("predictions", "example_detection_format.json")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(sample_results, f, indent=2, ensure_ascii=False)
    
    print(f"  示例格式已保存到: {output_path}")
    print(f"  注意: 这是格式示例，不是真实推理结果！")


def main():
    print_header("3D 检测 Baseline 推理")
    
    print("""
📋 推理说明:
   本脚本帮助你使用 PointPillars 模型进行 3D 目标检测推理。
   
   你可以:
   1. 使用预训练模型直接推理（不需要训练）
   2. 使用自己训练的模型推理
   3. 对单张点云进行 demo 推理
""")
    
    # 检查 MMDetection3D
    has_mmdet3d = try_mmdet3d_inference()
    
    if has_mmdet3d:
        print("  ✅ MMDetection3D 推理接口可用")
    else:
        print("  ⚠️ MMDetection3D 未安装，打印推理命令指南")
    
    # 打印推理指南
    print_inference_guide()
    
    # 展示结果格式
    demo_inference_output()
    
    print_header("推理指南输出完成")
    print("\n请按照上方命令进行推理。")
    print("推理完成后，运行 python scripts/09_visualize_predictions.py 可视化结果。\n")


if __name__ == '__main__':
    main()
