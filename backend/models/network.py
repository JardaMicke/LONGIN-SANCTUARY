"""Network / cluster Pydantic models."""
from datetime import datetime
from typing import Literal, Optional
from uuid import UUID, uuid4
from pydantic import BaseModel, Field


class NodeInfo(BaseModel):
    id: str                                # hostname or UUID
    name: str
    ip: str
    role: Literal["master", "worker", "both"]
    status: Literal["online", "offline", "joining"]
    gpu_name: Optional[str] = None
    gpu_vram_total_mb: int = 0
    gpu_vram_free_mb: int = 0
    gpu_util_pct: int = 0
    cpu_cores: int = 0
    ram_total_mb: int = 0
    ram_free_mb: int = 0
    services: list[str] = []             # ["ollama", "comfyui", "exo", "llama_rpc"]
    last_seen: datetime = Field(default_factory=datetime.utcnow)


class ClusterStatus(BaseModel):
    master_node: str
    total_vram_mb: int
    free_vram_mb: int
    nodes: list[NodeInfo]
    active_jobs: int
    pending_join_requests: int


class JoinRequest(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    hostname: str
    ip: str
    hardware_info: dict                  # GPU, CPU, RAM, OS
    requested_at: datetime = Field(default_factory=datetime.utcnow)
    status: Literal["pending", "approved", "rejected"] = "pending"


class JoinApproval(BaseModel):
    install_path: str = "C:/LonginSanctuary"
    install_comfyui: bool = True
    install_ollama: bool = True


class ModelLoadRequest(BaseModel):
    model: str
    service: Literal["ollama", "lmstudio"]
