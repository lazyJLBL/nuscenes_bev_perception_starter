# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import desc, select

from backend.db import (
    AppUser,
    ModelCatalog,
    SimulationRun,
    SimulationRunArtifact,
    SimulationScenario,
    create_schema,
    is_database_configured,
    model_by_key,
    new_run_uid,
    row_to_dict,
    rows_to_dicts,
    session_scope,
)

router = APIRouter()


class ModelPayload(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    model_key: str = Field(..., min_length=2, max_length=96)
    name: str = Field(..., min_length=1, max_length=160)
    subsystem: str = Field(..., pattern="^(preprocessing|perception|decision|planning)$")
    category: str = "general"
    framework: Optional[str] = None
    version: str = "v1"
    status: str = Field("active", pattern="^(active|draft|disabled|needs_checkpoint|unavailable)$")
    description: str = ""
    artifact_uri: Optional[str] = None
    image_uri: Optional[str] = None
    config_json: Dict[str, Any] = Field(default_factory=dict)
    metrics_json: Dict[str, Any] = Field(default_factory=dict)
    created_by_id: Optional[int] = None


class ModelPatchPayload(BaseModel):
    name: Optional[str] = None
    subsystem: Optional[str] = Field(None, pattern="^(preprocessing|perception|decision|planning)$")
    category: Optional[str] = None
    framework: Optional[str] = None
    version: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(active|draft|disabled|needs_checkpoint|unavailable)$")
    description: Optional[str] = None
    artifact_uri: Optional[str] = None
    image_uri: Optional[str] = None
    config_json: Optional[Dict[str, Any]] = None
    metrics_json: Optional[Dict[str, Any]] = None


class ScenarioPayload(BaseModel):
    scenario_key: str = Field(..., min_length=2, max_length=96)
    name: str = Field(..., min_length=1, max_length=160)
    description: str = ""
    dataset_source: str = Field("carla", pattern="^(nuscenes|carla|mixed)$")
    carla_town: Optional[str] = None
    status: str = Field("active", pattern="^(active|draft|disabled)$")
    default_config_json: Dict[str, Any] = Field(default_factory=dict)
    created_by_id: Optional[int] = None


class ScenarioPatchPayload(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    dataset_source: Optional[str] = Field(None, pattern="^(nuscenes|carla|mixed)$")
    carla_town: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(active|draft|disabled)$")
    default_config_json: Optional[Dict[str, Any]] = None


class ClientRunPayload(BaseModel):
    user_id: int = 2
    scenario_id: Optional[int] = None
    preprocessing_model_key: str = "lidar_topdown"
    perception_model_key: str = "pointpillars"
    decision_model_key: str = "fsm_decision"
    planning_model_key: str = "mpc_smoothing"
    max_samples: int = Field(8, ge=1, le=200)
    request_config_json: Dict[str, Any] = Field(default_factory=dict)


def _db_required() -> None:
    if not is_database_configured():
        raise HTTPException(
            status_code=503,
            detail="DATABASE_URL is not configured. Set it to mysql+pymysql://user:password@host:3306/dbname?charset=utf8mb4",
        )


def _model_options(session) -> Dict[str, list[Dict[str, Any]]]:
    rows = session.scalars(select(ModelCatalog).order_by(ModelCatalog.subsystem, ModelCatalog.name)).all()
    grouped: Dict[str, list[Dict[str, Any]]] = {
        "preprocessing": [],
        "perception": [],
        "decision": [],
        "planning": [],
    }
    for row in rows:
        grouped.setdefault(row.subsystem, []).append(row_to_dict(row))
    return grouped


def _run_to_dict(session, run: SimulationRun) -> Dict[str, Any]:
    data = row_to_dict(run)
    data["scenario"] = row_to_dict(run.scenario) if run.scenario else None
    data["user"] = {
        "id": run.user.id,
        "username": run.user.username,
        "display_name": run.user.display_name,
        "role": run.user.role,
    }
    data["artifacts"] = rows_to_dicts(run.artifacts)
    data["models"] = {}
    for key, model_id in {
        "preprocessing": run.preprocessing_model_id,
        "perception": run.perception_model_id,
        "decision": run.decision_model_id,
        "planning": run.planning_model_id,
    }.items():
        data["models"][key] = row_to_dict(session.get(ModelCatalog, model_id)) if model_id else None
    return data


@router.get("/db/status")
async def db_status():
    configured = is_database_configured()
    if not configured:
        return {"success": True, "configured": False, "connected": False}
    try:
        with session_scope() as session:
            users = session.scalar(select(AppUser).limit(1))
        return {"success": True, "configured": True, "connected": True, "has_seed_data": users is not None}
    except Exception as exc:
        return {"success": True, "configured": True, "connected": False, "error": str(exc)}


@router.post("/admin/db/init")
async def init_database():
    _db_required()
    create_schema(seed=True)
    return {"success": True, "message": "MySQL schema is ready and seed data has been inserted."}


@router.get("/admin/models")
async def admin_models(subsystem: Optional[str] = Query(None)):
    _db_required()
    with session_scope() as session:
        stmt = select(ModelCatalog).order_by(ModelCatalog.subsystem, ModelCatalog.name)
        if subsystem:
            stmt = stmt.where(ModelCatalog.subsystem == subsystem)
        return {"success": True, "models": rows_to_dicts(session.scalars(stmt).all())}


@router.post("/admin/models")
async def create_model(payload: ModelPayload):
    _db_required()
    with session_scope() as session:
        existing = model_by_key(session, payload.model_key)
        if existing:
            raise HTTPException(status_code=409, detail=f"model_key already exists: {payload.model_key}")
        model = ModelCatalog(**payload.model_dump())
        session.add(model)
        session.flush()
        return {"success": True, "model": row_to_dict(model)}


@router.patch("/admin/models/{model_id}")
async def update_model(model_id: int, payload: ModelPatchPayload):
    _db_required()
    with session_scope() as session:
        model = session.get(ModelCatalog, model_id)
        if model is None:
            raise HTTPException(status_code=404, detail="model not found")
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(model, key, value)
        session.flush()
        return {"success": True, "model": row_to_dict(model)}


@router.get("/admin/scenarios")
async def admin_scenarios(status: Optional[str] = Query(None)):
    _db_required()
    with session_scope() as session:
        stmt = select(SimulationScenario).order_by(desc(SimulationScenario.updated_at))
        if status:
            stmt = stmt.where(SimulationScenario.status == status)
        return {"success": True, "scenarios": rows_to_dicts(session.scalars(stmt).all())}


@router.post("/admin/scenarios")
async def create_scenario(payload: ScenarioPayload):
    _db_required()
    with session_scope() as session:
        existing = session.scalar(select(SimulationScenario).where(SimulationScenario.scenario_key == payload.scenario_key))
        if existing:
            raise HTTPException(status_code=409, detail=f"scenario_key already exists: {payload.scenario_key}")
        scenario = SimulationScenario(**payload.model_dump())
        session.add(scenario)
        session.flush()
        return {"success": True, "scenario": row_to_dict(scenario)}


@router.patch("/admin/scenarios/{scenario_id}")
async def update_scenario(scenario_id: int, payload: ScenarioPatchPayload):
    _db_required()
    with session_scope() as session:
        scenario = session.get(SimulationScenario, scenario_id)
        if scenario is None:
            raise HTTPException(status_code=404, detail="scenario not found")
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(scenario, key, value)
        session.flush()
        return {"success": True, "scenario": row_to_dict(scenario)}


@router.get("/client/bootstrap")
async def client_bootstrap():
    _db_required()
    with session_scope() as session:
        scenarios = session.scalars(
            select(SimulationScenario)
            .where(SimulationScenario.status == "active")
            .order_by(SimulationScenario.name)
        ).all()
        return {
            "success": True,
            "scenarios": rows_to_dicts(scenarios),
            "modelsBySubsystem": _model_options(session),
        }


@router.get("/client/runs")
async def client_runs(user_id: int = 2, limit: int = 20):
    _db_required()
    safe_limit = max(1, min(int(limit or 20), 100))
    with session_scope() as session:
        rows = session.scalars(
            select(SimulationRun)
            .where(SimulationRun.user_id == user_id)
            .order_by(desc(SimulationRun.created_at))
            .limit(safe_limit)
        ).all()
        return {"success": True, "count": len(rows), "runs": [_run_to_dict(session, row) for row in rows]}


@router.get("/client/runs/{run_id}")
async def client_run_detail(run_id: int, user_id: int = 2):
    _db_required()
    with session_scope() as session:
        run = session.get(SimulationRun, run_id)
        if run is None or run.user_id != user_id:
            raise HTTPException(status_code=404, detail="run not found")
        return {"success": True, "run": _run_to_dict(session, run)}


@router.post("/client/runs")
async def create_client_run(payload: ClientRunPayload):
    _db_required()
    with session_scope() as session:
        user = session.get(AppUser, payload.user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="user not found")
        scenario = session.get(SimulationScenario, payload.scenario_id) if payload.scenario_id else None
        if payload.scenario_id and scenario is None:
            raise HTTPException(status_code=404, detail="scenario not found")

        run = SimulationRun(
            run_uid=new_run_uid("client"),
            user_id=user.id,
            scenario_id=scenario.id if scenario else None,
            status="queued",
            preprocessing_model_id=_optional_model_id(session, payload.preprocessing_model_key),
            perception_model_id=_optional_model_id(session, payload.perception_model_key),
            decision_model_id=_optional_model_id(session, payload.decision_model_key),
            planning_model_id=_optional_model_id(session, payload.planning_model_key),
            max_samples=payload.max_samples,
            request_config_json={
                **payload.request_config_json,
                "preprocessing_model": payload.preprocessing_model_key,
                "perception_model": payload.perception_model_key,
                "decision_model": payload.decision_model_key,
                "planning_model": payload.planning_model_key,
                "carla_integration": "queued_manual",
            },
            result_summary="Queued. CARLA execution is available through /api/carla/run and the client sandbox.",
        )
        session.add(run)
        session.flush()
        session.add(SimulationRunArtifact(
            run_id=run.id,
            artifact_type="config",
            title="Requested simulation config",
            uri=f"mysql://simulation_runs/{run.id}/request_config_json",
            mime_type="application/json",
        ))
        session.flush()
        return {"success": True, "run": _run_to_dict(session, run)}


def _optional_model_id(session, model_key: str) -> Optional[int]:
    model = model_by_key(session, model_key)
    if model is None:
        raise HTTPException(status_code=404, detail=f"model not found: {model_key}")
    return model.id
