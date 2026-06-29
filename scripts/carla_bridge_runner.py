from __future__ import annotations

import argparse
import glob
import json
import os
import queue
import random
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path


def find_api_path(carla_home: Path) -> str:
    patterns = [
        str(carla_home / "PythonAPI" / "carla" / "dist" / "carla-*.egg"),
        str(carla_home / "PythonAPI" / "carla" / "dist" / "carla-*.whl"),
        str(carla_home / "WindowsNoEditor" / "PythonAPI" / "carla" / "dist" / "carla-*.egg"),
        str(carla_home / "WindowsNoEditor" / "PythonAPI" / "carla" / "dist" / "carla-*.whl"),
    ]
    for pattern in patterns:
        matches = glob.glob(pattern)
        if matches:
            return matches[0]
    raise RuntimeError("CARLA PythonAPI was not found under CARLA_HOME")


def load_carla(carla_home: str):
    api_path = find_api_path(Path(carla_home))
    sys.path.insert(0, api_path)
    import carla  # type: ignore

    return carla


def get_client(carla, host: str, port: int, timeout: float = 10.0):
    client = carla.Client(host, port)
    client.set_timeout(timeout)
    return client


def command_status(carla, client):
    world = client.get_world()
    return {
        "connected": True,
        "current_map": world.get_map().name,
        "server_version": client.get_server_version(),
        "client_version": client.get_client_version(),
    }


def command_maps(client):
    return {"maps": sorted([name.split("/")[-1] for name in client.get_available_maps()])}


