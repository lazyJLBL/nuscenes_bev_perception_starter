import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Dict, List, Tuple

class PillarVFE(nn.Module):
    """Simplified Pillar Feature Encoder."""
    def __init__(self, in_channels: int, out_channels: int):
        super().__init__()
        # In nuScenes, we often use (x, y, z, intensity, t) + (xc, yc, zc) + (xp, yp)
        # For simplicity, we assume the dataset provides [N, C] points where we use an MLP to map to out_channels.
        self.pfn_layers = nn.Sequential(
            nn.Linear(in_channels, out_channels, bias=False),
            nn.BatchNorm1d(out_channels, eps=1e-3, momentum=0.01),
            nn.ReLU(inplace=True)
        )

    def forward(self, features: torch.Tensor, num_points: torch.Tensor) -> torch.Tensor:
        """
        Args:
            features: [num_pillars, max_points_per_pillar, channels]
            num_points: [num_pillars]
        Returns:
            pillar_features: [num_pillars, out_channels]
        """
        num_pillars = features.shape[0]
        # Flatten for MLP
        features_flat = features.view(-1, features.shape[-1])
        features_flat = self.pfn_layers(features_flat)
        features = features_flat.view(num_pillars, -1, features_flat.shape[-1])
        
        # Max pooling over points in each pillar
        pillar_features, _ = features.max(dim=1)
        return pillar_features

class PillarScatter(nn.Module):
    """Scatters pillar features to a 2D BEV pseudo-image."""
    def __init__(self, output_shape: Tuple[int, int], num_input_features: int):
        super().__init__()
        self.output_shape = output_shape
        self.num_input_features = num_input_features

    def forward(self, pillar_features: torch.Tensor, coords: torch.Tensor, batch_size: int) -> torch.Tensor:
        """
        Args:
            pillar_features: [num_pillars, channels]
            coords: [num_pillars, 4] with (batch_idx, z, y, x)
            batch_size: int
        Returns:
            batch_spatial_features: [batch_size, channels, ny, nx]
        """
        ny, nx = self.output_shape
        batch_spatial_features = torch.zeros(
            (batch_size, self.num_input_features, ny, nx),
            dtype=pillar_features.dtype,
            device=pillar_features.device,
        )
        
        # coords are usually (batch_idx, z_idx, y_idx, x_idx)
        # Since pillars span the full Z range, z_idx is always 0
        batch_idx = coords[:, 0].long()
        y_idx = coords[:, 2].long()
        x_idx = coords[:, 3].long()
        
        # Keep indices within bounds (in case of edge effects)
        valid_mask = (y_idx >= 0) & (y_idx < ny) & (x_idx >= 0) & (x_idx < nx)
        batch_idx = batch_idx[valid_mask]
        y_idx = y_idx[valid_mask]
        x_idx = x_idx[valid_mask]
        features = pillar_features[valid_mask]
        
        # Scatter features. A pillar maps to exactly one (x, y) location.
        batch_spatial_features[batch_idx, :, y_idx, x_idx] = features
        
        return batch_spatial_features

class SimpleBEVBackbone(nn.Module):
    """A simplified 2D CNN backbone for processing BEV pseudo-images."""
    def __init__(self, in_channels: int):
        super().__init__()
        
        # A simple downsampling and upsampling network.
        # This is a highly miniaturized version of the typical RPN/Backbone2D.
        self.block1 = nn.Sequential(
            nn.Conv2d(in_channels, 64, kernel_size=3, padding=1, stride=2, bias=False),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.Conv2d(64, 64, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
        )
        self.block2 = nn.Sequential(
            nn.Conv2d(64, 128, kernel_size=3, padding=1, stride=2, bias=False),
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True),
            nn.Conv2d(128, 128, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True),
        )
        
        self.deblock1 = nn.Sequential(
            nn.ConvTranspose2d(64, 128, kernel_size=2, stride=2, bias=False),
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True),
        )
        self.deblock2 = nn.Sequential(
            nn.ConvTranspose2d(128, 128, kernel_size=4, stride=4, bias=False),
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True),
        )
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: [B, C, H, W]
        x1 = self.block1(x)
        x2 = self.block2(x1)
        
        up1 = self.deblock1(x1)
        up2 = self.deblock2(x2)
        
        # up1 and up2 should have the same spatial dimensions if input dims are divisible by 4
        # We concatenate features from different scales.
        out = torch.cat([up1, up2], dim=1)  # [B, 256, H, W]
        return out

