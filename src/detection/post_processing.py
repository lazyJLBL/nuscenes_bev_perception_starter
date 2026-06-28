"""
Post-processing utilities for 3D detection inference.
- decode_boxes: 从模型输出解码出 3D 框
- nms_bev: BEV 平面上的非极大值抑制
- post_process: 完整推理后处理管线
"""

import torch
import numpy as np
from typing import List, Dict
from .anchor_utils import decode_boxes_torch


def nms_bev(boxes: np.ndarray, scores: np.ndarray, nms_threshold: float = 0.2) -> np.ndarray:
    """
    轴对齐 BEV NMS。

    Args:
        boxes: [N, 7] (x, y, z, w, l, h, rot)
        scores: [N]
        nms_threshold: IoU 阈值
    Returns:
        keep: 保留的索引
    """
    if len(boxes) == 0:
        return np.array([], dtype=np.int64)

    x1 = boxes[:, 0] - boxes[:, 3] / 2
    y1 = boxes[:, 1] - boxes[:, 4] / 2
    x2 = boxes[:, 0] + boxes[:, 3] / 2
    y2 = boxes[:, 1] + boxes[:, 4] / 2

    areas = (x2 - x1) * (y2 - y1)
    order = scores.argsort()[::-1]

    keep = []
    while order.size > 0:
        i = order[0]
        keep.append(i)

        if order.size == 1:
            break

        xx1 = np.maximum(x1[i], x1[order[1:]])
        yy1 = np.maximum(y1[i], y1[order[1:]])
        xx2 = np.minimum(x2[i], x2[order[1:]])
        yy2 = np.minimum(y2[i], y2[order[1:]])

        w = np.maximum(0, xx2 - xx1)
        h = np.maximum(0, yy2 - yy1)
        inter = w * h

        iou = inter / (areas[i] + areas[order[1:]] - inter + 1e-6)

        inds = np.where(iou <= nms_threshold)[0]
        order = order[inds + 1]

    return np.array(keep, dtype=np.int64)


@torch.no_grad()
def post_process(
    preds_dict: Dict[str, torch.Tensor],
    anchors: torch.Tensor,
    num_classes: int,
    score_threshold: float = 0.3,
    nms_threshold: float = 0.2,
    max_detections: int = 100,
) -> List[Dict]:
    """
    完整推理后处理管线：sigmoid → 阈值过滤 → 解码 → NMS。

    Args:
        preds_dict: model output {'cls_preds': [B, N, C], 'box_preds': [B, N, 8], ...}
        anchors: [N, 7]
        num_classes: int
        score_threshold: 置信度阈值
        nms_threshold: NMS IoU 阈值
        max_detections: 最大检测数量
    Returns:
        List of dicts (one per batch), each with 'boxes', 'scores', 'labels'
    """
    batch_size = preds_dict['cls_preds'].shape[0]
    results = []

    for b in range(batch_size):
        cls_preds = torch.sigmoid(preds_dict['cls_preds'][b])  # [N, C]
        box_preds = preds_dict['box_preds'][b]  # [N, 8]

        # 每个 anchor 取最大分数和对应类别
        max_scores, max_labels = cls_preds.max(dim=-1)

        # 置信度阈值过滤
        mask = max_scores >= score_threshold

        if mask.sum() == 0:
            results.append({
                'boxes': np.zeros((0, 7), dtype=np.float32),
                'scores': np.zeros(0, dtype=np.float32),
                'labels': np.zeros(0, dtype=np.int64),
            })
            continue

        scores = max_scores[mask]
        labels = max_labels[mask]
        box_preds_filtered = box_preds[mask]
        anchors_filtered = anchors[mask]

        # 解码框
        decoded_boxes = decode_boxes_torch(box_preds_filtered, anchors_filtered)

        # 转 numpy 做 NMS
        boxes_np = decoded_boxes.cpu().numpy()
        scores_np = scores.cpu().numpy()
        labels_np = labels.cpu().numpy()

        # 分类别 NMS
        all_keep = []
        for cls_id in range(num_classes):
            cls_mask = labels_np == cls_id
            if cls_mask.sum() == 0:
                continue

            cls_boxes = boxes_np[cls_mask]
            cls_scores = scores_np[cls_mask]
            cls_indices = np.where(cls_mask)[0]

            keep = nms_bev(cls_boxes, cls_scores, nms_threshold)
            all_keep.extend(cls_indices[keep].tolist())

        if len(all_keep) == 0:
            results.append({
                'boxes': np.zeros((0, 7), dtype=np.float32),
                'scores': np.zeros(0, dtype=np.float32),
                'labels': np.zeros(0, dtype=np.int64),
            })
            continue

        all_keep = np.array(all_keep)

        # 按分数排序，取 top K
        sorted_idx = scores_np[all_keep].argsort()[::-1][:max_detections]
        final_keep = all_keep[sorted_idx]

        results.append({
            'boxes': boxes_np[final_keep],
            'scores': scores_np[final_keep],
            'labels': labels_np[final_keep],
        })

    return results