def command_run(carla, client, payload, project_root: Path):
    town = payload.get("town") or payload.get("carla_town") or "Town03"
    duration_seconds = float(payload.get("duration_seconds", 10.0))
    traffic_vehicles = int(payload.get("traffic_vehicles", 10))
    traffic_walkers = int(payload.get("traffic_walkers", 0))
    weather = payload.get("weather", "ClearNoon")
    spawn_point_index = int(payload.get("spawn_point_index", 0))
    requested_synchronous_mode = bool(payload.get("synchronous_mode", False))
    synchronous_mode = requested_synchronous_mode and os.environ.get("CARLA_ENABLE_SYNCHRONOUS") == "1"
    run_uid = payload.get("run_uid") or "carla_{}_{}".format(
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        uuid.uuid4().hex[:8],
    )

    output_dir = project_root / "outputs" / "carla" / run_uid
    static_dir = project_root / "backend" / "static" / "carla" / run_uid
    output_dir.mkdir(parents=True, exist_ok=True)
    static_dir.mkdir(parents=True, exist_ok=True)
    trajectory_path = output_dir / "trajectory.json"
    image_path = static_dir / "camera.jpg"

    current_world = client.get_world()
    current_map = current_world.get_map().name.split("/")[-1]
    world = current_world if current_map == town else client.load_world(town)
    world.wait_for_tick()
    traffic_manager = client.get_trafficmanager()
    original_settings = world.get_settings()
    actors = []
    image_queue = queue.Queue(maxsize=5)
    collision_count = 0

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
        spawn_points = world.get_map().get_spawn_points()
        if not spawn_points:
            raise RuntimeError("No spawn points are available in {}".format(town))
        ego_bp = blueprints.filter(payload.get("ego_vehicle", "vehicle.tesla.model3"))[0]
        ego = world.try_spawn_actor(ego_bp, spawn_points[spawn_point_index % len(spawn_points)])
        if ego is None:
            raise RuntimeError("Could not spawn ego vehicle")
        actors.append(ego)
        ego.set_autopilot(True, traffic_manager.get_port())

        vehicle_bps = blueprints.filter("vehicle.*")
        random.shuffle(spawn_points)
        for transform in spawn_points[1: traffic_vehicles + 1]:
            actor = world.try_spawn_actor(random.choice(vehicle_bps), transform)
            if actor is not None:
                actor.set_autopilot(True, traffic_manager.get_port())
                actors.append(actor)

        if traffic_walkers > 0:
            walker_bps = blueprints.filter("walker.pedestrian.*")
            for _ in range(traffic_walkers):
                location = world.get_random_location_from_navigation()
                if location is None:
                    continue
                actor = world.try_spawn_actor(random.choice(walker_bps), carla.Transform(location))
                if actor is not None:
                    actors.append(actor)

        camera_bp = blueprints.find("sensor.camera.rgb")
        camera_bp.set_attribute("image_size_x", "1280")
        camera_bp.set_attribute("image_size_y", "720")
        camera_bp.set_attribute("fov", "90")
        camera = world.spawn_actor(
            camera_bp,
            carla.Transform(carla.Location(x=1.6, z=1.7), carla.Rotation(pitch=-8)),
            attach_to=ego,
        )
        actors.append(camera)
        camera.listen(lambda image: put_latest(image_queue, image))

        collision_sensor = world.spawn_actor(blueprints.find("sensor.other.collision"), carla.Transform(), attach_to=ego)
        actors.append(collision_sensor)

        def on_collision(_event):
            nonlocal collision_count
            collision_count += 1

        collision_sensor.listen(on_collision)

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

        latest = drain_latest(image_queue)
        if latest is not None:
            latest.save_to_disk(str(image_path))

        speeds = [frame["speed_kmh"] for frame in frames]
        metrics = {
            "duration_seconds": round(duration_seconds, 2),
            "frame_count": len(frames),
            "distance_m": round(distance_m, 2),
            "collision_count": int(collision_count),
            "average_speed_kmh": round(sum(speeds) / len(speeds), 2) if speeds else 0.0,
            "max_speed_kmh": round(max(speeds), 2) if speeds else 0.0,
            "requested_synchronous_mode": requested_synchronous_mode,
            "synchronous_mode_used": synchronous_mode,
        }
        trajectory_path.write_text(json.dumps({"run_uid": run_uid, "town": town, "frames": frames}, indent=2), encoding="utf-8")
        return {
            "success": True,
            "run_uid": run_uid,
            "town": town,
            "metrics": metrics,
            "trajectory_path": str(trajectory_path),
            "camera_image_path": str(image_path) if image_path.exists() else None,
            "camera_image_url": "/static/carla/{}/camera.jpg".format(run_uid) if image_path.exists() else None,
            "timesteps": frames,
            "stats": {
                "collision_count": collision_count,
                "distance_m": round(distance_m, 2),
                "average_speed_kmh": metrics["average_speed_kmh"],
                "duration_seconds": metrics["duration_seconds"],
            },
        }
    finally:
        for actor in reversed(actors):
            try:
                if hasattr(actor, "is_listening") and actor.is_listening:
                    actor.stop()
            except Exception:
                pass
        try:
            world.wait_for_tick()
        except Exception:
            time.sleep(0.2)
        try:
            client.apply_batch([carla.command.DestroyActor(actor) for actor in reversed(actors)])
        except Exception:
            for actor in reversed(actors):
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


def put_latest(image_queue, image):
    try:
        if image_queue.full():
            image_queue.get_nowait()
        image_queue.put_nowait(image)
    except Exception:
        pass


def drain_latest(image_queue):
    latest = None
    while True:
        try:
            latest = image_queue.get_nowait()
        except queue.Empty:
            return latest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["status", "maps", "run"])
    parser.add_argument("--carla-home", required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=2000)
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--payload", default="{}")
    args = parser.parse_args()

    try:
        carla = load_carla(args.carla_home)
        client_timeout = 120.0 if args.command == "run" else 10.0
        client = get_client(carla, args.host, args.port, timeout=client_timeout)
        if args.command == "status":
            result = command_status(carla, client)
        elif args.command == "maps":
            result = command_maps(client)
        else:
            result = command_run(carla, client, json.loads(args.payload), Path(args.project_root))
        result["success"] = True
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except Exception as exc:
        print(json.dumps({"success": False, "error": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
