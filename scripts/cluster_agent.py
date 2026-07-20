"""
LONGIN SANCTUARY — Cluster Agent
Runs on worker nodes to join the master and provide GPU compute.

Usage:
  python cluster_agent.py --master 192.168.1.15 --name NITRO-NB

Installation (on new device):
  1. Get this script from master node or GitHub
  2. Install Python 3.11+
  3. pip install httpx psutil zeroconf
  4. python cluster_agent.py --master <master_ip>
"""

import argparse
import asyncio
import json
import platform
import socket
import subprocess
import sys
from pathlib import Path

import httpx
import psutil


def get_hardware_info() -> dict:
    """Collect hardware information for the join request."""
    info = {
        "hostname": socket.gethostname(),
        "os": platform.system(),
        "os_version": platform.version(),
        "cpu": {
            "name": platform.processor(),
            "cores_physical": psutil.cpu_count(logical=False),
            "cores_logical": psutil.cpu_count(logical=True),
        },
        "ram_total_mb": int(psutil.virtual_memory().total / 1024 / 1024),
        "gpu": [],
    }

    # NVIDIA GPU detection
    try:
        result = subprocess.run(
            ["nvidia-smi",
             "--query-gpu=name,memory.total,driver_version",
             "--format=csv,noheader"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            for line in result.stdout.strip().split("\n"):
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 3:
                    info["gpu"].append({
                        "name": parts[0],
                        "vram_mb": int(parts[1].split(" ")[0]),
                        "driver": parts[2],
                        "vendor": "NVIDIA",
                    })
    except FileNotFoundError:
        pass

    return info


async def send_join_request(master_ip: str, master_port: int, node_name: str) -> dict | None:
    """Send join request to master node."""
    hw = get_hardware_info()
    hw["requested_name"] = node_name

    print(f"🔍 Hardware detected:")
    print(f"   CPU: {hw['cpu']['name']}")
    print(f"   RAM: {hw['ram_total_mb']} MB")
    for gpu in hw["gpu"]:
        print(f"   GPU: {gpu['name']} ({gpu['vram_mb']} MB VRAM)")

    url = f"http://{master_ip}:{master_port}/api/v1/network/join"
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, json={
                "hostname": hw["hostname"],
                "ip": get_local_ip(),
                "hardware_info": hw,
            })
            if resp.status_code in (200, 201):
                return resp.json()
            print(f"❌ Master rejected request: {resp.status_code} {resp.text}")
            return None
    except Exception as e:
        print(f"❌ Could not reach master at {master_ip}:{master_port}: {e}")
        return None


async def wait_for_approval(master_ip: str, master_port: int, request_id: str):
    """Poll master for approval status."""
    print(f"⏳ Waiting for approval from master ({master_ip})...")
    print(f"   Check the LONGIN SANCTUARY UI to approve this request.")

    url = f"http://{master_ip}:{master_port}/api/v1/network/join-requests/{request_id}"
    async with httpx.AsyncClient(timeout=10) as client:
        while True:
            try:
                resp = await client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    status = data.get("status", "pending")
                    if status == "approved":
                        print("✅ Approved!")
                        return data
                    elif status == "rejected":
                        print("❌ Rejected by master.")
                        sys.exit(1)
            except Exception:
                pass
            await asyncio.sleep(5)


async def install_dependencies(install_path: str, install_comfyui: bool, install_ollama: bool):
    """Install required components."""
    path = Path(install_path)
    path.mkdir(parents=True, exist_ok=True)
    print(f"📦 Installing to: {path}")

    # Install Ollama
    if install_ollama:
        print("📥 Installing Ollama...")
        if platform.system() == "Windows":
            subprocess.run(
                ["winget", "install", "Ollama.Ollama", "--silent"],
                check=False,
            )
        else:
            subprocess.run(
                "curl -fsSL https://ollama.ai/install.sh | sh",
                shell=True, check=False,
            )

    # Install ComfyUI
    if install_comfyui:
        print("📥 Installing ComfyUI...")
        comfy_path = path / "comfyui"
        if not comfy_path.exists():
            subprocess.run(
                ["git", "clone",
                 "https://github.com/comfyanonymous/ComfyUI.git",
                 str(comfy_path)],
                check=False,
            )
        # Install ComfyUI deps
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r",
             str(comfy_path / "requirements.txt")],
            cwd=str(comfy_path), check=False,
        )

    print("✅ Installation complete!")


def get_local_ip() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"


async def run_worker_services(install_path: str):
    """Start worker services: Ollama + ComfyUI."""
    print("🚀 Starting worker services...")

    path = Path(install_path)
    comfy_path = path / "comfyui"

    tasks = []
    if comfy_path.exists():
        print(f"   Starting ComfyUI from {comfy_path}")
        tasks.append(asyncio.create_subprocess_exec(
            sys.executable, "main.py",
            "--listen", "0.0.0.0",
            "--port", "8188",
            cwd=str(comfy_path),
        ))

    if tasks:
        await asyncio.gather(*[t for t in tasks])

    print("✅ Worker services running. Node is ready!")

    # Keep alive with heartbeat
    while True:
        await asyncio.sleep(30)
        print("💓 Heartbeat — worker alive")


async def main():
    parser = argparse.ArgumentParser(description="LONGIN SANCTUARY Cluster Agent")
    parser.add_argument("--master", required=True, help="Master node IP address")
    parser.add_argument("--port", type=int, default=8000, help="Master API port")
    parser.add_argument("--name", default=socket.gethostname(), help="This node's name")
    args = parser.parse_args()

    print("=" * 50)
    print("  🌟 LONGIN SANCTUARY — Cluster Agent")
    print(f"  Joining master: {args.master}:{args.port}")
    print(f"  Node name: {args.name}")
    print("=" * 50)

    # 1. Send join request
    result = await send_join_request(args.master, args.port, args.name)
    if not result:
        sys.exit(1)

    request_id = result.get("id")
    print(f"📡 Join request sent. Request ID: {request_id}")

    # 2. Wait for approval
    approval = await wait_for_approval(args.master, args.port, request_id)
    install_path = approval.get("install_path", "C:/LonginSanctuary")
    install_comfyui = approval.get("install_comfyui", True)
    install_ollama = approval.get("install_ollama", True)

    # 3. Install dependencies
    await install_dependencies(install_path, install_comfyui, install_ollama)

    # 4. Start services
    await run_worker_services(install_path)


if __name__ == "__main__":
    asyncio.run(main())
