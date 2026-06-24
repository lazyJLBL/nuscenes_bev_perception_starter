# 坐标系详解

> 本文面向自动驾驶初学者，详细解释 nuScenes 中的坐标系和变换。

## 1. 为什么自动驾驶有这么多坐标系？

自动驾驶车辆上有多个传感器（摄像头、LiDAR、Radar），每个传感器有自己的坐标系。

为了将不同传感器的数据融合到一起，我们需要**坐标系转换**。

想象一下：
- LiDAR 说"前方 10 米有一个物体"——这个"前方"是 LiDAR 的前方
- 摄像头说"图像中央有一个物体"——这个"中央"是摄像头的视角
- 我们需要把它们统一到同一个参考框架中

## 2. nuScenes 中的四个坐标系

### 2.1 传感器坐标系 (Sensor Frame)

每个传感器（LiDAR、Camera）都有自己的坐标系。

**LiDAR 坐标系:**
```
      Z (上)
      |
      |
      |_____ X (前)
     /
    Y (左)
```
- X 轴: 指向车辆前方
- Y 轴: 指向车辆左方
- Z 轴: 指向车辆上方
- 原点: LiDAR 传感器中心

**Camera 坐标系:**
```
    Z (前/深度)
   /
  /
 /_____ X (右)
 |
 Y (下)
```
- X 轴: 指向图像右方
- Y 轴: 指向图像下方
- Z 轴: 指向相机前方（深度方向）
- 原点: 相机光心

> ⚠️ **注意**: Camera 坐标系和 LiDAR 坐标系的轴方向不同！
> 这是新手最容易犯的错误之一。

### 2.2 Ego Vehicle 坐标系 (Ego Frame)

以车辆后轴中心为原点的坐标系。

```
      Z (上)
      |
      |
      |_____ X (前)
     /
    Y (左)
```
- 与 LiDAR 坐标系方向一致，但原点不同
- 原点在车辆后轴中心

### 2.3 全局坐标系 (Global Frame)

固定在地图上的坐标系。

- 使用 UTM 坐标（一种地理坐标系）
- 所有帧、所有传感器的数据都可以转换到这个坐标系
- 标注框 (sample_annotation) 的坐标就是在全局坐标系下的

## 3. calibrated_sensor 和 ego_pose 的区别

这两个概念是理解坐标系转换的关键：

### calibrated_sensor（传感器标定）
- **描述**: 传感器相对于车辆的位置和朝向
- **特点**: 固定不变（传感器安装后不会动）
- **作用**: Sensor Frame ↔ Ego Frame 的转换
- **包含**: 相机内参（仅摄像头）

### ego_pose（自车位姿）
- **描述**: 车辆在全局坐标系中的位置和朝向
- **特点**: 每一帧都不同（车在移动）
- **作用**: Ego Frame ↔ Global Frame 的转换

```
    传感器坐标系                    Ego 坐标系                    全局坐标系
    (Sensor Frame)                (Ego Frame)                  (Global Frame)
         │                            │                            │
         │   calibrated_sensor        │     ego_pose               │
         │   (固定不变)                │    (每帧变化)              │
         │◄──────────────────────────►│◄──────────────────────────►│
```

## 4. 从 LiDAR 点到图像像素的完整链路

将一个 LiDAR 点投影到某个摄像头图像上，需要经过以下步骤：

```
LiDAR 坐标系中的点 [x_L, y_L, z_L]
        │
        │ 步骤 1: LiDAR → Ego
        │ 使用: LiDAR 的 calibrated_sensor
        │ T_lidar_to_ego = [R_lidar | t_lidar]
        ▼
Ego 坐标系中的点 [x_E, y_E, z_E]
        │
        │ 步骤 2: Ego → Global
        │ 使用: LiDAR 时刻的 ego_pose
        │ T_ego_to_global = [R_ego | t_ego]
        ▼
Global 坐标系中的点 [x_G, y_G, z_G]
        │
        │ 步骤 3: Global → Ego (Camera 时刻)
        │ 使用: Camera 时刻的 ego_pose（取逆）
        │ T_global_to_ego = T_ego_to_global⁻¹
        ▼
Ego 坐标系中的点 (Camera 时刻) [x_E', y_E', z_E']
        │
        │ 步骤 4: Ego → Camera
        │ 使用: Camera 的 calibrated_sensor（取逆）
        │ T_ego_to_cam = T_cam_to_ego⁻¹
        ▼
Camera 坐标系中的点 [x_C, y_C, z_C]
        │
        │ 步骤 5: Camera 3D → Image 2D
        │ 使用: Camera 内参矩阵 K
        │ [u, v, 1] = (1/z_C) * K * [x_C, y_C, z_C]
        ▼
图像像素坐标 [u, v]
```

### 为什么步骤 2 和 3 要分开？

虽然在 nuScenes 的关键帧（sample）中，LiDAR 和 Camera 几乎是同时采集的，但它们的 ego_pose 可能略有不同。严格来说，从 LiDAR 坐标系到 Camera 坐标系需要经过 Global 坐标系做中转。

## 5. 变换矩阵

### 5.1 齐次坐标

为了用一个矩阵同时表示旋转和平移，我们使用齐次坐标：

```
3D 点: [x, y, z] → 齐次坐标: [x, y, z, 1]

4x4 变换矩阵:
┌              ┐   ┌   ┐     ┌    ┐
│ R₁₁ R₁₂ R₁₃ tx │   │ x │     │ x' │
│ R₂₁ R₂₂ R₂₃ ty │ × │ y │  =  │ y' │
│ R₃₁ R₃₂ R₃₃ tz │   │ z │     │ z' │
│ 0   0   0   1  │   │ 1 │     │ 1  │
└              ┘   └   ┘     └    ┘
```

### 5.2 四元数

nuScenes 使用四元数 `[w, x, y, z]` 表示旋转：
- 比欧拉角更稳定（没有万向锁问题）
- 比旋转矩阵更紧凑（4 个数 vs 9 个数）
- 可以方便地插值和组合

### 5.3 相机内参矩阵

```
K = ┌             ┐
    │ fx  0   cx  │   fx, fy: 焦距（像素单位）
    │ 0   fy  cy  │   cx, cy: 主点坐标（通常接近图像中心）
    │ 0   0   1   │
    └             ┘
```

投影公式:
```
u = fx * (X/Z) + cx
v = fy * (Y/Z) + cy
```

## 6. 新手最容易犯的坐标系错误

### 错误 1: 混淆 LiDAR 和 Camera 的轴方向
- LiDAR: X 前方, Y 左方, Z 上方
- Camera: X 右方, Y 下方, Z 前方
- **解决**: 画图标注每个坐标系的轴方向

### 错误 2: 忘记取逆
- `calibrated_sensor` 定义的是 **Sensor → Ego** 的变换
- 如果要从 Ego → Sensor，需要取逆矩阵
- **解决**: 明确每个变换的方向

### 错误 3: 忘记过滤相机后方的点
- 投影公式中除以 Z，如果 Z ≤ 0，点在相机后方
- 后方的点投影后坐标无意义
- **解决**: 投影前先过滤 Z > 0 的点

### 错误 4: 使用错误的 ego_pose
- LiDAR 和 Camera 各有自己的 ego_pose
- 虽然差异很小，但严格来说应该使用各自的
- **解决**: 通过 sample_data 获取对应的 ego_pose

### 错误 5: 内参矩阵用错
- nuScenes 的 camera_intrinsic 是 3x3 矩阵
- 有些框架使用 3x4 或 4x4 的投影矩阵
- **解决**: 检查矩阵维度是否匹配
