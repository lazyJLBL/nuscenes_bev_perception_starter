"""
Anchor utilities for 3D object detection.
Handles anchor generation, IoU computation, target assignment, and box encoding/decoding.
"""

import torch
import numpy as np
from typing import List, Tuple, Dict

# nuScenes 典型目标尺寸 [w, l, h] 和 z 中心高度
NUSCENES_ANCHOR_SIZES = {
    'car':        {'size': [1.9, 4.7, 1.7], 'z_center': -1.0},
    'pedestrian': {'size': [0.7, 0.7, 1.8], 'z_center': -0.73},
    'bicycle':    {'size': [0.6, 1.7, 1.3], 'z_center': -1.0},
    'bus':        {'size': [2.9, 12.0, 3.9], 'z_center': 0.0},
    'truck':      {'size': [2.5, 6.9, 2.8], 'z_center': -0.2},
}

ANCHOR_ROTATIONS = [0, np.pi / 2]


class AnchorGenerator:
    """在 BEV 网格上生成 3D 检测 Anchor。"""

    def __init__(
        self,
        point_cloud_range: List[float],
        feature_map_size: Tuple[int, int],  # (H, W)
        classes: List[str],
        rotations: List[float] = None,
    ):
        self.point_cloud_range = point_cloud_range
        self.feature_map_size = feature_map_size
        self.classes = classes
        self.rotations = rotations or ANCHOR_ROTATIONS
        self.num_anchors_per_loc = len(classes) * len(self.rotations)

        # 生成所有 anchors
        self.anchors = self._generate_anchors()

    def _generate_anchors(self) -> np.ndarray:
        """
        生成所有 anchor。
        Returns: [H * W * num_classes * num_rotations, 7]
                 每个 anchor 格式为 [x, y, z, w, l, h, rotation]
        """
        H, W = self.feature_map_size
        x_min, y_min = self.point_cloud_range[0], self.point_cloud_range[1]
        x_max, y_max = self.point_cloud_range[3], self.point_cloud_range[4]

        x_step = (x_max - x_min) / W
        y_step = (y_max - y_min) / H

        x_centers = np.arange(W) * x_step + x_min + x_step / 2
        y_centers = np.arange(H) * y_step + y_min + y_step / 2

        xx, yy = np.meshgrid(x_centers, y_centers)  # [H, W]

        all_anchors = []
        for cls_name in self.classes:
            cfg = NUSCENES_ANCHOR_SIZES[cls_name]
            w, l, h = cfg['size']
            z = cfg['z_center']

            for rot in self.rotations:
                anchors = np.stack([
                    xx, yy,
                    np.full_like(xx, z),
                    np.full_like(xx, w),
                    np.full_like(xx, l),
                    np.full_like(xx, h),
                    np.full_like(xx, rot),
                ], axis=-1)
                all_anchors.append(anchors)

        # [num_anchor_types, H, W, 7] -> [H, W, num_anchor_types, 7] -> [H*W*A, 7]
        all_anchors = np.stack(all_anchors, axis=0)
        all_anchors = all_anchors.transpose(1, 2, 0, 3)
        all_anchors = all_anchors.reshape(-1, 7).astype(np.float32)

        return all_anchors

    def get_anchors_tensor(self, device='cpu') -> torch.Tensor:
        return torch.from_numpy(self.anchors).to(device)


