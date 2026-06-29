from __future__ import annotations

import argparse
import glob
import json
import os
import platform
import shutil
import socket
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional


DEFAULT_HOME = r"D:\CARLA\CARLA_0.9.15"


def _is_port_open(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _find_executable(carla_home: Path) -> Optional[Path]:
    direct = carla_home / "CarlaUE4.exe"
    if direct.exists():
        return direct
    matches = list(carla_home.rglob("CarlaUE4.exe")) if carla_home.exists() else []
    return matches[0] if matches else None


def _find_python_api(carla_home: Path) -> Optional[str]:
    patterns = [
        str(carla_home / "PythonAPI" / "carla" / "dist" / "carla-*.egg"),
        str(carla_home / "WindowsNoEditor" / "PythonAPI" / "carla" / "dist" / "carla-*.egg"),
        str(carla_home / "PythonAPI" / "carla" / "dist" / "carla-*.whl"),
        str(carla_home / "WindowsNoEditor" / "PythonAPI" / "carla" / "dist" / "carla-*.whl"),
    ]
    for pattern in patterns:
        matches = glob.glob(pattern)
        if matches:
            return matches[0]
    return None


def _gpu_info() -> list[Dict[str, Any]]:
    if platform.system().lower() != "windows":
        return []
    try:
        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "Get-CimInstance Win32_VideoController | Select-Object Name,DriverVersion | ConvertTo-Json",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if result.returncode != 0 or not result.stdout.strip():
            return []
        data = json.loads(result.stdout)
        return data if isinstance(data, list) else [data]
    except Exception:
        return []


def _try_import_carla(api_path: Optional[str]) -> Dict[str, Any]:
    if api_path:
        sys.path.insert(0, api_path)
    try:
        import carla  # type: ignore

        return {
            "available": True,
            "module": getattr(carla, "__file__", "unknown"),
            "api_path": api_path,
        }
    except Exception as exc:
        return {
            "available": False,
            "api_path": api_path,
            "error": str(exc),
        }


def check_environment(carla_home: str, host: str, port: int) -> Dict[str, Any]:
    home = Path(carla_home)
    exe = _find_executable(home)
    api_path = _find_python_api(home)
    total, used, free = shutil.disk_usage(home.anchor or ".")
    return {
        "carla_home": str(home),
        "carla_home_exists": home.exists(),
        "carla_executable": str(exe) if exe else None,
        "carla_executable_exists": exe is not None,
        "python": sys.version,
        "platform": platform.platform(),
        "disk": {
            "drive": home.anchor,
            "free_gb": round(free / (1024 ** 3), 2),
            "total_gb": round(total / (1024 ** 3), 2),
        },
        "ports": {
            str(port): _is_port_open(host, port),
            str(port + 1): _is_port_open(host, port + 1),
        },
        "gpu": _gpu_info(),
        "python_api": _try_import_carla(api_path),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Check CARLA 0.9.15 local environment.")
    parser.add_argument("--carla-home", default=os.environ.get("CARLA_HOME", DEFAULT_HOME))
    parser.add_argument("--host", default=os.environ.get("CARLA_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("CARLA_PORT", "2000")))
    args = parser.parse_args()

    report = check_environment(args.carla_home, args.host, args.port)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["carla_executable_exists"]:
        return 2
    if not report["python_api"]["available"]:
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
