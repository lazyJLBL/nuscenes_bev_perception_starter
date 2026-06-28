"""Lightweight perception adapters that can run without external CUDA ops."""

from __future__ import annotations

from collections import deque
from typing import Dict, Iterable, List, Tuple

import numpy as np


class PointCloudClusterDetector:
    """
    A deterministic LiDAR clustering baseline.

    This is not a replacement for PointPillars/SECOND/CenterPoint. It is a real,
    runnable smoke baseline for comparison plumbing: it consumes points and emits
    coarse 3D boxes without training or fake thresholds.
    """

    def __init__(
        self,
        point_cloud_range: Tuple[float, float, float, float, float, float] = (-51.2, -51.2, -5.0, 51.2, 51.2, 3.0),
        cell_size: float = 1.0,
        min_cell_points: int = 3,
        min_cluster_points: int = 18,
        max_detections: int = 80,
    ):
        self.point_cloud_range = point_cloud_range
        self.cell_size = cell_size
        self.min_cell_points = min_cell_points
        self.min_cluster_points = min_cluster_points
        self.max_detections = max_detections

    def _filter_points(self, points: np.ndarray) -> np.ndarray:
        points = np.asarray(points, dtype=np.float32)
        if points.ndim != 2 or points.shape[1] < 3:
            return np.zeros((0, 4), dtype=np.float32)
        finite = np.isfinite(points[:, :3]).all(axis=1)
        x_min, y_min, z_min, x_max, y_max, z_max = self.point_cloud_range
        mask = (
            finite
            & (points[:, 0] >= x_min) & (points[:, 0] < x_max)
            & (points[:, 1] >= y_min) & (points[:, 1] < y_max)
            & (points[:, 2] >= z_min) & (points[:, 2] < z_max)
            & (points[:, 2] > -2.2)
        )
        return points[mask, :4]

    def _build_cells(self, points: np.ndarray) -> Dict[Tuple[int, int], np.ndarray]:
        x_min, y_min = self.point_cloud_range[0], self.point_cloud_range[1]
        xy = np.floor((points[:, :2] - np.array([x_min, y_min])) / self.cell_size).astype(np.int32)
        cell_to_indices: Dict[Tuple[int, int], List[int]] = {}
        for idx, cell in enumerate(xy):
            key = (int(cell[0]), int(cell[1]))
            cell_to_indices.setdefault(key, []).append(idx)
        return {
            cell: np.asarray(indices, dtype=np.int64)
            for cell, indices in cell_to_indices.items()
            if len(indices) >= self.min_cell_points
        }

    def _connected_components(self, cells: Iterable[Tuple[int, int]]) -> List[List[Tuple[int, int]]]:
        remaining = set(cells)
        components: List[List[Tuple[int, int]]] = []
        neighbors = [(dx, dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1) if not (dx == 0 and dy == 0)]

        while remaining:
            start = remaining.pop()
            comp = [start]
            queue = deque([start])
            while queue:
                cx, cy = queue.popleft()
                for dx, dy in neighbors:
                    nxt = (cx + dx, cy + dy)
                    if nxt in remaining:
                        remaining.remove(nxt)
                        comp.append(nxt)
                        queue.append(nxt)
            components.append(comp)
        return components

    def predict(self, points: np.ndarray) -> Dict[str, np.ndarray]:
        filtered = self._filter_points(points)
        if len(filtered) == 0:
            return {
                "boxes": np.zeros((0, 7), dtype=np.float32),
                "scores": np.zeros((0,), dtype=np.float32),
                "labels": np.zeros((0,), dtype=np.int64),
            }

        cell_to_indices = self._build_cells(filtered)
        boxes: List[np.ndarray] = []
        scores: List[float] = []

        for component in self._connected_components(cell_to_indices.keys()):
            indices = np.concatenate([cell_to_indices[cell] for cell in component])
            cluster = filtered[indices]
            if len(cluster) < self.min_cluster_points:
                continue

            mins = cluster[:, :3].min(axis=0)
            maxs = cluster[:, :3].max(axis=0)
            extent = np.maximum(maxs - mins, np.array([0.5, 0.5, 0.5], dtype=np.float32))
            if extent[0] > 18.0 or extent[1] > 18.0:
                continue

            center = (mins + maxs) / 2.0
            w = float(np.clip(extent[1], 0.6, 4.0))
            l = float(np.clip(extent[0], 0.6, 8.0))
            h = float(np.clip(extent[2], 0.5, 4.0))
            box = np.array([center[0], center[1], center[2], w, l, h, 0.0], dtype=np.float32)
            boxes.append(box)
            scores.append(float(np.clip(np.log1p(len(cluster)) / 7.0, 0.05, 0.95)))

        if not boxes:
            return {
                "boxes": np.zeros((0, 7), dtype=np.float32),
                "scores": np.zeros((0,), dtype=np.float32),
                "labels": np.zeros((0,), dtype=np.int64),
            }

        boxes_arr = np.stack(boxes).astype(np.float32)
        scores_arr = np.asarray(scores, dtype=np.float32)
        order = scores_arr.argsort()[::-1][: self.max_detections]
        return {
            "boxes": boxes_arr[order],
            "scores": scores_arr[order],
            "labels": np.zeros((len(order),), dtype=np.int64),
        }
