# MySQL 数据库设计

数据库名：`nuscenes_bev_platform`

设计目标：支撑一个客户端和一个管理员端。管理员维护模型与 CARLA 仿真试验模板；客户运行或查看自己的仿真试验和最终结果。

## 关系总览

```text
app_users 1 ── n model_catalog
app_users 1 ── n simulation_scenarios
app_users 1 ── n simulation_runs

simulation_scenarios 1 ── n simulation_runs
simulation_runs 1 ── n simulation_run_artifacts

model_catalog 1 ── n simulation_runs.preprocessing_model_id
model_catalog 1 ── n simulation_runs.perception_model_id
model_catalog 1 ── n simulation_runs.decision_model_id
model_catalog 1 ── n simulation_runs.planning_model_id
```

## app_users

用户表。当前先支持角色区分，不做完整登录系统。

| 字段 | 说明 |
|---|---|
| `id` | 主键 |
| `username` | 登录名或系统内唯一用户标识 |
| `display_name` | 页面显示名 |
| `email` | 邮箱，可为空 |
| `role` | `admin` 或 `client` |
| `status` | `active`、`disabled` 等 |
| `password_hash` | 后续接登录时存密码哈希，不存明文 |
| `created_at` / `updated_at` | 创建和更新时间 |

## model_catalog

模型目录。管理员在这里增加、修改模型。模型文件、checkpoint、服务地址不直接塞进数据库，只存 URI。

| 字段 | 说明 |
|---|---|
| `id` | 主键 |
| `model_key` | 程序使用的唯一模型标识，例如 `pointpillars` |
| `name` | 展示名称 |
| `subsystem` | `preprocessing`、`perception`、`decision`、`planning` |
| `category` | 细分类型，例如 `3d_detection` |
| `framework` | `pytorch`、`python`、`carla-adapter` 等 |
| `version` | 模型版本 |
| `status` | `active`、`draft`、`disabled`、`needs_checkpoint`、`unavailable` |
| `description` | 管理员说明 |
| `artifact_uri` | checkpoint、本地文件或模型服务地址 |
| `image_uri` | 预览图地址 |
| `config_json` | 模型运行配置 |
| `metrics_json` | 模型默认指标或最近指标 |
| `created_by_id` | 创建人 |
| `created_at` / `updated_at` | 创建和更新时间 |

索引：`subsystem + status`，用于按阶段筛选可用模型。

## simulation_scenarios

仿真试验模板。管理员在这里维护 nuScenes 或 CARLA 场景。

| 字段 | 说明 |
|---|---|
| `id` | 主键 |
| `scenario_key` | 唯一试验标识 |
| `name` | 试验名称 |
| `description` | 试验说明 |
| `dataset_source` | `nuscenes`、`carla`、`mixed` |
| `carla_town` | CARLA Town 名称，例如 `Town03` |
| `status` | `active`、`draft`、`disabled` |
| `default_config_json` | 默认天气、仿真时长、车流、行人、出生点等配置 |
| `created_by_id` | 创建人 |
| `created_at` / `updated_at` | 创建和更新时间 |

索引：`dataset_source + status`，用于客户端只展示可用场景。

## simulation_runs

客户的一次仿真运行记录，也是客户端“我的仿真试验与结果”的主表。

| 字段 | 说明 |
|---|---|
| `id` | 主键 |
| `run_uid` | 与文件系统 `run_id` 对齐的唯一运行号 |
| `user_id` | 归属客户 |
| `scenario_id` | 使用的仿真试验模板 |
| `status` | `queued`、`running`、`succeeded`、`failed`、`needs_attention` |
| `preprocessing_model_id` | 使用的预处理模型 |
| `perception_model_id` | 使用的感知模型 |
| `decision_model_id` | 使用的决策模型 |
| `planning_model_id` | 使用的规划模型 |
| `max_samples` | 本次运行样本数量 |
| `request_config_json` | 本次请求的完整配置 |
| `metrics_json` | 最终指标，按 `perception`、`decision`、`planning` 分组 |
| `artifacts_json` | 产物索引，例如预测 JSON、指标 JSON |
| `run_record_path` | 本地 `run_record.json` 路径 |
| `result_summary` | 页面展示的简短结果摘要 |
| `error_message` | 失败原因 |
| `started_at` / `finished_at` | 执行起止时间 |
| `created_at` / `updated_at` | 创建和更新时间 |

索引：`user_id + created_at` 支持客户查看自己的最近记录；`status + created_at` 支持管理员排查任务。

## simulation_run_artifacts

运行产物表。用于保存结果文件、图片、日志、JSON 的地址，不存大文件本体。

| 字段 | 说明 |
|---|---|
| `id` | 主键 |
| `run_id` | 所属运行 |
| `artifact_type` | `record`、`image`、`metrics`、`log`、`config` |
| `title` | 产物标题 |
| `uri` | 文件路径、静态 URL 或对象存储地址 |
| `mime_type` | MIME 类型 |
| `metadata_json` | 尺寸、采样点、说明等附加信息 |
| `created_at` | 创建时间 |

索引：`run_id + artifact_type`，用于快速列出某次运行的结果产物。

## 为什么不把图片和模型存进 MySQL

模型权重、点云、图片、视频都属于大文件。MySQL 只保存它们的位置和元数据，文件本体继续放在 `outputs/`、`backend/static/` 或后续对象存储里。这样数据库不会膨胀，备份和迁移也更稳。
