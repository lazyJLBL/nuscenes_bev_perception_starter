"""
Loss functions for 3D object detection.
- SigmoidFocalLoss: 处理正负样本极度不平衡
- WeightedSmoothL1Loss: 框回归损失
- DetectionLoss: 统一封装
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


class SigmoidFocalLoss(nn.Module):
    """
    Focal Loss for dense classification.
    FL(p_t) = -alpha_t * (1 - p_t)^gamma * log(p_t)
    """
    def __init__(self, alpha: float = 0.25, gamma: float = 2.0):
        super().__init__()
        self.alpha = alpha
        self.gamma = gamma

    def forward(self, pred, target, pos_mask, neg_mask):
        """
        Args:
            pred: [N, num_classes] raw logits
            target: [N] integer class labels (0=background, 1..C=foreground)
            pos_mask: [N] boolean
            neg_mask: [N] boolean
        Returns:
            loss: scalar
        """
        num_classes = pred.shape[1]

        # One-hot encode (只对前景类别)
        target_one_hot = torch.zeros_like(pred)
        pos_indices = torch.where(pos_mask)[0]
        if pos_indices.numel() > 0:
            fg_classes = target[pos_mask] - 1  # 1-indexed -> 0-indexed
            fg_classes = fg_classes.clamp(0, num_classes - 1)
            target_one_hot[pos_indices, fg_classes] = 1.0

        # 只在正样本和负样本上计算 loss
        valid_mask = pos_mask | neg_mask
        pred = pred[valid_mask]
        target_one_hot = target_one_hot[valid_mask]

        p = torch.sigmoid(pred)
        ce = F.binary_cross_entropy_with_logits(pred, target_one_hot, reduction='none')

        p_t = p * target_one_hot + (1 - p) * (1 - target_one_hot)
        alpha_t = self.alpha * target_one_hot + (1 - self.alpha) * (1 - target_one_hot)

        loss = alpha_t * (1 - p_t) ** self.gamma * ce

        num_pos = max(pos_mask.sum().item(), 1.0)
        return loss.sum() / num_pos


class WeightedSmoothL1Loss(nn.Module):
    """SmoothL1 loss for box regression, only on positive anchors."""

    def __init__(self, beta: float = 1.0 / 9.0):
        super().__init__()
        self.beta = beta

    def forward(self, pred, target, pos_mask):
        """
        Args:
            pred: [N, 8] predicted box residuals
            target: [N, 8] target box residuals
            pos_mask: [N] boolean
        """
        if pos_mask.sum() == 0:
            return pred.sum() * 0.0

        pred_pos = pred[pos_mask]
        target_pos = target[pos_mask]

        diff = torch.abs(pred_pos - target_pos)
        loss = torch.where(
            diff < self.beta,
            0.5 * diff ** 2 / self.beta,
            diff - 0.5 * self.beta
        )

        num_pos = max(pos_mask.sum().item(), 1.0)
        return loss.sum() / num_pos


class DetectionLoss(nn.Module):
    """Combined detection loss: classification + regression + direction."""

    def __init__(self, cls_weight: float = 1.0, reg_weight: float = 2.0, dir_weight: float = 0.2):
        super().__init__()
        self.cls_loss_fn = SigmoidFocalLoss(alpha=0.25, gamma=2.0)
        self.reg_loss_fn = WeightedSmoothL1Loss()
        self.cls_weight = cls_weight
        self.reg_weight = reg_weight
        self.dir_weight = dir_weight

    def forward(self, preds_dict, targets_dict):
        """
        Args:
            preds_dict: {'cls_preds': [B, N, C], 'box_preds': [B, N, 8], 'dir_cls_preds': [B, N, 2]}
            targets_dict: {'cls_targets': [B, N], 'box_targets': [B, N, 8], 'dir_targets': [B, N],
                           'pos_mask': [B, N], 'neg_mask': [B, N]}
        Returns:
            total_loss: scalar
            loss_dict: dict of individual losses
        """
        batch_size = preds_dict['cls_preds'].shape[0]

        total_cls_loss = 0.0
        total_reg_loss = 0.0
        total_dir_loss = 0.0

        for b in range(batch_size):
            cls_pred = preds_dict['cls_preds'][b]
            box_pred = preds_dict['box_preds'][b]
            dir_pred = preds_dict['dir_cls_preds'][b]

            cls_target = targets_dict['cls_targets'][b]
            box_target = targets_dict['box_targets'][b]
            dir_target = targets_dict['dir_targets'][b]
            pos_mask = targets_dict['pos_mask'][b]
            neg_mask = targets_dict['neg_mask'][b]

            total_cls_loss += self.cls_loss_fn(cls_pred, cls_target, pos_mask, neg_mask)
            total_reg_loss += self.reg_loss_fn(box_pred, box_target, pos_mask)

            if pos_mask.sum() > 0:
                dir_loss = F.cross_entropy(
                    dir_pred[pos_mask], dir_target[pos_mask], reduction='mean'
                )
                total_dir_loss += dir_loss

        total_cls_loss /= batch_size
        total_reg_loss /= batch_size
        total_dir_loss = total_dir_loss / batch_size if isinstance(total_dir_loss, torch.Tensor) else 0.0

        total_loss = (
            self.cls_weight * total_cls_loss +
            self.reg_weight * total_reg_loss +
            (self.dir_weight * total_dir_loss if isinstance(total_dir_loss, torch.Tensor) else 0.0)
        )

        return total_loss, {
            'loss_cls': total_cls_loss.item() if isinstance(total_cls_loss, torch.Tensor) else 0.0,
            'loss_reg': total_reg_loss.item() if isinstance(total_reg_loss, torch.Tensor) else 0.0,
            'loss_dir': total_dir_loss.item() if isinstance(total_dir_loss, torch.Tensor) else 0.0,
            'total_loss': total_loss.item() if isinstance(total_loss, torch.Tensor) else 0.0,
        }
