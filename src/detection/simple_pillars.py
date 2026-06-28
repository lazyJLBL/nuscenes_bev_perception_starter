import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Dict, List, Tuple


class PillarVFE(nn.Module):
    """Simplified Pillar Feature Encoder."""
    def __init__(self, in_channels: int, out_channels: int):
        super().__init__()
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

        batch_idx = coords[:, 0].long()
        y_idx = coords[:, 2].long()
        x_idx = coords[:, 3].long()

        valid_mask = (y_idx >= 0) & (y_idx < ny) & (x_idx >= 0) & (x_idx < nx)
        batch_idx = batch_idx[valid_mask]
        y_idx = y_idx[valid_mask]
        x_idx = x_idx[valid_mask]
        features = pillar_features[valid_mask]

        batch_spatial_features[batch_idx, :, y_idx, x_idx] = features

        return batch_spatial_features


class SimpleBEVBackbone(nn.Module):
    """2D CNN backbone for BEV feature extraction.
    Outputs feature map at 1/4 of input resolution (512→128) for efficient anchor-based detection."""
    def __init__(self, in_channels: int):
        super().__init__()

        # 下采样路径
        self.block1 = nn.Sequential(
            nn.Conv2d(in_channels, 64, kernel_size=3, padding=1, stride=2, bias=False),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.Conv2d(64, 64, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
        )  # -> H/2, W/2

        self.block2 = nn.Sequential(
            nn.Conv2d(64, 128, kernel_size=3, padding=1, stride=2, bias=False),
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True),
            nn.Conv2d(128, 128, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True),
        )  # -> H/4, W/4

        # 多尺度特征融合 (都在 H/4 分辨率)
        # 把 block1 的特征下采样到 block2 的尺度
        self.down1 = nn.Sequential(
            nn.Conv2d(64, 128, kernel_size=3, padding=1, stride=2, bias=False),
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True),
        )

        # 精炼 block2 的特征
        self.refine2 = nn.Sequential(
            nn.Conv2d(128, 128, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x1 = self.block1(x)     # [B, 64, H/2, W/2]
        x2 = self.block2(x1)    # [B, 128, H/4, W/4]

        d1 = self.down1(x1)     # [B, 128, H/4, W/4]
        d2 = self.refine2(x2)   # [B, 128, H/4, W/4]

        out = torch.cat([d1, d2], dim=1)  # [B, 256, H/4, W/4]
        return out


class DetectionHead(nn.Module):
    """Anchor-based Detection Head."""
    def __init__(self, in_channels: int, num_classes: int, num_anchors_per_loc: int):
        super().__init__()
        self.num_classes = num_classes
        self.num_anchors_per_loc = num_anchors_per_loc

        box_code_size = 8  # [dx, dy, dz, dw, dl, dh, rot_sin, rot_cos]

        self.conv_cls = nn.Conv2d(in_channels, num_anchors_per_loc * num_classes, kernel_size=1)
        self.conv_box = nn.Conv2d(in_channels, num_anchors_per_loc * box_code_size, kernel_size=1)
        self.conv_dir_cls = nn.Conv2d(in_channels, num_anchors_per_loc * 2, kernel_size=1)

    def forward(self, x: torch.Tensor) -> Dict[str, torch.Tensor]:
        cls_preds = self.conv_cls(x)
        box_preds = self.conv_box(x)
        dir_cls_preds = self.conv_dir_cls(x)

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
    Complete, self-contained PointPillars architecture with real anchor-based detection.
    """
    def __init__(
        self,
        point_cloud_range: List[float],
        voxel_size: List[float],
        num_classes: int,
        classes: List[str] = None,
        max_num_points: int = 32,
        max_num_pillars: int = 16000,
        num_point_features: int = 4  # (x, y, z, intensity)
    ):
        super().__init__()
        self.point_cloud_range = point_cloud_range
        self.voxel_size = voxel_size
        self.num_classes = num_classes
        self.classes = classes or ['car', 'pedestrian', 'bicycle', 'bus', 'truck'][:num_classes]

        in_channels = num_point_features + 5  # + (xc, yc, zc, xp, yp)
        vfe_out_channels = 64

        grid_size = [
            int(round((point_cloud_range[3] - point_cloud_range[0]) / voxel_size[0])),
            int(round((point_cloud_range[4] - point_cloud_range[1]) / voxel_size[1]))
        ]

        self.vfe = PillarVFE(in_channels=in_channels, out_channels=vfe_out_channels)
        self.scatter = PillarScatter(output_shape=(grid_size[1], grid_size[0]), num_input_features=vfe_out_channels)

        self.backbone = SimpleBEVBackbone(in_channels=vfe_out_channels)

        # 特征图尺寸 = 原始网格 / 4（backbone 步幅为 4）
        self.feature_map_size = (grid_size[1] // 4, grid_size[0] // 4)  # (H, W)

        # 每个位置 2 个旋转角 × num_classes 个类别 = 2*C anchors
        num_anchors_per_loc = num_classes * 2

        self.head = DetectionHead(in_channels=256, num_classes=num_classes, num_anchors_per_loc=num_anchors_per_loc)

        # 生成并注册 anchors
        from .anchor_utils import AnchorGenerator
        self.anchor_generator = AnchorGenerator(
            point_cloud_range=point_cloud_range,
            feature_map_size=self.feature_map_size,
            classes=self.classes,
        )
        self.register_buffer('anchors', torch.from_numpy(self.anchor_generator.anchors))

    def forward(self, batch_dict: Dict[str, torch.Tensor]) -> Dict[str, torch.Tensor]:
        """
        Args:
            batch_dict:
                - pillar_features: [num_pillars, max_points, feature_dim]
                - pillar_coords: [num_pillars, 4] with (batch_idx, z, y, x)
                - num_points: [num_pillars]
                - batch_size: int
        """
        # 1. Pillar 特征编码
        pillar_features = self.vfe(batch_dict["pillar_features"], batch_dict["num_points"])

        # 2. 散射到 BEV 伪图像
        spatial_features = self.scatter(pillar_features, batch_dict["pillar_coords"], batch_dict["batch_size"])

        # 3. BEV Backbone
        bev_features = self.backbone(spatial_features)

        # 4. 检测头
        preds_dict = self.head(bev_features)

        return preds_dict

    @torch.no_grad()
    def predict(self, batch_dict, score_threshold=0.3, nms_threshold=0.2):
        """运行推理并进行后处理（decode + NMS）。"""
        from .post_processing import post_process
        preds_dict = self.forward(batch_dict)
        results = post_process(
            preds_dict, self.anchors,
            self.num_classes,
            score_threshold=score_threshold,
            nms_threshold=nms_threshold,
        )
        return results
