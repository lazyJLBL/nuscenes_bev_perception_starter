# 后续学习路线：从感知到规划

> 完成本项目后的进阶学习路线图。

## 1. 学习路线总览

```
你在这里
    ↓
┌────────────────────────────┐
│  本项目: 入门感知           │
│  - nuScenes 数据理解        │
│  - 坐标系转换               │
│  - LiDAR BEV 生成           │
│  - PointPillars 3D 检测     │
└────────────┬───────────────┘
             ↓
┌────────────────────────────┐
│  进阶感知                   │
│  - BEVFormer               │
│  - BEVFusion               │
│  - PETR / StreamPETR        │
│  - Occupancy Networks       │
└────────────┬───────────────┘
             ↓
┌────────────────────────────┐
│  预测 (Prediction)          │
│  - 运动预测                 │
│  - 轨迹预测                 │
│  - 意图预测                 │
└────────────┬───────────────┘
             ↓
┌────────────────────────────┐
│  规划 (Planning)            │
│  - 路径规划                 │
│  - 决策                     │
│  - UniAD (端到端)           │
└────────────────────────────┘
```

## 2. 进阶感知

### 2.1 BEVFormer

**论文**: BEVFormer: Learning Bird's-Eye-View Representation from Multi-Camera Images via Spatiotemporal Transformers (ECCV 2022)

**核心思想**:
- 使用 Transformer 将多个摄像头图像特征转换到 BEV 空间
- 引入时序信息（利用历史帧）
- 纯视觉方案（只用摄像头，不用 LiDAR）

**为什么学它**:
- 理解如何从图像生成 BEV 特征
- Transformer 在自动驾驶中的经典应用
- 纯视觉方案成本低

**代码**: https://github.com/fundamentalvision/BEVFormer

### 2.2 BEVFusion

**论文**: BEVFusion: Multi-Task Multi-Sensor Fusion with Unified Bird's-Eye View Representation (ICRA 2023)

**核心思想**:
- 分别从 Camera 和 LiDAR 提取 BEV 特征
- 在 BEV 空间进行特征融合
- 支持多任务（检测 + 分割）

**为什么学它**:
- 理解多传感器融合
- BEV 空间融合的经典方案
- 性能领先

**代码**: https://github.com/mit-han-lab/bevfusion

### 2.3 PETR / StreamPETR

**论文**:
- PETR: Position Embedding Transformation for Multi-View 3D Object Detection (ECCV 2022)
- StreamPETR: Exploring Object-Centric Temporal Modeling for Efficient Multi-Frame 3D Object Detection (ICCV 2023)

**核心思想**:
- 将 3D 位置编码到 2D 图像特征中
- StreamPETR 加入了高效的时序建模
- 不需要显式构建 BEV 特征图

**为什么学它**:
- 理解不构建 BEV 的替代方案
- 高效的时序建模方法

**代码**: https://github.com/megvii-research/PETR

### 2.4 Occupancy Networks

**论文**: 多篇，如 SurroundOcc, OccFormer, FB-OCC 等

**核心思想**:
- 将 3D 空间离散化为体素网格
- 预测每个体素是否被占据、属于什么类别
- 比 3D 检测更精细（可以描述不规则形状的物体）

**为什么学它**:
- 自动驾驶感知的新趋势
- 可以表示任意形状的障碍物
- 对规划更友好

## 3. 预测 (Prediction)

### 3.1 运动预测 (Motion Prediction)

**任务**: 预测其他交通参与者未来的运动轨迹

**输入**: 历史轨迹 + 地图信息 + 感知结果
**输出**: 未来 N 秒的轨迹（通常 3-8 秒）

**代表工作**:
- HiVT: 基于 Transformer 的轨迹预测
- QCNet: 查询中心的轨迹预测
- MTR: 运动 Transformer

### 3.2 意图预测

**任务**: 预测其他车辆的驾驶意图（左转、右转、直行、变道等）

## 4. 规划 (Planning)

### 4.1 传统规划

- **路径规划**: A*, RRT, Lattice Planner
- **决策**: 状态机、规则引擎
- **运动规划**: 优化方法、MPC

### 4.2 端到端自动驾驶

#### UniAD

**论文**: Planning-oriented Autonomous Driving (CVPR 2023 Best Paper)

**核心思想**:
- 将感知、预测、规划统一在一个端到端模型中
- 以规划为导向设计整个系统
- 包含：检测 → 跟踪 → 地图分割 → 运动预测 → 占据预测 → 规划

**为什么学它**:
- 理解端到端自动驾驶的范式
- CVPR 2023 最佳论文
- 连接感知与规划

**代码**: https://github.com/OpenDriveLab/UniAD

## 5. 推荐学习顺序

```
第 1 个月: 本项目 + 精读 PointPillars 论文
第 2 个月: 跑通 BEVFormer + 理解 Camera BEV
第 3 个月: 跑通 BEVFusion + 理解多传感器融合
第 4 个月: 学习 Occupancy + 3D 语义分割
第 5 个月: 学习运动预测 (HiVT / QCNet)
第 6 个月: 学习 UniAD + 理解端到端方案
```

## 6. 推荐资源

### 论文阅读
- [Papers With Code - nuScenes Leaderboard](https://paperswithcode.com/dataset/nuscenes)
- [OpenDriveLab](https://github.com/OpenDriveLab) — 多个优秀开源项目

### 课程
- [Self-Driving Cars Specialization (Coursera)](https://www.coursera.org/specializations/self-driving-cars)
- [MIT 6.S094: Deep Learning for Self-Driving Cars](https://selfdrivingcars.mit.edu/)

### 开源框架
- [MMDetection3D](https://github.com/open-mmlab/mmdetection3d) — 3D 检测框架
- [OpenPCDet](https://github.com/open-mmlab/OpenPCDet) — 点云检测框架
- [nuPlan](https://github.com/motional/nuplan-devkit) — 规划数据集和框架

### 社区
- [自动驾驶之心](https://www.zdjc.com/) — 中文自动驾驶社区
- [知乎 - 自动驾驶话题](https://www.zhihu.com/topic/20035585)
- [GitHub Awesome Lists](https://github.com/topics/autonomous-driving)
