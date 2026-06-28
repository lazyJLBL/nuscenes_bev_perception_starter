"""
Training and inference utilities for 3D detection.
- train_one_epoch: 使用真实的 Focal Loss + SmoothL1 训练一个 epoch
- inference: 使用模型的 predict() 方法生成真实检测结果
- run_nuscenes_eval: 调用 nuScenes 官方评估器
"""

import torch
import torch.nn as nn
import numpy as np
from typing import Dict, List
import time
import json
import os
from pyquaternion import Quaternion

from nuscenes.eval.detection.evaluate import DetectionEval
from nuscenes.eval.detection.config import config_factory

from .anchor_utils import assign_targets
from .losses import DetectionLoss


def prepare_targets(batch_dict, anchors_np, num_classes):
    """为一个 batch 准备 anchor-GT 目标分配。"""
    batch_size = batch_dict['batch_size']

    all_cls_targets = []
    all_box_targets = []
    all_dir_targets = []
    all_pos_masks = []
    all_neg_masks = []

    for b in range(batch_size):
        if 'gt_boxes' in batch_dict and len(batch_dict['gt_boxes']) > b:
            gt_boxes = batch_dict['gt_boxes'][b]
            gt_classes = batch_dict['gt_classes'][b]
        else:
            gt_boxes = np.zeros((0, 7), dtype=np.float32)
            gt_classes = np.zeros(0, dtype=np.int64)

        targets = assign_targets(
            anchors_np, gt_boxes, gt_classes, num_classes,
            pos_iou_threshold=0.6,
            neg_iou_threshold=0.45,
        )

        all_cls_targets.append(torch.from_numpy(targets['cls_targets']))
        all_box_targets.append(torch.from_numpy(targets['box_targets']))
        all_dir_targets.append(torch.from_numpy(targets['dir_targets']))
        all_pos_masks.append(torch.from_numpy(targets['pos_mask']))
        all_neg_masks.append(torch.from_numpy(targets['neg_mask']))

    return {
        'cls_targets': torch.stack(all_cls_targets),
        'box_targets': torch.stack(all_box_targets),
        'dir_targets': torch.stack(all_dir_targets),
        'pos_mask': torch.stack(all_pos_masks),
        'neg_mask': torch.stack(all_neg_masks),
    }


def train_one_epoch(
    model: nn.Module,
    optimizer: torch.optim.Optimizer,
    dataloader,
    device: torch.device,
    epoch: int,
    max_grad_norm: float = 10.0,
) -> Dict[str, float]:
    """用真实的 Focal Loss + SmoothL1 训练一个 epoch。"""
    model.train()
    loss_fn = DetectionLoss(cls_weight=1.0, reg_weight=2.0, dir_weight=0.2)

    anchors_np = model.anchor_generator.anchors
    num_classes = model.num_classes

    total_loss = 0.0
    num_pos_total = 0

    for i, batch_dict in enumerate(dataloader):
        optimizer.zero_grad()

        # Move inputs to device
        batch_dict["pillar_features"] = batch_dict["pillar_features"].to(device)
        batch_dict["pillar_coords"] = batch_dict["pillar_coords"].to(device)
        batch_dict["num_points"] = batch_dict["num_points"].to(device)

        # Forward
        preds_dict = model(batch_dict)

        # 准备 anchor-GT 匹配目标
        targets_dict = prepare_targets(batch_dict, anchors_np, num_classes)
        for key in targets_dict:
            targets_dict[key] = targets_dict[key].to(device)

        # 计算损失
        loss, loss_stats = loss_fn(preds_dict, targets_dict)

        num_pos = targets_dict['pos_mask'].sum().item()
        num_pos_total += num_pos

        # Backward + 梯度裁剪
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_grad_norm)
        optimizer.step()

        total_loss += loss.item()

        if i % 5 == 0:
            print(f"  Epoch [{epoch}] Batch [{i}/{len(dataloader)}] "
                  f"Loss: {loss.item():.4f} (cls: {loss_stats['loss_cls']:.4f}, "
                  f"reg: {loss_stats['loss_reg']:.4f}, dir: {loss_stats['loss_dir']:.4f}) "
                  f"Pos anchors: {int(num_pos)}")

    avg_loss = total_loss / max(len(dataloader), 1)
    print(f"  ✅ Epoch {epoch} 完成. Avg Loss: {avg_loss:.4f}, Total Pos Anchors: {num_pos_total}")
    return {"loss": avg_loss}


