"""
Simple 3D Detection Baseline for nuScenes.
Self-contained implementation of a simplified PointPillars-like network
with real anchor-based detection, Focal Loss, and NMS post-processing.
"""

from .simple_pillars import SimplePointPillars
from .nuscenes_dataset import NuScenesDetDataset
from .train_utils import train_one_epoch, inference, run_nuscenes_eval
from .anchor_utils import AnchorGenerator, assign_targets, encode_boxes, decode_boxes_torch
from .losses import DetectionLoss
from .post_processing import post_process, nms_bev

__all__ = [
    "SimplePointPillars",
    "NuScenesDetDataset",
    "train_one_epoch",
    "inference",
    "run_nuscenes_eval",
    "AnchorGenerator",
    "assign_targets",
    "encode_boxes",
    "decode_boxes_torch",
    "DetectionLoss",
    "post_process",
    "nms_bev",
]
