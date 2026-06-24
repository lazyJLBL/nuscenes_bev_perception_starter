# nuScenes 数据结构详解

> 本文面向自动驾驶初学者，详细介绍 nuScenes 数据集的组织方式。

## 1. nuScenes 是什么

nuScenes 是由 Motional（前 nuTonomy）发布的大规模自动驾驶数据集，包含：
- **1000 个场景** (scenes)，每个约 20 秒
- **6 个环视摄像头** 图像
- **1 个 LiDAR** 点云（32 线 Velodyne）
- **5 个 Radar** 点云
- **完整的 3D 标注** (23 个类别)
- **IMU 和 GPS 数据**

nuScenes mini 是完整数据集的子集，包含 10 个场景，约 4GB。

## 2. 数据集目录结构

```
nuscenes/
├── maps/                    # 地图数据
├── samples/                 # 关键帧传感器数据
│   ├── CAM_FRONT/          # 前方摄像头图像
│   ├── CAM_FRONT_LEFT/     # 左前方摄像头图像
│   ├── CAM_FRONT_RIGHT/    # 右前方摄像头图像
│   ├── CAM_BACK/           # 后方摄像头图像
│   ├── CAM_BACK_LEFT/      # 左后方摄像头图像
│   ├── CAM_BACK_RIGHT/     # 右后方摄像头图像
│   ├── LIDAR_TOP/          # 顶部 LiDAR 点云
│   ├── RADAR_FRONT/        # 前方 Radar
│   ├── RADAR_FRONT_LEFT/   # 左前方 Radar
│   ├── RADAR_FRONT_RIGHT/  # 右前方 Radar
│   ├── RADAR_BACK_LEFT/    # 左后方 Radar
│   └── RADAR_BACK_RIGHT/   # 右后方 Radar
├── sweeps/                  # 非关键帧传感器数据（更高频率）
│   └── (同 samples 的子目录结构)
└── v1.0-mini/              # 元数据 JSON 文件
    ├── attribute.json
    ├── calibrated_sensor.json
    ├── category.json
    ├── ego_pose.json
    ├── instance.json
    ├── log.json
    ├── map.json
    ├── sample.json
    ├── sample_annotation.json
    ├── sample_data.json
    ├── scene.json
    ├── sensor.json
    └── visibility.json
```

## 3. 核心表（JSON 文件）

nuScenes 的数据用关系型表来组织，通过 `token`（唯一 ID）互相关联。

### 3.1 scene（场景）
一段 20 秒左右的连续驾驶记录。

| 字段 | 说明 |
|------|------|
| token | 唯一标识符 |
| name | 场景名称，如 "scene-0001" |
| description | 场景描述 |
| first_sample_token | 第一个关键帧的 token |
| last_sample_token | 最后一个关键帧的 token |
| nbr_samples | 关键帧数量 |

### 3.2 sample（关键帧）
每个场景中每 0.5 秒采样一次的关键帧。

| 字段 | 说明 |
|------|------|
| token | 唯一标识符 |
| timestamp | 时间戳 |
| scene_token | 所属场景 |
| data | {传感器名: sample_data_token} 字典 |
| anns | [sample_annotation_token] 标注列表 |

### 3.3 sample_data（传感器数据）
某个传感器在某个时刻的具体数据文件。

| 字段 | 说明 |
|------|------|
| token | 唯一标识符 |
| sample_token | 所属关键帧 |
| ego_pose_token | 对应的车辆位姿 |
| calibrated_sensor_token | 对应的传感器标定 |
| filename | 数据文件路径 |
| is_key_frame | 是否为关键帧数据 |

### 3.4 ego_pose（自车位姿）
车辆在全局坐标系中的位置和朝向。

| 字段 | 说明 |
|------|------|
| token | 唯一标识符 |
| translation | [x, y, z] 在全局坐标系中的位置 |
| rotation | [w, x, y, z] 四元数旋转 |
| timestamp | 时间戳 |

### 3.5 calibrated_sensor（传感器标定）
传感器在车辆上的安装位置和朝向。

| 字段 | 说明 |
|------|------|
| token | 唯一标识符 |
| sensor_token | 所属传感器 |
| translation | [x, y, z] 相对于车辆中心的位置 |
| rotation | [w, x, y, z] 相对于车辆的旋转 |
| camera_intrinsic | 3x3 相机内参矩阵（仅摄像头有） |

### 3.6 sample_annotation（3D 标注框）
一个物体在某帧中的 3D 标注。

| 字段 | 说明 |
|------|------|
| token | 唯一标识符 |
| sample_token | 所属关键帧 |
| instance_token | 物体实例（同一物体跨帧共享） |
| category_name | 类别名，如 "vehicle.car" |
| translation | [x, y, z] 中心点（全局坐标系） |
| size | [width, length, height] 尺寸 |
| rotation | [w, x, y, z] 四元数旋转 |
| num_lidar_pts | box 内的 LiDAR 点数 |

## 4. 表之间的关系

```
scene
  └── sample (关键帧)
        ├── sample_data (每个传感器的数据)
        │     ├── ego_pose (车辆位姿)
        │     └── calibrated_sensor (传感器标定)
        │           └── sensor (传感器信息)
        └── sample_annotation (3D 标注)
              └── instance (物体实例)
                    └── category (物体类别)
```

## 5. LiDAR 点云数据格式

nuScenes 的 LiDAR 点云保存为 `.pcd.bin` 二进制文件：
- 每个点包含 5 个 `float32` 值：`x, y, z, intensity, ring_index`
- `x, y, z`: 在 LiDAR 坐标系下的三维坐标（米）
- `intensity`: 反射强度（0~255）
- `ring_index`: 激光线束编号（0~31）

读取方式：
```python
import numpy as np
points = np.fromfile('path/to/file.pcd.bin', dtype=np.float32).reshape(-1, 5)
```

## 6. 摄像头图像数据格式

- 格式: JPEG
- 分辨率: 1600 x 900 像素
- 6 个摄像头覆盖 360° 环视
