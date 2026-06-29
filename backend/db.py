from __future__ import annotations

import os
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, Optional

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    create_engine,
    select,
)
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker
from sqlalchemy.sql import func

from src.experiments.schemas import RunRecord
from src.experiments.registry import get_model_registry


def database_url() -> str:
    return os.environ.get("DATABASE_URL") or os.environ.get("MYSQL_URL") or ""


def is_database_configured() -> bool:
    return bool(database_url())


class Base(DeclarativeBase):
    pass


class AppUser(Base):
    __tablename__ = "app_users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255), unique=True)
    role: Mapped[str] = mapped_column(String(24), nullable=False, default="client")
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="active")
    password_hash: Mapped[Optional[str]] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    created_models: Mapped[list["ModelCatalog"]] = relationship(back_populates="creator")
    created_scenarios: Mapped[list["SimulationScenario"]] = relationship(back_populates="creator")
    runs: Mapped[list["SimulationRun"]] = relationship(back_populates="user")


class ModelCatalog(Base):
    __tablename__ = "model_catalog"
    __table_args__ = (
        Index("ix_model_catalog_subsystem_status", "subsystem", "status"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    model_key: Mapped[str] = mapped_column(String(96), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    subsystem: Mapped[str] = mapped_column(String(32), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False, default="general")
    framework: Mapped[Optional[str]] = mapped_column(String(64))
    version: Mapped[str] = mapped_column(String(48), nullable=False, default="v1")
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="active")
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    artifact_uri: Mapped[Optional[str]] = mapped_column(String(512))
    image_uri: Mapped[Optional[str]] = mapped_column(String(512))
    config_json: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    metrics_json: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey("app_users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    creator: Mapped[Optional[AppUser]] = relationship(back_populates="created_models")


class SimulationScenario(Base):
    __tablename__ = "simulation_scenarios"
    __table_args__ = (
        Index("ix_simulation_scenarios_source_status", "dataset_source", "status"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    scenario_key: Mapped[str] = mapped_column(String(96), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    dataset_source: Mapped[str] = mapped_column(String(32), nullable=False, default="nuscenes")
    unity_scene_name: Mapped[Optional[str]] = mapped_column(String(160))
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="active")
    default_config_json: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey("app_users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    creator: Mapped[Optional[AppUser]] = relationship(back_populates="created_scenarios")
    runs: Mapped[list["SimulationRun"]] = relationship(back_populates="scenario")


class SimulationRun(Base):
    __tablename__ = "simulation_runs"
    __table_args__ = (
        Index("ix_simulation_runs_user_created", "user_id", "created_at"),
        Index("ix_simulation_runs_status_created", "status", "created_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    run_uid: Mapped[str] = mapped_column(String(160), unique=True, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("app_users.id", ondelete="RESTRICT"), nullable=False)
    scenario_id: Mapped[Optional[int]] = mapped_column(ForeignKey("simulation_scenarios.id", ondelete="SET NULL"))
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="queued")
    preprocessing_model_id: Mapped[Optional[int]] = mapped_column(ForeignKey("model_catalog.id", ondelete="SET NULL"))
    perception_model_id: Mapped[Optional[int]] = mapped_column(ForeignKey("model_catalog.id", ondelete="SET NULL"))
    decision_model_id: Mapped[Optional[int]] = mapped_column(ForeignKey("model_catalog.id", ondelete="SET NULL"))
    planning_model_id: Mapped[Optional[int]] = mapped_column(ForeignKey("model_catalog.id", ondelete="SET NULL"))
    max_samples: Mapped[int] = mapped_column(nullable=False, default=8)
    request_config_json: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    metrics_json: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    artifacts_json: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    run_record_path: Mapped[Optional[str]] = mapped_column(String(512))
    result_summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    user: Mapped[AppUser] = relationship(back_populates="runs")
    scenario: Mapped[Optional[SimulationScenario]] = relationship(back_populates="runs")
    artifacts: Mapped[list["SimulationRunArtifact"]] = relationship(back_populates="run", cascade="all, delete-orphan")


class SimulationRunArtifact(Base):
    __tablename__ = "simulation_run_artifacts"
    __table_args__ = (
        Index("ix_simulation_run_artifacts_run_type", "run_id", "artifact_type"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("simulation_runs.id", ondelete="CASCADE"), nullable=False)
    artifact_type: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    uri: Mapped[str] = mapped_column(String(512), nullable=False)
    mime_type: Mapped[Optional[str]] = mapped_column(String(96))
    metadata_json: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    run: Mapped[SimulationRun] = relationship(back_populates="artifacts")


_engine = None
_SessionLocal = None


def get_engine():
    global _engine
    if _engine is None:
        url = database_url()
        if not url:
            raise RuntimeError("DATABASE_URL is not configured")
        _engine = create_engine(url, pool_pre_ping=True, pool_recycle=1800, future=True)
    return _engine


def get_session_factory():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine(), autoflush=False, autocommit=False, future=True)
    return _SessionLocal


@contextmanager
def session_scope():
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def create_schema(seed: bool = True) -> None:
    Base.metadata.create_all(bind=get_engine())
    if seed:
        with session_scope() as session:
            seed_initial_data(session)


def seed_initial_data(session: Session) -> None:
    admin = _get_or_create_user(session, "admin", "管理员", "admin")
    _get_or_create_user(session, "client_demo", "演示客户", "client")
    _seed_registry_models(session, admin.id)
    _get_or_create_scenario(
        session,
        scenario_key="nuscenes_mini_offline",
        name="nuScenes mini 离线仿真",
        dataset_source="nuscenes",
        description="使用本地 nuScenes mini 数据和现有感知/决策/规划链路生成一次离线仿真结果。",
        created_by_id=admin.id,
        default_config_json={"split": "mini_val", "max_samples": 8},
    )
    _get_or_create_scenario(
        session,
        scenario_key="unity_reserved_template",
        name="Unity 仿真占位模板",
        dataset_source="unity",
        description="为后续 Unity 场景接入保留的试验模板；当前只维护配置，不触发 Unity。",
        created_by_id=admin.id,
        unity_scene_name="ReservedUnityScene",
        status="draft",
        default_config_json={"weather": "clear", "traffic_density": "medium"},
    )


def _get_or_create_user(session: Session, username: str, display_name: str, role: str) -> AppUser:
    user = session.scalar(select(AppUser).where(AppUser.username == username))
    if user:
        return user
    user = AppUser(username=username, display_name=display_name, role=role)
    session.add(user)
    session.flush()
    return user


def _get_or_create_scenario(session: Session, **values: Any) -> SimulationScenario:
    scenario = session.scalar(select(SimulationScenario).where(SimulationScenario.scenario_key == values["scenario_key"]))
    if scenario:
        return scenario
    scenario = SimulationScenario(**values)
    session.add(scenario)
    session.flush()
    return scenario


def _seed_registry_models(session: Session, created_by_id: int) -> None:
    registry = get_model_registry()
    for subsystem, models in registry.items():
        for model_key, model in models.items():
            existing = session.scalar(select(ModelCatalog).where(ModelCatalog.model_key == model_key))
            if existing:
                continue
            session.add(ModelCatalog(
                model_key=model_key,
                name=model.get("name", model_key),
                subsystem=subsystem,
                category="3d_detection" if subsystem == "perception" else subsystem,
                framework="pytorch" if model_key == "pointpillars" else "python",
                version="v1",
                status=model.get("status", "active"),
                description=model.get("desc", ""),
                image_uri=model.get("outputImage"),
                metrics_json=model.get("metrics") or {},
                config_json={"registry_source": "src.experiments.registry"},
                created_by_id=created_by_id,
            ))


def model_by_key(session: Session, model_key: Optional[str]) -> Optional[ModelCatalog]:
    if not model_key:
        return None
    return session.scalar(select(ModelCatalog).where(ModelCatalog.model_key == model_key))


def try_persist_run_record(record: RunRecord, user_id: int = 2, scenario_id: Optional[int] = None) -> Optional[int]:
    if not is_database_configured():
        return None
    try:
        with session_scope() as session:
            user = session.get(AppUser, user_id) or session.scalar(select(AppUser).where(AppUser.username == "client_demo"))
            if user is None:
                user = _get_or_create_user(session, "client_demo", "演示客户", "client")
            scenario = session.get(SimulationScenario, scenario_id) if scenario_id else None
            if scenario is None:
                scenario = session.scalar(select(SimulationScenario).where(SimulationScenario.scenario_key == "nuscenes_mini_offline"))

            existing = session.scalar(select(SimulationRun).where(SimulationRun.run_uid == record.run_id))
            if existing:
                return existing.id

            spec = record.spec
            reports = {key: value.to_dict() for key, value in record.reports.items()}
            metrics = {
                subsystem: report.get("metrics", {})
                for subsystem, report in reports.items()
            }
            artifacts = {
                subsystem: report.get("artifacts", {})
                for subsystem, report in reports.items()
                if report.get("artifacts")
            }
            run = SimulationRun(
                run_uid=record.run_id,
                user_id=user.id,
                scenario_id=scenario.id if scenario else None,
                status="succeeded" if record.status == "ok" else "needs_attention",
                preprocessing_model_id=_model_id(model_by_key(session, spec.preprocessing_model)),
                perception_model_id=_model_id(model_by_key(session, spec.perception_model)),
                decision_model_id=_model_id(model_by_key(session, spec.decision_model)),
                planning_model_id=_model_id(model_by_key(session, spec.planning_model)),
                max_samples=spec.max_samples,
                request_config_json=spec.to_dict(),
                metrics_json=metrics,
                artifacts_json=artifacts,
                run_record_path=os.path.join(record.output_dir or "", "run_record.json") if record.output_dir else None,
                result_summary=_summary_from_record(record),
                started_at=datetime.now(timezone.utc),
                finished_at=datetime.now(timezone.utc),
            )
            session.add(run)
            session.flush()
            if run.run_record_path:
                session.add(SimulationRunArtifact(
                    run_id=run.id,
                    artifact_type="record",
                    title="Run record JSON",
                    uri=run.run_record_path,
                    mime_type="application/json",
                ))
            return run.id
    except Exception:
        return None


def _model_id(model: Optional[ModelCatalog]) -> Optional[int]:
    return model.id if model else None


def _summary_from_record(record: RunRecord) -> str:
    planning = record.reports.get("planning")
    perception = record.reports.get("perception")
    planning_metrics = planning.metrics if planning else {}
    perception_metrics = perception.metrics if perception else {}
    collision = planning_metrics.get("collision_rate")
    nd_score = perception_metrics.get("nd_score")
    parts = [f"status={record.status}"]
    if nd_score is not None:
        parts.append(f"NDS={float(nd_score):.3f}")
    if collision is not None:
        parts.append(f"collision={float(collision) * 100:.1f}%")
    return ", ".join(parts)


def new_run_uid(prefix: str = "manual") -> str:
    return f"{prefix}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}_{uuid.uuid4().hex[:8]}"


def rows_to_dicts(rows: Iterable[Any]) -> list[Dict[str, Any]]:
    return [row_to_dict(row) for row in rows]


def row_to_dict(row: Any) -> Dict[str, Any]:
    data = {
        column.name: getattr(row, column.name)
        for column in row.__table__.columns
    }
    for key, value in list(data.items()):
        if isinstance(value, datetime):
            data[key] = value.isoformat()
    return data
