#!/usr/bin/env python3
"""Kizuna Node: consent-based local capability monitor using only Python's standard library."""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
import platform
import shutil
import socket
import subprocess
import sys
import time
import uuid
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

VERSION = "0.1.0"
CREATIVE_TOOLS = {
    "blender": ["blender"], "krita": ["krita"], "gimp": ["gimp", "gimp-3.0"],
    "ffmpeg": ["ffmpeg"], "ollama": ["ollama"], "comfyui": ["comfyui"],
    "opentoonz": ["opentoonz"], "davinci resolve": ["resolve"],
    "automatic1111 / forge": ["webui-user.bat", "webui.sh"],
}


def config_path() -> Path:
    if os.name == "nt":
        root = Path(os.getenv("APPDATA", Path.home()))
    else:
        root = Path(os.getenv("XDG_CONFIG_HOME", Path.home() / ".config"))
    return root / "Kizuna" / "node.json"


def total_ram_gb() -> float:
    try:
        if os.name == "nt":
            class MemoryStatus(ctypes.Structure):
                _fields_ = [("length", ctypes.c_ulong), ("memory_load", ctypes.c_ulong), ("total", ctypes.c_ulonglong), ("available", ctypes.c_ulonglong), ("page_total", ctypes.c_ulonglong), ("page_available", ctypes.c_ulonglong), ("virtual_total", ctypes.c_ulonglong), ("virtual_available", ctypes.c_ulonglong), ("extended", ctypes.c_ulonglong)]
            status = MemoryStatus(); status.length = ctypes.sizeof(status)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status))
            return round(status.total / 1024**3, 1)
        pages = os.sysconf("SC_PHYS_PAGES"); page_size = os.sysconf("SC_PAGE_SIZE")
        return round(pages * page_size / 1024**3, 1)
    except Exception:
        return 0.0


def cpu_name() -> str:
    name = platform.processor() or platform.machine()
    if os.name == "nt":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0") as key:
                name = winreg.QueryValueEx(key, "ProcessorNameString")[0]
        except Exception:
            pass
    return " ".join(str(name).split())[:255]


