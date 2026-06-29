# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from backend.carla_service import (
    CarlaUnavailable,
    available_maps,
    carla_status,
    run_carla_simulation,
    start_carla,
    stop_carla,
)

router = APIRouter(prefix="/carla")


class CarlaStartRequest(BaseModel):
    windowed: bool = True
    res_x: int = Field(1280, ge=640, le=3840)
    res_y: int = Field(720, ge=480, le=2160)


class CarlaRunRequest(BaseModel):
    user_id: int = 2
    scenario_id: Optional[int] = None
    town: str = "Town03"
    duration_seconds: float = Field(10.0, ge=1.0, le=300.0)
    weather: str = "ClearNoon"
    traffic_vehicles: int = Field(10, ge=0, le=200)
    traffic_walkers: int = Field(0, ge=0, le=100)
    ego_vehicle: str = "vehicle.tesla.model3"
    spawn_point_index: int = Field(0, ge=0)
    synchronous_mode: bool = False


def _error(exc: Exception) -> Dict[str, Any]:
    return {"success": False, "error": str(exc)}


@router.get("/status")
async def get_carla_status():
    return carla_status()


@router.post("/start")
async def post_carla_start(payload: CarlaStartRequest):
    try:
        return start_carla(windowed=payload.windowed, res_x=payload.res_x, res_y=payload.res_y)
    except CarlaUnavailable as exc:
        return _error(exc)


@router.post("/stop")
async def post_carla_stop():
    return stop_carla()


@router.get("/maps")
async def get_carla_maps():
    return available_maps()


@router.post("/run")
async def post_carla_run(payload: CarlaRunRequest):
    try:
        return run_carla_simulation(payload.model_dump())
    except Exception as exc:
        return _error(exc)