@torch.no_grad()
def inference(model: nn.Module, dataloader, device: torch.device, classes: List[str], output_file: str):
    """使用模型的 predict() 方法运行真实推理，生成 nuScenes 格式的检测结果。"""
    model.eval()

    results = {}

    print("🔍 Running inference...")
    for i, batch_dict in enumerate(dataloader):
        batch_dict["pillar_features"] = batch_dict["pillar_features"].to(device)
        batch_dict["pillar_coords"] = batch_dict["pillar_coords"].to(device)
        batch_dict["num_points"] = batch_dict["num_points"].to(device)

        # 真实的模型推理 + 后处理
        batch_results = model.predict(batch_dict, score_threshold=0.1, nms_threshold=0.2)

        sample_tokens = batch_dict["sample_tokens"]
        for b, token in enumerate(sample_tokens):
            det = batch_results[b]
            preds = []

            for j in range(len(det['scores'])):
                box = det['boxes'][j]
                score = float(det['scores'][j])
                label_idx = int(det['labels'][j])
                cls_name = classes[label_idx] if label_idx < len(classes) else 'car'

                # 旋转角转四元数
                yaw = float(box[6])
                q = Quaternion(axis=[0, 0, 1], angle=yaw)

                pred = {
                    "sample_token": token,
                    "translation": [float(box[0]), float(box[1]), float(box[2])],
                    "size": [float(box[3]), float(box[4]), float(box[5])],
                    "rotation": q.elements.tolist(),
                    "velocity": [0.0, 0.0],
                    "detection_name": cls_name,
                    "detection_score": score,
                    "attribute_name": ""
                }
                preds.append(pred)

            results[token] = preds

        if i % 10 == 0:
            total_dets = sum(len(r['scores']) for r in batch_results)
            print(f"  Processed {i}/{len(dataloader)} batches. Detections: {total_dets}")

    # 封装为 nuScenes 提交格式
    submission = {
        "meta": {
            "use_camera": False,
            "use_lidar": True,
            "use_radar": False,
            "use_map": False,
            "use_external": False
        },
        "results": results
    }

    with open(output_file, 'w') as f:
        json.dump(submission, f)

    total_preds = sum(len(v) for v in results.values())
    print(f"  💾 Predictions saved to {output_file} (total: {total_preds} detections)")


def run_nuscenes_eval(nusc, res_path: str, eval_set: str, output_dir: str):
    """运行 nuScenes 官方检测评估器。"""
    cfg = config_factory("detection_cvpr_2019")

    nusc_eval = DetectionEval(
        nusc,
        config=cfg,
        result_path=res_path,
        eval_set=eval_set,
        output_dir=output_dir,
        verbose=True
    )

    print("📊 Starting nuScenes evaluation...")
    eval_result = nusc_eval.main(plot_examples=0, render_curves=False)
    metrics = eval_result[0] if isinstance(eval_result, tuple) else eval_result

    summary_path = os.path.join(output_dir, "metrics_summary.json")
    if os.path.exists(summary_path):
        with open(summary_path, "r") as f:
            nusc_metrics = json.load(f)

        mAP = nusc_metrics.get("mean_ap", 0.0)
        NDS = nusc_metrics.get("nd_score", 0.0)

        print(f"  📈 mAP: {mAP:.4f}")
        print(f"  📈 NDS: {NDS:.4f}")
    else:
        print(f"  ❌ Failed to find nuScenes metrics at {summary_path}")