def gpu_inventory() -> list[dict]:
    command = shutil.which("nvidia-smi")
    if command:
        try:
            output = subprocess.run([command, "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=5, check=False).stdout
            return [{"name": name.strip(), "memory_mb": int(memory.strip())} for line in output.splitlines() if "," in line for name, memory in [line.rsplit(",", 1)]]
        except Exception:
            pass
    if os.name == "nt" and shutil.which("powershell"):
        try:
            script = "Get-CimInstance Win32_VideoController | Select-Object Name,AdapterRAM | ConvertTo-Json -Compress"
            raw = subprocess.run(["powershell", "-NoProfile", "-Command", script], capture_output=True, text=True, timeout=8, check=False).stdout.strip()
            items = json.loads(raw) if raw else []
            if isinstance(items, dict): items = [items]
            return [{"name": str(item.get("Name", "Unknown GPU")), "memory_mb": round(int(item.get("AdapterRAM") or 0) / 1024**2)} for item in items]
        except Exception:
            pass
    return []


def windows_installed_names() -> set[str]:
    names: set[str] = set()
    if os.name != "nt": return names
    try:
        import winreg
        roots = [(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"), (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"), (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall")]
        for root, path in roots:
            try:
                with winreg.OpenKey(root, path) as parent:
                    for index in range(winreg.QueryInfoKey(parent)[0]):
                        try:
                            with winreg.OpenKey(parent, winreg.EnumKey(parent, index)) as item:
                                value = winreg.QueryValueEx(item, "DisplayName")[0]
                                if value: names.add(str(value).strip())
                        except OSError:
                            continue
            except OSError:
                continue
    except Exception:
        pass
    return names


def creative_software() -> list[str]:
    detected = {name for name, commands in CREATIVE_TOOLS.items() if any(shutil.which(command) for command in commands)}
    creative_terms = ("adobe", "premiere", "after effects", "audition", "photoshop", "illustrator", "corel", "gimp", "krita", "blender", "opentoonz", "davinci", "resolve", "ollama", "comfyui", "ffmpeg", "automatic1111", "forge", "invokeai")
    detected.update(name for name in windows_installed_names() if any(term in name.lower() for term in creative_terms))
    return sorted(detected)


def all_software() -> list[str]:
    names: set[str] = set(creative_software())
    if os.name == "nt":
        names.update(windows_installed_names())
    elif sys.platform == "darwin":
        names.update(path.stem for path in Path("/Applications").glob("*.app"))
    else:
        command = shutil.which("dpkg-query")
        if command:
            try:
                names.update(subprocess.run([command, "-W", "-f=${binary:Package}\n"], capture_output=True, text=True, timeout=15, check=False).stdout.splitlines())
            except Exception:
                pass
    return sorted(name for name in names if name)[:2000]


def benchmark_score() -> float:
    start = time.perf_counter(); rounds = 0; payload = b"kizuna-local-capability-check"
    while time.perf_counter() - start < 0.35:
        payload = hashlib.sha256(payload).digest(); rounds += 1
    elapsed = max(time.perf_counter() - start, 0.001)
    return round(rounds / elapsed / 1000, 1)


def scan(software_level: str) -> dict:
    software = [] if software_level == "none" else all_software() if software_level == "all" else creative_software()
    gpus = gpu_inventory(); capabilities = ["cpu_tasks"]; software_text = " ".join(software).lower()
    if total_ram_gb() >= 16: capabilities.append("memory_intensive")
    if gpus: capabilities.extend(["gpu_render", "image_generation"])
    if "ollama" in software_text: capabilities.append("local_ai")
    if "comfyui" in software_text: capabilities.extend(["comfyui", "animation_generation"])
    if "ffmpeg" in software_text: capabilities.extend(["video_encode", "audio_encode"])
    return {"node_key": str(uuid.uuid4()), "name": socket.gethostname(), "os_name": platform.system(), "os_version": platform.version(), "architecture": platform.machine(), "cpu_name": cpu_name(), "logical_cores": os.cpu_count() or 1, "ram_gb": total_ram_gb(), "gpu": gpus, "software": software, "benchmark_score": benchmark_score(), "capabilities": sorted(set(capabilities))}


def request_json(url: str, payload: dict | None = None, token: str = "") -> dict:
    headers = {"Accept": "application/json"}
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"; data = json.dumps(payload).encode("utf-8")
    if token: headers["Authorization"] = f"Bearer {token}"
    request = Request(url, data=data, headers=headers, method="POST" if payload is not None else "GET")
    try:
        with urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise RuntimeError(f"Kizuna returned {exc.code}: {exc.read().decode('utf-8', errors='replace')[:300]}") from exc
    except URLError as exc:
        raise RuntimeError(f"Could not reach Kizuna: {exc.reason}") from exc


def save_config(data: dict) -> None:
    path = config_path(); path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    if os.name != "nt": path.chmod(0o600)


def enroll(args: argparse.Namespace) -> None:
    profile = scan(args.software_level); profile["code"] = args.code
    print(json.dumps({key: value for key, value in profile.items() if key != "code"}, indent=2))
    if not args.yes and input("Send this capability profile to Kizuna? [y/N] ").strip().lower() != "y":
        print("Nothing was sent."); return
    result = request_json(args.server.rstrip("/") + "/api/nodes/enroll", profile)
    save_config({"server": args.server.rstrip("/"), "node_key": result["node_key"], "token": result["token"], "software_level": args.software_level})
    print(f"Enrolled {result['name']}. Configuration saved to {config_path()}")


def sync_once() -> None:
    path = config_path()
    if not path.exists(): raise RuntimeError("This computer is not enrolled. Run the enroll command first.")
    config = json.loads(path.read_text(encoding="utf-8"))
    result = request_json(f"{config['server']}/api/nodes/{config['node_key']}/heartbeat", {"benchmark_score": benchmark_score()}, config["token"])
    print(f"Kizuna node is {result['status']} · {result['last_seen']}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Connect this computer to a Kizuna studio.")
    parser.add_argument("--version", action="version", version=VERSION)
    sub = parser.add_subparsers(dest="command", required=True)
    scan_parser = sub.add_parser("scan", help="Preview the data that would be shared")
    scan_parser.add_argument("--software-level", choices=["none", "creative", "all"], default="creative")
    enroll_parser = sub.add_parser("enroll", help="Scan and connect this computer")
    enroll_parser.add_argument("--server", required=True); enroll_parser.add_argument("--code", required=True)
    enroll_parser.add_argument("--software-level", choices=["none", "creative", "all"], default="creative")
    enroll_parser.add_argument("--yes", action="store_true", help="Skip the profile confirmation prompt")
    sub.add_parser("sync", help="Send a fresh health check")
    monitor_parser = sub.add_parser("monitor", help="Keep the node online")
    monitor_parser.add_argument("--interval", type=int, default=60)
    args = parser.parse_args()
    try:
        if args.command == "scan": print(json.dumps(scan(args.software_level), indent=2))
        elif args.command == "enroll": enroll(args)
        elif args.command == "sync": sync_once()
        else:
            while True:
                sync_once(); time.sleep(max(30, args.interval))
        return 0
    except (RuntimeError, KeyboardInterrupt) as exc:
        print(str(exc), file=sys.stderr); return 1


if __name__ == "__main__":
    raise SystemExit(main())
