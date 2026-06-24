import torch
from torch.utils.data import Dataset
import numpy as np
import os
import pickle
from typing import Dict, List, Tuple
from nuscenes.nuscenes import NuScenes
from nuscenes.utils.data_classes import LidarPointCloud, Box
from pyquaternion import Quaternion

class NuScenesDetDataset(Dataset):
    """
    Dataset for 3D object detection on nuScenes using LiDAR.
    Loads data and performs simple PointPillars voxelization.
    """
    def __init__(
        self,
        nusc: NuScenes,
        tokens_file: str,
        classes: List[str],
        point_cloud_range: List[float] = [-51.2, -51.2, -5.0, 51.2, 51.2, 3.0],
        voxel_size: List[float] = [0.2, 0.2, 8.0],
        max_points_per_pillar: int = 32,
        max_pillars: int = 16000,
        training: bool = True
    ):
        self.nusc = nusc
        with open(tokens_file, "rb") as f:
            self.tokens = pickle.load(f)
            
        self.classes = classes
        self.class_to_idx = {c: i for i, c in enumerate(classes)}
        
        self.point_cloud_range = np.array(point_cloud_range, dtype=np.float32)
        self.voxel_size = np.array(voxel_size, dtype=np.float32)
        self.max_points_per_pillar = max_points_per_pillar
        self.max_pillars = max_pillars
        self.training = training
        
        self.grid_size = np.round((self.point_cloud_range[3:6] - self.point_cloud_range[0:3]) / self.voxel_size).astype(np.int32)

    def __len__(self) -> int:
        return len(self.tokens)

    def voxelize(self, points: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Pure numpy voxelization (slow but works without custom CUDA ops).
        points: [N, 4] (x, y, z, intensity)
        """
        # Filter points outside range
        mask = (points[:, 0] >= self.point_cloud_range[0]) & (points[:, 0] < self.point_cloud_range[3]) & \
               (points[:, 1] >= self.point_cloud_range[1]) & (points[:, 1] < self.point_cloud_range[4]) & \
               (points[:, 2] >= self.point_cloud_range[2]) & (points[:, 2] < self.point_cloud_range[5])
        points = points[mask]
        
        # Calculate voxel indices: (x, y, z) -> (x_idx, y_idx, z_idx)
        coords = np.floor((points[:, :3] - self.point_cloud_range[:3]) / self.voxel_size).astype(np.int32)
        
        # Pillar is just 2D grid, so z_idx is 0
        coords[:, 2] = 0 
        
        # Create a unique integer for each voxel (x, y, z)
        # Assuming max dimensions fits in int64
        # coord_hash = z * (W * H) + y * W + x
        voxel_coords_hash = coords[:, 2] * (self.grid_size[0] * self.grid_size[1]) + \
                            coords[:, 1] * self.grid_size[0] + \
                            coords[:, 0]
                            
        # Find unique voxels
        unique_hashes, unique_indices, inverse_indices = np.unique(voxel_coords_hash, return_index=True, return_inverse=True)
        
        num_pillars = min(len(unique_hashes), self.max_pillars)
        
        pillar_features = np.zeros((num_pillars, self.max_points_per_pillar, 9), dtype=np.float32)
        pillar_coords = np.zeros((num_pillars, 3), dtype=np.int32)
        num_points_per_pillar = np.zeros(num_pillars, dtype=np.int32)
        
        # Group points into pillars
        # This loop in python is slow, but acceptable for CPU-only mini dataset training
        for i in range(num_pillars):
            point_indices = np.where(inverse_indices == i)[0]
            num_pts = len(point_indices)
            
            if num_pts > self.max_points_per_pillar:
                # Randomly sample if too many
                point_indices = np.random.choice(point_indices, self.max_points_per_pillar, replace=False)
                num_pts = self.max_points_per_pillar
                
            pts = points[point_indices]
            
            # Center of the pillar
            pillar_coords[i] = coords[point_indices[0]]
            
            # Calculate geometric augmentations (xc, yc, zc, xp, yp)
            # xc, yc, zc = distance to arithmetic mean of points in the pillar
            mean_xyz = pts[:, :3].mean(axis=0)
            center_offset = pts[:, :3] - mean_xyz
            
            # xp, yp = distance to pillar center
            pillar_center_x = pillar_coords[i, 0] * self.voxel_size[0] + self.point_cloud_range[0] + self.voxel_size[0] / 2
            pillar_center_y = pillar_coords[i, 1] * self.voxel_size[1] + self.point_cloud_range[1] + self.voxel_size[1] / 2
            
            offset_x = pts[:, 0] - pillar_center_x
            offset_y = pts[:, 1] - pillar_center_y
            
            # Combine
            feat = np.zeros((num_pts, 9), dtype=np.float32)
            feat[:, 0:4] = pts[:, 0:4] # x, y, z, intensity
            feat[:, 4:7] = center_offset # xc, yc, zc
            feat[:, 7] = offset_x
            feat[:, 8] = offset_y
            
            pillar_features[i, :num_pts, :] = feat
            num_points_per_pillar[i] = num_pts
            
        return pillar_features, pillar_coords, num_points_per_pillar

    def __getitem__(self, idx: int) -> Dict:
        sample_token = self.tokens[idx]
        sample = self.nusc.get('sample', sample_token)
        
        # 1. Load LiDAR points
        lidar_token = sample['data']['LIDAR_TOP']
        lidar_data = self.nusc.get('sample_data', lidar_token)
        pcl_path = os.path.join(self.nusc.dataroot, lidar_data['filename'])
        
        pc = LidarPointCloud.from_file(pcl_path)
        points = pc.points.T # [N, 4]
        
        # 2. Voxelization
        pillar_features, pillar_coords, num_points = self.voxelize(points)
        
        data_dict = {
            "sample_token": sample_token,
            "pillar_features": pillar_features,
            "pillar_coords": pillar_coords,
            "num_points": num_points,
        }
        
        # 3. Load GT boxes if training
        if self.training:
            gt_boxes = []
            gt_classes = []
            
            _, boxes, _ = self.nusc.get_sample_data(lidar_token)
            
            for box in boxes:
                # Basic class filtering/mapping
                name = box.name
                # Simplify class names (e.g., vehicle.car -> car)
                mapped_name = name.split('.')[1] if '.' in name else name
                if mapped_name == 'pedestrian':
                    # Sometimes pedestrian is human.pedestrian
                    mapped_name = 'pedestrian'
                    
                matched_class = None
                for c in self.classes:
                    if c in name:
                        matched_class = c
                        break
                        
                if matched_class is not None:
                    # [x, y, z, w, l, h, yaw]
                    # Note: Box in nuScenes has w, l, h.
                    yaw = box.orientation.yaw_pitch_roll[0]
                    # We store [x, y, z, w, l, h, yaw]
                    gt_box = np.array([
                        box.center[0], box.center[1], box.center[2],
                        box.wlh[0], box.wlh[1], box.wlh[2],
                        yaw
                    ], dtype=np.float32)
                    
                    gt_boxes.append(gt_box)
                    gt_classes.append(self.class_to_idx[matched_class])
                    
            if len(gt_boxes) > 0:
                data_dict["gt_boxes"] = np.stack(gt_boxes)
                data_dict["gt_classes"] = np.array(gt_classes, dtype=np.int64)
            else:
                data_dict["gt_boxes"] = np.zeros((0, 7), dtype=np.float32)
                data_dict["gt_classes"] = np.zeros((0,), dtype=np.int64)
                
        return data_dict

def collate_fn(batch_list: List[Dict]) -> Dict:
    """Collate function for the DataLoader."""
    pillar_features_list = []
    pillar_coords_list = []
    num_points_list = []
    
    gt_boxes_list = []
    gt_classes_list = []
    sample_tokens = []
    
    for i, data_dict in enumerate(batch_list):
        sample_tokens.append(data_dict["sample_token"])
        
        pillar_features_list.append(data_dict["pillar_features"])
        
        # Prepend batch index to coords
        # coords is [num_pillars, 3] (x, y, z)
        # We want [num_pillars, 4] (batch_idx, z, y, x) for PillarScatter
        coords = data_dict["pillar_coords"]
        coords_with_batch = np.pad(coords, ((0, 0), (1, 0)), mode='constant', constant_values=i)
        # Swap x, y, z to z, y, x to match spconv/scatter conventions
        coords_with_batch[:, 1:] = coords_with_batch[:, [3, 2, 1]]
        pillar_coords_list.append(coords_with_batch)
        
        num_points_list.append(data_dict["num_points"])
        
        if "gt_boxes" in data_dict:
            gt_boxes_list.append(data_dict["gt_boxes"])
            gt_classes_list.append(data_dict["gt_classes"])
            
    ret = {
        "sample_tokens": sample_tokens,
        "pillar_features": torch.from_numpy(np.concatenate(pillar_features_list, axis=0)),
        "pillar_coords": torch.from_numpy(np.concatenate(pillar_coords_list, axis=0)),
        "num_points": torch.from_numpy(np.concatenate(num_points_list, axis=0)),
        "batch_size": len(batch_list)
    }
    
    if len(gt_boxes_list) > 0:
        ret["gt_boxes"] = gt_boxes_list # List of arrays
        ret["gt_classes"] = gt_classes_list # List of arrays
        
    return ret