class DetectionHead(nn.Module):
    """Simplified Anchor-based Detection Head."""
    def __init__(self, in_channels: int, num_classes: int, num_anchors_per_loc: int):
        super().__init__()
        self.num_classes = num_classes
        self.num_anchors_per_loc = num_anchors_per_loc
        
        # Output channels for regression: [dx, dy, dz, w, l, h, rot_sin, rot_cos] = 8
        box_code_size = 8
        
        self.conv_cls = nn.Conv2d(in_channels, num_anchors_per_loc * num_classes, kernel_size=1)
        self.conv_box = nn.Conv2d(in_channels, num_anchors_per_loc * box_code_size, kernel_size=1)
        # Direction classification (optional, usually 2 bins per anchor)
        self.conv_dir_cls = nn.Conv2d(in_channels, num_anchors_per_loc * 2, kernel_size=1)
        
    def forward(self, x: torch.Tensor) -> Dict[str, torch.Tensor]:
        # x: [B, C, H, W]
        cls_preds = self.conv_cls(x)    # [B, num_anchors * num_classes, H, W]
        box_preds = self.conv_box(x)    # [B, num_anchors * 8, H, W]
        dir_cls_preds = self.conv_dir_cls(x) # [B, num_anchors * 2, H, W]
        
        # Rearrange to [B, num_anchors_total, num_classes]
        B, _, H, W = cls_preds.shape
        cls_preds = cls_preds.permute(0, 2, 3, 1).contiguous().view(B, -1, self.num_classes)
        box_preds = box_preds.permute(0, 2, 3, 1).contiguous().view(B, -1, 8)
        dir_cls_preds = dir_cls_preds.permute(0, 2, 3, 1).contiguous().view(B, -1, 2)
        
        return {
            "cls_preds": cls_preds,
            "box_preds": box_preds,
            "dir_cls_preds": dir_cls_preds
        }

class SimplePointPillars(nn.Module):
    """
    Complete, self-contained PointPillars architecture.
    Suitable for CPU training as a baseline.
    """
    def __init__(
        self,
        point_cloud_range: List[float],
        voxel_size: List[float],
        num_classes: int,
        max_num_points: int = 32,
        max_num_pillars: int = 16000,
        num_point_features: int = 4  # (x, y, z, intensity)
    ):
        super().__init__()
        self.point_cloud_range = point_cloud_range
        self.voxel_size = voxel_size
        self.num_classes = num_classes
        
        # For PointPillars, features are usually augmented with geometric info:
        # (x, y, z, i, xc, yc, zc, xp, yp) -> 9 features typically
        # Here we just assume a simple feature set for the baseline.
        in_channels = num_point_features + 5 # + (xc, yc, zc, xp, yp)
        vfe_out_channels = 64
        
        grid_size = [
            int(round((point_cloud_range[3] - point_cloud_range[0]) / voxel_size[0])),
            int(round((point_cloud_range[4] - point_cloud_range[1]) / voxel_size[1]))
        ]
        
        self.vfe = PillarVFE(in_channels=in_channels, out_channels=vfe_out_channels)
        self.scatter = PillarScatter(output_shape=(grid_size[1], grid_size[0]), num_input_features=vfe_out_channels)
        
        self.backbone = SimpleBEVBackbone(in_channels=vfe_out_channels)
        
        # 1 anchor per location per class (simplified)
        num_anchors_per_loc = num_classes 
        
        self.head = DetectionHead(in_channels=256, num_classes=num_classes, num_anchors_per_loc=num_anchors_per_loc)

    def forward(self, batch_dict: Dict[str, torch.Tensor]) -> Dict[str, torch.Tensor]:
        """
        Args:
            batch_dict:
                - pillar_features: [num_pillars, max_points, feature_dim]
                - pillar_coords: [num_pillars, 4] with (batch_idx, z, y, x)
                - num_points: [num_pillars]
                - batch_size: int
        """
        # 1. Feature encoding
        pillar_features = self.vfe(batch_dict["pillar_features"], batch_dict["num_points"])
        
        # 2. Scatter to BEV
        spatial_features = self.scatter(pillar_features, batch_dict["pillar_coords"], batch_dict["batch_size"])
        
        # 3. Backbone
        bev_features = self.backbone(spatial_features)
        
        # 4. Detection Head
        preds_dict = self.head(bev_features)
        
        return preds_dict
