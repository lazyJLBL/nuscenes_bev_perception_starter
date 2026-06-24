# 3D 检测 Baseline 详解

> 本文面向自动驾驶初学者，解释 3D 目标检测的基本概念和 baseline 模型。

## 1. 3D 检测是什么

3D 目标检测是自动驾驶感知的核心任务之一：

**输入**: 传感器数据（LiDAR 点云、摄像头图像）

**输出**: 每个检测到的目标的：
- **3D 位置** [x, y, z]（在全局或 ego 坐标系中的中心点）
- **3D 尺寸** [width, length, height]
- **朝向** (yaw 角或四元数旋转)
- **类别** (car, pedestrian, truck, ...)
- **置信度** (0~1，模型对检测结果的确信程度)
- **速度** [vx, vy]（可选）

与 2D 检测（在图像上画矩形框）不同，3D 检测输出的是真实世界中的 3D 长方体。

## 2. PointPillars

### 2.1 基本思想

PointPillars (2019) 是一种高效的基于 LiDAR 的 3D 检测方法。

核心思想：将 3D 点云组织成 **柱体 (Pillars)**，而不是传统的 3D 体素。

```
传统体素化:           PointPillars:
┌─┬─┬─┐              ┌─┬─┬─┐
│ │ │ │ ← Z 方向     │ │ │ │ ← Z 方向不分格
├─┼─┼─┤  有多层       │ │ │ │   只有一层柱体
│ │ │ │              │ │ │ │
├─┼─┼─┤              │ │ │ │
│ │ │ │              │ │ │ │
└─┴─┴─┘              └─┴─┴─┘
3D 体素               2D 柱体（Pillar）
计算量大               计算量小
```

### 2.2 网络结构

```
LiDAR 点云
    ↓
Pillar Feature Net (将点云编码为柱体特征)
    ↓
Pseudo Image (将柱体特征散射到 2D BEV 平面)
    ↓
2D Backbone (标准 2D CNN，如 VGGNet)
    ↓
SSD Detection Head (输出 3D 检测结果)
```

### 2.3 优缺点

| 优点 | 缺点 |
|------|------|
| 推理速度快（可实时） | 精度不如 CenterPoint 等新方法 |
| 结构简单，易理解 | Z 方向信息损失（压缩成了柱体） |
| 训练稳定 | 对小目标检测效果一般 |

## 3. CenterPoint

### 3.1 基本思想

CenterPoint (2021) 是基于中心点的 3D 检测方法。

核心思想：先检测目标的**中心点**，再回归其 3D 属性。

```
LiDAR 点云
    ↓
3D Backbone (VoxelNet / PointPillars)
    ↓
BEV 特征图
    ↓
Center Heatmap Head → 检测中心点
    ↓
Property Regression Heads → 回归尺寸、旋转、速度等
```

### 3.2 与 PointPillars 的对比

| 对比项 | PointPillars | CenterPoint |
|--------|-------------|-------------|
| 检测方式 | Anchor-based | Center-based |
| 精度 | 中等 | 较高 |
| 速度 | 快 | 中等 |
| 复杂度 | 低 | 中等 |
| 是否需要 NMS | 是 | 否（或简化版） |

## 4. nuScenes 3D Detection 的输入输出

### 输入
- **LiDAR 点云**: (N, 5) 数组，每个点 [x, y, z, intensity, ring]
- **可选**: 摄像头图像（用于多模态融合）

### 输出（nuScenes 提交格式）
```json
{
  "results": {
    "<sample_token>": [
      {
        "sample_token": "xxx",
        "translation": [x, y, z],
        "size": [w, l, h],
        "rotation": [qw, qx, qy, qz],
        "velocity": [vx, vy],
        "detection_name": "car",
        "detection_score": 0.85,
        "attribute_name": "vehicle.moving"
      }
    ]
  }
}
```

## 5. 评估指标

### 5.1 mAP (mean Average Precision)

- 计算每个类别的 AP，然后取平均
- nuScenes 使用**基于中心距离的匹配**（而非 IoU）
- 匹配阈值：0.5m, 1m, 2m, 4m
- mAP 越高越好，满分 1.0

### 5.2 NDS (nuScenes Detection Score)

NDS 是 nuScenes 独有的综合指标，考虑了多个方面：

```
NDS = (1/10) × [5 × mAP + Σ(mATE, mASE, mAOE, mAVE, mAAE 的补)]
```

其中：
| 指标 | 全称 | 含义 |
|------|------|------|
| mATE | Average Translation Error | 位置误差（米） |
| mASE | Average Scale Error | 尺寸误差 |
| mAOE | Average Orientation Error | 朝向误差（弧度） |
| mAVE | Average Velocity Error | 速度误差 |
| mAAE | Average Attribute Error | 属性误差 |

NDS 越高越好，满分 1.0。

### 5.3 各模型在 nuScenes 上的典型性能

| 模型 | mAP | NDS | 备注 |
|------|-----|-----|------|
| PointPillars | ~30% | ~45% | LiDAR only, 基线 |
| CenterPoint | ~58% | ~65% | LiDAR only |
| BEVFusion | ~68% | ~71% | Camera + LiDAR |
| TransFusion | ~65% | ~70% | Camera + LiDAR |

> ⚠️ 以上数据为完整 nuScenes 数据集上的参考值，非 mini 数据集。

## 6. 本项目的 Baseline 实现 (SimplePointPillars)

为了在不需要复杂编译（尤其是 Windows 上的 CUDA 编译）的情况下跑通 3D 检测的全流程闭环，本项目实现了一个**自包含的纯 PyTorch** PointPillars (SimplePointPillars)。

### 6.1 核心特点
1. **纯 PyTorch**: 不依赖 `spconv`，使用简化的 Voxelizer 避开了 C++/CUDA 扩展。
2. **CPU 兼容**: 可以在没有 CUDA 的机器上运行验证流程（速度较慢，仅供教学）。
3. **闭环验证**: 包含数据准备、训练（Dummy Loss 跑通流程）、推理、评估和可视化。

### 6.2 流程与脚本
1. **准备数据**: `python scripts/06_prepare_detection_baseline.py --execute` 
   - 提取 nuScenes tokens 并分为 train/val 列表。
2. **训练**: `python scripts/07_train_baseline.py --execute`
   - 使用随机目标损失函数，确保网络各层梯度流动。
3. **推理**: `python scripts/08_inference_baseline.py --execute`
   - 对验证集进行前向推理，并生成符合 nuScenes submission 格式的 JSON。
4. **可视化**: `python scripts/09_visualize_predictions.py`
   - 在 BEV 俯视图上对比 Ground Truth 和预测框。
5. **指标检查**: `python scripts/10_check_detection_results.py`
   - 自动检查生成的各种产物，并读取打印核心评估指标（mAP，NDS 等）。

## 7. 为什么 mini 数据集训练结果不能代表真实性能

| 对比项 | v1.0-mini | v1.0-trainval |
|--------|-----------|---------------|
| 场景数 | 10 | 850 |
| 关键帧数 | ~400 | ~40,000 |
| 数据量 | ~4 GB | ~300+ GB |
| 训练结果 | 仅验证流程 | 代表真实性能 |

mini 数据集太小，且本项目的 Baseline 采用的是简化版结构（未引入复杂的 Anchor Assigning 与 NMS），因此训练结果仅用于验证代码闭环（mAP / NDS 趋近于 0），不要期待在 mini 数据集上获得可用的真实感知能力。

**结论**: 用 mini 跑通流程，用完整的检测框架（如 OpenPCDet 或 MMDetection3D）和完整数据集去训练出可用性能。
