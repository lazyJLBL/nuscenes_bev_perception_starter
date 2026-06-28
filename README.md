# nuScenes BEV Perception Starter 🚗

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.8%2B-blue)
![PyTorch](https://img.shields.io/badge/PyTorch-2.0%2B-red)
![nuScenes](https://img.shields.io/badge/dataset-nuScenes%20mini-green)

这是一个面向**自动驾驶初学者**的零基础 BEV（鸟瞰图）多传感器感知入门项目。本项目带你一步步理解自动驾驶数据、掌握核心概念（坐标系、BEV），并跑通一个真实的 3D 检测算法。

> 🎯 **项目目标**: 不讲空洞理论，用 10 个脚本带你手把手撸代码，打通自动驾驶感知的任督二脉。

---

## 🌟 项目最终效果

完成本项目后，你将能够：
1. **理解 nuScenes**：掌握自动驾驶界最经典数据集的结构。
2. **掌握坐标系**：彻底搞懂 LiDAR、Camera、Ego、Global 四大坐标系的转换。
3. **点云投影**：将 3D LiDAR 点云精准投影到 2D 摄像头图像上。
4. **生成 BEV**：从点云生成高度图、密度图、强度图三通道 BEV 表示。
5. **3D 可视化**：在图像和 BEV 俯视图中画出精准的 3D 边界框（Bounding Boxes）。
6. **3D 检测**：跑通带 anchor、Focal Loss、SmoothL1、NMS 的 SimplePointPillars baseline。
7. **离线实验平台**：用 FastAPI + Vue 对比感知、决策、规划组合，并保存可复现实验记录。

---

## 📂 项目结构

```text
nuscenes_bev_perception_starter/
├── backend/                  # 🌐 FastAPI 后端：模块查询、实验运行、上传推理
│   ├── api/routes.py         # API 路由
│   ├── data/mock_data.py     # 兼容旧导入的模块配置入口
│   └── main.py               # 后端启动入口，默认端口 8010
├── configs/                  # ⚙️ 配置文件 (路径、数据集、模型)
├── docs/                     # 📚 核心概念学习文档 (初学者必读!)
│   ├── 01_nuscenes_data_structure.md  # 数据集结构详解
│   ├── 02_coordinate_systems.md       # 坐标系转换详解
│   ├── 03_bev_explanation.md          # BEV 鸟瞰图详解
│   ├── 04_3d_detection_baseline.md    # 3D 检测原理解析
│   └── 05_next_steps_to_planning.md   # 后续进阶路线图
├── frontend/                 # 🖥️ Vue 3 + Vite 离线实验沙盒
│   ├── src/views/            # 沙盒、实验记录、系统状态等页面
│   ├── src/components/       # 模型选择、上传推理、图片查看组件
│   └── vite.config.js        # 5174 前端开发端口与 API 代理
├── scripts/                  # 🚀 执行脚本 (按数字顺序运行)
│   ├── 00_check_environment.py        # 检查环境
│   ├── 01_check_nuscenes_data.py      # 检查数据集
│   ├── 02_visualize_samples.py        # 可视化样本
│   ├── 03_project_lidar_to_camera.py  # 点云投影到图像
│   ├── 04_visualize_3d_boxes.py       # 绘制 3D Boxes
│   ├── 05_generate_simple_bev.py      # 生成 BEV
│   ├── 06_prepare_detection_baseline.py # 准备 3D 检测
│   ├── 07_train_baseline.py           # 训练 PointPillars
│   ├── 08_inference_baseline.py       # 模型推理
│   ├── 09_visualize_predictions.py    # 可视化预测结果
│   ├── 10_check_detection_results.py  # 检查预测、指标、实验记录
│   └── export_model.py                # 导出自包含模型文件
├── src/                      # 🧠 核心源码
│   ├── bev/                  # BEV 生成逻辑
│   ├── dataset/              # 数据集加载逻辑
│   ├── detection/            # SimplePointPillars、anchor、loss、NMS、训练推理工具
│   ├── experiments/          # nuScenes-only 感知/决策/规划离线实验
│   ├── geometry/             # 坐标系转换、投影、3D Box逻辑
│   ├── utils/                # 工具类 (日志、路径、配置)
│   └── visualization/        # 绘图逻辑
├── tests/                    # ✅ API、实验组件、结果校验、基础几何/BEV 测试
├── package.json              # 根目录 npm 代理脚本
└── outputs/                  # 🖼️ 所有脚本的输出文件将保存在这里
```

---

## 🛠️ 环境配置

本项目支持 Python 3.8+ 和 PyTorch 2.0+。
如果要运行 Web 实验平台，还需要 Node.js 18+ 和 npm。

### 1. 克隆代码并进入目录
```bash
# 假设你已经下载了本项目代码
cd nuscenes_bev_perception_starter
```

### 2. 创建 Conda 环境 (推荐)
```bash
# 使用提供的 environment.yml 创建环境
conda env create -f environment.yml
conda activate nuscenes_bev
```

> **注意**: `environment.yml` 默认安装 CUDA 11.8 版本的 PyTorch。如果你的显卡不支持，请修改 `environment.yml` 或使用 Pip 安装。

### 3. 使用 Pip 安装 (备选)
```bash
pip install -r requirements.txt
```

### 4. 安装前端依赖（仅 Web 实验平台需要）
```bash
npm install --prefix frontend
```

---

## 💾 数据准备

本项目默认使用 **nuScenes v1.0-mini**（约 4GB），非常适合入门。

1. 访问 [nuScenes 官网](https://www.nuscenes.org/nuscenes#download) 注册并登录。
2. 下载 **v1.0-mini** 版本。
3. 解压到一个你喜欢的目录（例如 `D:/data/nuscenes` 或 `/home/user/data/nuscenes`）。
4. **修改配置文件**: 打开 `configs/paths.yaml`，将 `nuscenes_dataroot` 修改为你的实际解压路径。

```yaml
# configs/paths.yaml
nuscenes_dataroot: "你的解压路径"
nuscenes_version: "v1.0-mini"
```

---

## 🚀 运行指南 (新手推荐顺序)

请按照以下顺序运行脚本，每运行完一个，去 `outputs/` 目录看看生成的图片，并阅读对应的 `docs/` 文档！

### 阶段 1：环境与数据准备
```bash
# 检查你的环境是否安装正确
python scripts/00_check_environment.py

# 检查你的数据是否放对了位置
python scripts/01_check_nuscenes_data.py
# 📖 推荐阅读: docs/01_nuscenes_data_structure.md
```

### 阶段 2：感知基础可视化
```bash
# 生成 6 个摄像头的拼接图和 LiDAR 俯视图
python scripts/02_visualize_samples.py

# 将 LiDAR 3D 点云投影到 2D 图像上 (自动驾驶经典操作)
python scripts/03_project_lidar_to_camera.py
# 📖 推荐阅读: docs/02_coordinate_systems.md

# 在图像和鸟瞰图中画出 3D 边界框
python scripts/04_visualize_3d_boxes.py

# 将 3D 点云压缩成 2D 的多通道 BEV 图像
python scripts/05_generate_simple_bev.py
# 📖 推荐阅读: docs/03_bev_explanation.md

# 💡 提示：02-05 脚本支持通过 --sample-token 参数指定特定帧
# 例如: python scripts/02_visualize_samples.py --sample-token <token>
```

### 阶段 3：3D 检测 Baseline 流程 (自包含 PyTorch 闭环)
本项目内置了一个无需复杂 CUDA 编译的 SimplePointPillars 检测器，使用 anchor 分配、Focal Loss、SmoothL1 回归损失、方向分类损失和 BEV NMS，方便新人在 CPU 或任意显卡上验证全流程。

```bash
# 提取 nuScenes 训练和验证集 tokens
python scripts/06_prepare_detection_baseline.py --execute
# 📖 推荐阅读: docs/04_3d_detection_baseline.md

# 执行真实检测损失训练，并自动保存 latest/best/model_exported.pth
python scripts/07_train_baseline.py --execute --epochs 5 --batch-size 2

# 在验证集上执行前向推理，加载导出模型并调用官方工具评估指标 (mAP/NDS)
python scripts/08_inference_baseline.py --execute

# 可视化预测结果 (加载真实 JSON 预测，并在 BEV 上与 Ground Truth 对比)
python scripts/09_visualize_predictions.py

# 自动化检查整个训练与推理流程的生成产物
python scripts/10_check_detection_results.py
```

### 阶段 4：nuScenes-only 离线实验平台

当前项目也提供了一个轻量后端 + 前端，用于对比感知、决策、规划组合。它默认只使用 nuScenes，不引入 nuPlan/CARLA，适合 4070 / 32GB 机器做离线实验。

```bash
# 终端 1：启动后端 API，默认端口 8010
python -m backend.main

# 终端 2：启动前端，默认端口 5174
npm run dev
```

前端默认运行在 `http://127.0.0.1:5174`，并代理访问 `http://127.0.0.1:8010/api`；如需改后端地址，可设置 `VITE_BACKEND_URL`。打开首页后会直接进入 nuScenes 离线实验沙盒，旧的模块管理页面只保留在开发调试路由 `/dev/modules/preprocessing`。

常用 API：

```text
GET  /api/health
GET  /api/modules
GET  /api/experiments
GET  /api/experiments/latest
POST /api/run_experiment
POST /api/run_sandbox
POST /api/inference/{model_id}
```

离线实验会写入 `outputs/experiments/<run_id>/run_record.json`，并可在“实验记录”页面对比最近运行结果。PointPillars 模型上传推理会优先读取 `outputs/predictions/train_results/model_exported.pth`，没有导出模型时依次尝试 `best.pth` 和 `latest.pth`。

严格产物检查默认会拒绝 mAP/NDS 全 0 的检测结果：

```bash
python scripts/10_check_detection_results.py
```

如只想调试文件格式，可临时使用：

```bash
python scripts/10_check_detection_results.py --allow-zero-metrics
```

---

## ✅ 开发验证

```bash
# Python 单元测试
pytest -q

# 前端生产构建
npm --prefix frontend run build
```

---

## ❓ 常见问题 FAQ

**Q: 运行脚本报错 `FileNotFoundError: 配置文件不存在`？**
A: 请确保你在项目的**根目录**下运行脚本（即 `python scripts/xxx.py`），而不是进入 `scripts` 目录内运行。

**Q: 我没有 GPU 可以运行吗？**
A: `00` 到 `05` 的可视化脚本**完全不需要 GPU**，用 CPU 几秒钟就能跑完。`07` 和 `08` 可以用 CPU 跑通流程，但会明显更慢；推荐使用 CUDA。

**Q: `07_train_baseline.py` 报错 `CUDA out of memory` 怎么办？**
A: 你的显存不足。请把命令里的 `--batch-size` 调小，例如 `python scripts/07_train_baseline.py --execute --batch-size 1`；也可以在 `configs/model.yaml` 中调小 detection 配置。

**Q: Web 前端打不开后端数据怎么办？**
A: 先确认 `python -m backend.main` 正在运行，再访问 `http://127.0.0.1:8010/api/health`。如果后端端口不是 8010，启动前端时设置 `VITE_BACKEND_URL=http://127.0.0.1:<端口> npm run dev`。

**Q: 为什么生成的 BEV 图像全黑？**
A: 可能是坐标系转换错误，或者点云过滤范围不对。请检查你是否正确应用了 `calibrated_sensor` 和 `ego_pose` 变换。本项目提供的源码已经处理了这些细节，你可以仔细阅读 `src/geometry/transforms.py`。

---

## 🎓 毕业了，下一步学什么？

恭喜你完成了这个入门项目！你现在已经掌握了自动驾驶感知的基石。

为了从感知走向预测和规划（最终实现端到端自动驾驶），请仔细阅读：
👉 **[docs/05_next_steps_to_planning.md](docs/05_next_steps_to_planning.md)**

祝你在自动驾驶的道路上越走越远！🚗💨