def iou_bev_axis_aligned(boxes_a: np.ndarray, boxes_b: np.ndarray) -> np.ndarray:
    """
    计算轴对齐的 BEV 2D IoU（忽略旋转角，CPU 友好）。

    Args:
        boxes_a: [N, 7] (x, y, z, w, l, h, rot)
        boxes_b: [M, 7] (x, y, z, w, l, h, rot)
    Returns:
        iou: [N, M]
    """
    a_x1 = boxes_a[:, 0] - boxes_a[:, 3] / 2
    a_y1 = boxes_a[:, 1] - boxes_a[:, 4] / 2
    a_x2 = boxes_a[:, 0] + boxes_a[:, 3] / 2
    a_y2 = boxes_a[:, 1] + boxes_a[:, 4] / 2

    b_x1 = boxes_b[:, 0] - boxes_b[:, 3] / 2
    b_y1 = boxes_b[:, 1] - boxes_b[:, 4] / 2
    b_x2 = boxes_b[:, 0] + boxes_b[:, 3] / 2
    b_y2 = boxes_b[:, 1] + boxes_b[:, 4] / 2

    a_area = (a_x2 - a_x1) * (a_y2 - a_y1)
    b_area = (b_x2 - b_x1) * (b_y2 - b_y1)

    inter_x1 = np.maximum(a_x1[:, None], b_x1[None, :])
    inter_y1 = np.maximum(a_y1[:, None], b_y1[None, :])
    inter_x2 = np.minimum(a_x2[:, None], b_x2[None, :])
    inter_y2 = np.minimum(a_y2[:, None], b_y2[None, :])

    inter_w = np.maximum(inter_x2 - inter_x1, 0)
    inter_h = np.maximum(inter_y2 - inter_y1, 0)
    inter_area = inter_w * inter_h

    union_area = a_area[:, None] + b_area[None, :] - inter_area
    iou = inter_area / np.maximum(union_area, 1e-6)

    return iou


def encode_boxes(gt_boxes: np.ndarray, anchors: np.ndarray) -> np.ndarray:
    """
    将 GT 框编码为相对于 anchor 的残差。

    Args:
        gt_boxes: [N, 7] (x, y, z, w, l, h, rot)
        anchors:  [N, 7] (x, y, z, w, l, h, rot)
    Returns:
        targets: [N, 8] (dx, dy, dz, dw, dl, dh, sin, cos)
    """
    diag = np.sqrt(anchors[:, 3]**2 + anchors[:, 4]**2)

    dx = (gt_boxes[:, 0] - anchors[:, 0]) / np.maximum(diag, 1e-6)
    dy = (gt_boxes[:, 1] - anchors[:, 1]) / np.maximum(diag, 1e-6)
    dz = (gt_boxes[:, 2] - anchors[:, 2]) / np.maximum(anchors[:, 5], 1e-6)
    dw = np.log(np.maximum(gt_boxes[:, 3], 1e-6) / np.maximum(anchors[:, 3], 1e-6))
    dl = np.log(np.maximum(gt_boxes[:, 4], 1e-6) / np.maximum(anchors[:, 4], 1e-6))
    dh = np.log(np.maximum(gt_boxes[:, 5], 1e-6) / np.maximum(anchors[:, 5], 1e-6))

    rot_diff = gt_boxes[:, 6] - anchors[:, 6]
    sin_val = np.sin(rot_diff)
    cos_val = np.cos(rot_diff)

    targets = np.stack([dx, dy, dz, dw, dl, dh, sin_val, cos_val], axis=-1)
    return targets.astype(np.float32)


def decode_boxes_torch(box_preds: torch.Tensor, anchors: torch.Tensor) -> torch.Tensor:
    """
    将预测残差解码为绝对 3D 框坐标。

    Args:
        box_preds: [N, 8] (dx, dy, dz, dw, dl, dh, sin, cos)
        anchors:   [N, 7] (x, y, z, w, l, h, rot)
    Returns:
        boxes: [N, 7] (x, y, z, w, l, h, rot)
    """
    diag = torch.sqrt(anchors[:, 3]**2 + anchors[:, 4]**2)

    x = box_preds[:, 0] * diag + anchors[:, 0]
    y = box_preds[:, 1] * diag + anchors[:, 1]
    z = box_preds[:, 2] * anchors[:, 5] + anchors[:, 2]
    w = torch.exp(box_preds[:, 3].clamp(max=5.0)) * anchors[:, 3]
    l = torch.exp(box_preds[:, 4].clamp(max=5.0)) * anchors[:, 4]
    h = torch.exp(box_preds[:, 5].clamp(max=5.0)) * anchors[:, 5]

    rot = torch.atan2(box_preds[:, 6], box_preds[:, 7]) + anchors[:, 6]

    return torch.stack([x, y, z, w, l, h, rot], dim=-1)


