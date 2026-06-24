"""
10_check_detection_results.py — 检查 3D 检测产物
==========================================================
检查训练、推理、评估产生的各文件是否存在，并打印核心指标。

运行命令:
    python scripts/10_check_detection_results.py
"""

import sys
import os
import json

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from src.utils.logger import print_header, print_separator
from src.utils.config import get_model_config

def main():
    print_header("3D 检测产物检查")
    
    model_cfg = get_model_config()
    det_cfg = model_cfg.get('detection', {})
    
    work_dir = os.path.join(PROJECT_ROOT, det_cfg.get('work_dir', 'outputs/predictions/train_results'))
    pred_file = os.path.join(PROJECT_ROOT, det_cfg.get('prediction_file', 'outputs/predictions/detection_results.json'))
    metrics_file = os.path.join(PROJECT_ROOT, det_cfg.get('metrics_file', 'outputs/predictions/metrics_summary.json'))
    status_file = os.path.join(work_dir, "training_status.json")
    
    all_passed = True
    
    print("\n📌 1. 检查文件生成情况...")
    
    files_to_check = {
        "训练状态": status_file,
        "模型权重": os.path.join(work_dir, "latest.pth"),
        "预测结果": pred_file,
        "评估指标": metrics_file
    }
    
    for name, path in files_to_check.items():
        if os.path.exists(path):
            print(f"  ✅ {name}: 已找到")
        else:
            print(f"  ❌ {name}: 未找到 ({path})")
            all_passed = False
            
    print_separator()
    
    if os.path.exists(status_file):
        print("📌 2. 训练信息:")
        try:
            with open(status_file, "r") as f:
                status = json.load(f)
            print(f"  - 状态: {status.get('status', 'unknown')}")
            print(f"  - Epochs: {status.get('epochs', 0)}")
            print(f"  - Final Loss: {status.get('final_loss', 0.0):.4f}")
        except Exception as e:
            print(f"  ❌ 无法读取状态: {e}")
    
    print_separator()
    
    if os.path.exists(metrics_file):
        print("📌 3. 核心评估指标:")
        try:
            with open(metrics_file, "r") as f:
                metrics = json.load(f)
            print(f"  - mAP: {metrics.get('mean_ap', 0.0):.4f}")
            print(f"  - NDS: {metrics.get('nd_score', 0.0):.4f}")
            print("  - TP Errors:")
            for k, v in metrics.get('tp_errors', {}).items():
                print(f"    * {k}: {v:.4f}")
        except Exception as e:
            print(f"  ❌ 无法读取指标: {e}")
            
    print_separator()
    
    if all_passed:
        print("🎉 所有检查通过！闭环验证成功。")
        sys.exit(0)
    else:
        print("⚠️ 存在缺失的产物，请检查前面的步骤是否执行成功。")
        sys.exit(1)

if __name__ == '__main__':
    main()
