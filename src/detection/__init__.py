"""
Simple 3D Detection Baseline for nuScenes.
Self-contained implementation of a simplified PointPillars-like network.
"""

from .simple_pillars import SimplePointPillars
from .nuscenes_dataset import NuScenesDetDataset
from .train_utils import train_one_epoch, inference, run_nuscenes_eval

__all__ = [
    "SimplePointPillars",
    "NuScenesDetDataset",
    "train_one_epoch",
    "inference",
    "run_nuscenes_eval",
]