def assign_targets(
    anchors: np.ndarray,
    gt_boxes: np.ndarray,
    gt_classes: np.ndarray,
    num_classes: int,
    pos_iou_threshold: float = 0.6,
    neg_iou_threshold: float = 0.45,
) -> Dict[str, np.ndarray]:
    """
    基于 BEV IoU 将 GT 框分配给 anchor。

    Args:
        anchors: [num_anchors, 7]
        gt_boxes: [num_gt, 7]
        gt_classes: [num_gt] (整数类别索引, 0-indexed)
        num_classes: int
        pos_iou_threshold: 正样本 IoU 阈值
        neg_iou_threshold: 负样本 IoU 阈值
    Returns:
        dict with cls_targets, box_targets, dir_targets, pos_mask, neg_mask
    """
    num_anchors = anchors.shape[0]

    cls_targets = np.zeros(num_anchors, dtype=np.int64)
    box_targets = np.zeros((num_anchors, 8), dtype=np.float32)
    dir_targets = np.zeros(num_anchors, dtype=np.int64)

    if gt_boxes.shape[0] == 0:
        neg_mask = np.ones(num_anchors, dtype=bool)
        pos_mask = np.zeros(num_anchors, dtype=bool)
        return {
            'cls_targets': cls_targets,
            'box_targets': box_targets,
            'dir_targets': dir_targets,
            'pos_mask': pos_mask,
            'neg_mask': neg_mask,
        }

    # 计算 IoU 矩阵 [num_anchors, num_gt]
    iou_matrix = iou_bev_axis_aligned(anchors, gt_boxes)

    # 每个 anchor 找最佳匹配的 GT
    max_iou_per_anchor = iou_matrix.max(axis=1)
    best_gt_per_anchor = iou_matrix.argmax(axis=1)

    # 每个 GT 找最佳匹配的 anchor（确保每个 GT 至少有一个正样本）
    best_anchor_per_gt = iou_matrix.argmax(axis=0)

    # 正样本：IoU > 阈值
    pos_mask = max_iou_per_anchor >= pos_iou_threshold

    # 强制每个 GT 的最佳 anchor 为正样本
    for gt_idx in range(gt_boxes.shape[0]):
        pos_mask[best_anchor_per_gt[gt_idx]] = True
        best_gt_per_anchor[best_anchor_per_gt[gt_idx]] = gt_idx

    # 负样本：IoU < 阈值
    neg_mask = max_iou_per_anchor < neg_iou_threshold
    neg_mask[pos_mask] = False  # 正样本覆盖负样本

    # 为正样本分配目标
    pos_indices = np.where(pos_mask)[0]
    matched_gt_indices = best_gt_per_anchor[pos_indices]

    # 类别目标 (1-indexed: 0=背景, 1..C=前景类别)
    cls_targets[pos_indices] = gt_classes[matched_gt_indices] + 1

    # 框回归目标
    box_targets[pos_indices] = encode_boxes(
        gt_boxes[matched_gt_indices],
        anchors[pos_indices]
    )

    # 方向目标: 旋转差 > 0 则为 1，否则为 0
    gt_rot = gt_boxes[matched_gt_indices, 6]
    anchor_rot = anchors[pos_indices, 6]
    rot_diff = gt_rot - anchor_rot
    dir_targets[pos_indices] = (rot_diff > 0).astype(np.int64)

    return {
        'cls_targets': cls_targets,
        'box_targets': box_targets,
        'dir_targets': dir_targets,
        'pos_mask': pos_mask,
        'neg_mask': neg_mask,
    }
