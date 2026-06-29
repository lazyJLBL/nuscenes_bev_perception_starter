from __future__ import annotations

import glob
import json
import os
import queue
import random
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from PIL import Image

from backend.db import (
    AppUser,
    SimulationRun,
    SimulationRunArtifact,
    SimulationScenario,
    is_database_configured,
    session_scope,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CARLA_HOME = r"D:\CARLA\CARLA_0.9.15"
DEFAULT_MAPS = ["Town01", "Town02", "Town03", "Town04", "Town05", "Town10HD", "Town13", "Town15"]

_carla_process: Optional[subprocess.Popen] = None


@dataclass
class CarlaConfig:
    home: Path
    host: str
    port: int
    timeout_seconds: float = 10.0


class CarlaUnavailable(RuntimeError):
    pass


def get_config() -> CarlaConfig:
    return CarlaConfig(
        home=Path(os.environ.get("CARLA_HOME", DEFAULT_CARLA_HOME)),
        host=os.environ.get("CARLA_HOST", "127.0.0.1"),
        port=int(os.environ.get("CARLA_PORT", "2000")),
    )


def find_carla_executable(home: Optional[Path] = None) -> Optional[Path]:
    root = home or get_config().home
    direct = root / "CarlaUE4.exe"
    if direct.exists():
        return direct
    matches = list(root.rglob("CarlaUE4.exe")) if root.exists() else []
    return matches[0] if matches else None


def find_python_api(home: Optional[Path] = None) -> Optional[str]:
    root = home or get_config().home
    patterns = [
        str(root / "PythonAPI" / "carla" / "dist" / "carla-*.egg"),
        str(root / "PythonAPI" / "carla" / "dist" / "carla-*.whl"),
        str(root / "WindowsNoEditor" / "PythonAPI" / "carla" / "dist" / "carla-*.egg"),
        str(root / "WindowsNoEditor" / "PythonAPI" / "carla" / "dist" / "carla-*.whl"),
    ]
    for pattern in patterns:
        matches = glob.glob(pattern)
        if matches:
            return matches[0]
    return None


def import_carla():
    api_path = find_python_api()
    if api_path and api_path not in sys.path:
        sys.path.insert(0, api_path)
    try:
        import carla  # type: ignore

        return carla
    except Exception as exc:
        raise CarlaUnavailable(f"CARLA Python API is unavailable: {exc}") from exc


def carla_status() -> Dict[str, Any]:
    cfg = get_config()
    exe = find_carla_executable(cfg.home)
    api_path = find_python_api(cfg.home)
    api_available = False
    api_error = ""
    connected = False
    current_map = None
    try:
        carla = import_carla()
        api_available = True
        try:
            client = carla.Client(cfg.host, cfg.port)
            client.set_timeout(1.5)
            world = client.get_world()
            connected = True
            current_map = world.get_map().name
        except Exception as exc:
            api_error = str(exc)
    except Exception as exc:
        api_error = str(exc)

    return {
        "success": True,
        "carla_home": str(cfg.home),
        "executable": str(exe) if exe else None,
        "installed": exe is not None,
        "python_api_path": api_path,
        "python_api_available": api_available,
        "host": cfg.host,
        "port": cfg.port,
        "process_running": _carla_process is not None and _carla_process.poll() is None,
        "connected": connected,
        "current_map": current_map,
        "error": api_error,
    }


def start_carla(windowed: bool = True, res_x: int = 1280, res_y: int = 720) -> Dict[str, Any]:
    global _carla_process
    if _carla_process is not None and _carla_process.poll() is None:
        return {"success": True, "already_running": True, "pid": _carla_process.pid}

    exe = find_carla_executable()
    if exe is None:
        raise CarlaUnavailable("CarlaUE4.exe was not found. Run scripts/install_carla_0915.ps1 first.")

    args = [str(exe)]
    if windowed:
        args += ["-windowed", f"-ResX={int(res_x)}", f"-ResY={int(res_y)}"]
    _carla_process = subprocess.Popen(args, cwd=str(exe.parent))
    return {"success": True, "already_running": False, "pid": _carla_process.pid}


def stop_carla() -> Dict[str, Any]:
    global _carla_process
    if _carla_process is not None and _carla_process.poll() is None:
        pid = _carla_process.pid
        _carla_process.terminate()
        try:
            _carla_process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            _carla_process.kill()
        _carla_process = None
        return {"success": True, "stopped": True, "pid": pid}
    _carla_process = None
    return {"success": True, "stopped": False}


def get_client():
    cfg = get_config()
    carla = import_carla()
    client = carla.Client(cfg.host, cfg.port)
    client.set_timeout(cfg.timeout_seconds)
    return carla, client


def available_maps() -> Dict[str, Any]:
    try:
        _carla, client = get_client()
        maps = sorted([name.split("/")[-1] for name in client.get_available_maps()])
        return {"success": True, "connected": True, "maps": maps}
    except Exception as exc:
        return {"success": True, "connected": False, "maps": DEFAULT_MAPS, "error": str(exc)}


def run_carla_simulation(payload: Dict[str, Any]) -> Dict[str, Any]:
    carla, client = get_client()
    town = payload.get("town") or payload.get("carla_town") or "Town03"
    duration_seconds = float(payload.get("duration_seconds", 10.0))
    traffic_vehicles = int(payload.get("traffic_vehicles", 10))
    traffic_walkers = int(payload.get("traffic_walkers", 0))
    weather = payload.get("weather", "ClearNoon")
    spawn_point_index = int(payload.get("spawn_point_index", 0))
    synchronous_mode = bool(payload.get("synchronous_mode", True))
    user_id = int(payload.get("user_id", 2))
    scenario_id = payload.get("scenario_id")

    run_uid = payload.get("run_uid") or f"carla_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}_{uuid.uuid4().hex[:8]}"
    output_dir = PROJECT_ROOT / "outputs" / "carla" / run_uid
    static_dir = PROJECT_ROOT / "backend" / "static" / "carla" / run_uid
    output_dir.mkdir(parents=True, exist_ok=True)
    static_dir.mkdir(parents=True, exist_ok=True)
    trajectory_path = output_dir / "trajectory.json"
    image_path = static_dir / "camera.jpg"

    world = client.load_world(town)
    traffic_manager = client.get_trafficmanager()
    original_settings = world.get_settings()
    actors = []
    collision_count = 0
    image_queue: "queue.Queue[Any]" = queue.Queue(maxsize=5)

    try:
        if synchronous_mode:
            settings = world.get_settings()
            settings.synchronous_mode = True
            settings.fixed_delta_seconds = 0.05
            world.apply_settings(settings)
            traffic_manager.set_synchronous_mode(True)

        if hasattr(carla.WeatherParameters, weather):
            world.set_weather(getattr(carla.WeatherParameters, weather))

        blueprints = world.get_blueprint_library()
        vehicle_bp = blueprints.filter(payload.get("ego_vehicle", "vehicle.tesla.model3"))[0]
        spawn_points = world.get_map().get_spawn_points()
        if not spawn_points:
            raise CarlaUnavailable(f"No spawn points are available in {town}.")
        ego_transform = spawn_points[spawn_point_index % len(spawn_points)]
        ego = world.try_spawn_actor(vehicle_bp, ego_transform)
        if ego is None:
            raise CarlaUnavailable("Could not spawn ego vehicle. Try a different spawn_point_index.")
        actors.append(ego)
        ego.set_autopilot(True, traffic_manager.get_port())

        _spawn_traffic(carla, world, traffic_manager, actors, traffic_vehicles, traffic_walkers, spawn_points)
        camera = _attach_camera(carla, world, blueprints, ego, image_queue)
        actors.append(camera)
        collision_sensor = _attach_collision_sensor(carla, world, blueprints, ego)
        actors.append(collision_sensor)

        def count_collision(_event):
            nonlocal collision_count
            collision_count += 1

        collision_sensor.listen(count_collision)
        camera.listen(lambda image: _safe_put(image_queue, image))

        frames = []
        started = time.perf_counter()
        last_location = None
        distance_m = 0.0
        while time.perf_counter() - started < duration_seconds:
            if synchronous_mode:
                world.tick()
            else:
                world.wait_for_tick()
            transform = ego.get_transform()
            velocity = ego.get_velocity()
            location = transform.location
            speed_mps = (velocity.x ** 2 + velocity.y ** 2 + velocity.z ** 2) ** 0.5
            if last_location is not None:
                distance_m += location.distance(last_location)
            last_location = location
            frames.append({
                "t": round(time.perf_counter() - started, 3),
                "x": float(location.x),
                "y": float(location.y),
                "z": float(location.z),
                "yaw": float(transform.rotation.yaw),
                "speed_mps": float(speed_mps),
                "speed_kmh": float(speed_mps * 3.6),
            })

        _save_latest_image(image_queue, image_path)
        metrics = _metrics_from_frames(frames, distance_m, collision_count, duration_seconds)
        trajectory_path.write_text(json.dumps({"run_uid": run_uid, "town": town, "frames": frames}, indent=2), encoding="utf-8")
        db_run_id = _persist_carla_run(
            run_uid=run_uid,
            user_id=user_id,
            scenario_id=int(scenario_id) if scenario_id else None,
            request_config=payload,
            metrics=metrics,
            trajectory_path=str(trajectory_path),
            image_path=str(image_path),
        )
        return {
            "success": True,
            "run_uid": run_uid,
            "db_run_id": db_run_id,
            "town": town,
            "metrics": metrics,
            "trajectory_path": str(trajectory_path),
            "camera_image_url": f"/static/carla/{run_uid}/camera.jpg" if image_path.exists() else None,
            "timesteps": frames,
            "stats": {
                "collision_count": collision_count,
                "distance_m": round(distance_m, 2),
                "average_speed_kmh": metrics["average_speed_kmh"],
                "duration_seconds": metrics["duration_seconds"],
            },
        }
    finally:
        for actor in actors:
            try:
                actor.destroy()
            except Exception:
                pass
        if synchronous_mode:
            try:
                world.apply_settings(original_settings)
                traffic_manager.set_synchronous_mode(False)
            except Exception:
                pass


def _safe_put(image_queue: "queue.Queue[Any]", image: Any) -> None:
    try:
        if image_queue.full():
            image_queue.get_nowait()
        image_queue.put_nowait(image)
    except Exception:
        pass


def _attach_camera(carla, world, blueprints, ego, image_queue):
    camera_bp = blueprints.find("sensor.camera.rgb")
    camera_bp.set_attribute("image_size_x", "1280")
    camera_bp.set_attribute("image_size_y", "720")
    camera_bp.set_attribute("fov", "90")
    transform = carla.Transform(carla.Location(x=1.6, z=1.7), carla.Rotation(pitch=-8))
    return world.spawn_actor(camera_bp, transform, attach_to=ego)


def _attach_collision_sensor(carla, world, blueprints, ego):
    sensor_bp = blueprints.find("sensor.other.collision")
    return world.spawn_actor(sensor_bp, carla.Transform(), attach_to=ego)


def _spawn_traffic(carla, world, traffic_manager, actors, vehicle_count: int, walker_count: int, spawn_points) -> None:
    blueprints = world.get_blueprint_library()
    vehicle_bps = blueprints.filter("vehicle.*")
    random.shuffle(spawn_points)
    for transform in spawn_points[1: vehicle_count + 1]:
        bp = random.choice(vehicle_bps)
        actor = world.try_spawn_actor(bp, transform)
        if actor is not None:
            actor.set_autopilot(True, traffic_manager.get_port())
            actors.append(actor)

    if walker_count <= 0:
        return
    walker_bps = blueprints.filter("walker.pedestrian.*")
    for _ in range(walker_count):
        location = world.get_random_location_from_navigation()
        if location is None:
            continue
        transform = carla.Transform(location)
        actor = world.try_spawn_actor(random.choice(walker_bps), transform)
        if actor is not None:
            actors.append(actor)


def _save_latest_image(image_queue: "queue.Queue[Any]", image_path: Path) -> None:
    latest = None
    while True:
        try:
            latest = image_queue.get_nowait()
        except queue.Empty:
            break
    if latest is None:
        return
    raw = bytes(latest.raw_data)
    image = Image.frombuffer("RGBA", (latest.width, latest.height), raw, "raw", "BGRA", 0, 1)
    image.convert("RGB").save(image_path, quality=90)


def _metrics_from_frames(frames: list[Dict[str, Any]], distance_m: float, collision_count: int, duration_seconds: float) -> Dict[str, Any]:
    speeds = [frame["speed_kmh"] for frame in frames]
    return {
        "duration_seconds": round(duration_seconds, 2),
        "frame_count": len(frames),
        "distance_m": round(distance_m, 2),
        "collision_count": int(collision_count),
        "average_speed_kmh": round(sum(speeds) / len(speeds), 2) if speeds else 0.0,
        "max_speed_kmh": round(max(speeds), 2) if speeds else 0.0,
    }


def _persist_carla_run(
    run_uid: str,
    user_id: int,
    scenario_id: Optional[int],
    request_config: Dict[str, Any],
    metrics: Dict[str, Any],
    trajectory_path: str,
    image_path: str,
) -> Optional[int]:
    if not is_database_configured():
        return None
    try:
        with session_scope() as session:
            user = session.get(AppUser, user_id)
            if user is None:
                return None
            scenario = session.get(SimulationScenario, scenario_id) if scenario_id else None
            run = SimulationRun(
                run_uid=run_uid,
                user_id=user.id,
                scenario_id=scenario.id if scenario else None,
                status="succeeded",
                max_samples=int(request_config.get("duration_seconds", 10)),
                request_config_json=request_config,
                metrics_json={"carla": metrics},
                artifacts_json={
                    "trajectory": trajectory_path,
                    "camera_image": image_path,
                },
                run_record_path=trajectory_path,
                result_summary=(
                    f"CARLA {request_config.get('town', request_config.get('carla_town', 'Town03'))}: "
                    f"{metrics['distance_m']}m, {metrics['collision_count']} collisions, "
                    f"{metrics['average_speed_kmh']} km/h avg"
                ),
                started_at=datetime.now(timezone.utc),
                finished_at=datetime.now(timezone.utc),
            )
            session.add(run)
            session.flush()
            session.add(SimulationRunArtifact(
                run_id=run.id,
                artifact_type="trajectory",
                title="CARLA trajectory",
                uri=trajectory_path,
                mime_type="application/json",
            ))
            if Path(image_path).exists():
                session.add(SimulationRunArtifact(
                    run_id=run.id,
                    artifact_type="image",
                    title="CARLA RGB camera",
                    uri=image_path,
                    mime_type="image/jpeg",
                ))
            return run.id
    except Exception:
        return None
