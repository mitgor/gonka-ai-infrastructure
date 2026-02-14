"""
Gonka.ai Health Check — monitors vLLM backend status, GPU utilization, and queue depth.

Provides /health endpoint data for the gateway and external monitoring.
Can be used standalone or imported by the gateway.
"""

import asyncio
import time
from dataclasses import dataclass, field
from typing import Optional

import httpx


@dataclass
class GPUInfo:
    index: int
    name: str
    memory_used_mb: float
    memory_total_mb: float
    utilization_percent: float

    @property
    def memory_utilization_percent(self) -> float:
        if self.memory_total_mb == 0:
            return 0.0
        return (self.memory_used_mb / self.memory_total_mb) * 100


@dataclass
class ModelStatus:
    model_name: str
    status: str  # "ready", "loading", "error", "unreachable"
    uptime_seconds: float = 0.0
    pending_requests: int = 0
    active_requests: int = 0
    gpu_info: list[GPUInfo] = field(default_factory=list)
    error: Optional[str] = None
    last_checked: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "model_name": self.model_name,
            "status": self.status,
            "uptime_seconds": self.uptime_seconds,
            "pending_requests": self.pending_requests,
            "active_requests": self.active_requests,
            "gpu_info": [
                {
                    "index": g.index,
                    "name": g.name,
                    "memory_used_mb": round(g.memory_used_mb, 1),
                    "memory_total_mb": round(g.memory_total_mb, 1),
                    "memory_utilization_percent": round(g.memory_utilization_percent, 1),
                    "utilization_percent": round(g.utilization_percent, 1),
                }
                for g in self.gpu_info
            ],
            "error": self.error,
            "last_checked": self.last_checked,
        }


class HealthChecker:
    """Checks vLLM backend health and GPU status."""

    def __init__(self, vllm_base_url: str = "http://localhost:8000"):
        self.vllm_base_url = vllm_base_url.rstrip("/")
        self._start_time = time.time()

    async def check_vllm_health(self) -> bool:
        """Check if vLLM is responding."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.vllm_base_url}/health")
                return resp.status_code == 200
        except (httpx.ConnectError, httpx.TimeoutException):
            return False

    async def get_vllm_models(self) -> list[str]:
        """Get list of models served by vLLM."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.vllm_base_url}/v1/models")
                if resp.status_code == 200:
                    data = resp.json()
                    return [m["id"] for m in data.get("data", [])]
        except (httpx.ConnectError, httpx.TimeoutException):
            pass
        return []

    def get_gpu_info(self) -> list[GPUInfo]:
        """Get GPU utilization via nvidia-smi (if available)."""
        try:
            import subprocess
            result = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=index,name,memory.used,memory.total,utilization.gpu",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode != 0:
                return []

            gpus = []
            for line in result.stdout.strip().split("\n"):
                if not line.strip():
                    continue
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 5:
                    gpus.append(GPUInfo(
                        index=int(parts[0]),
                        name=parts[1],
                        memory_used_mb=float(parts[2]),
                        memory_total_mb=float(parts[3]),
                        utilization_percent=float(parts[4]),
                    ))
            return gpus
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return []

    async def get_status(self, model_name: str = "moonshotai/Kimi-K2.5") -> ModelStatus:
        """Get comprehensive health status."""
        is_healthy = await self.check_vllm_health()

        if not is_healthy:
            return ModelStatus(
                model_name=model_name,
                status="unreachable",
                error="vLLM backend not responding",
            )

        models = await self.get_vllm_models()
        gpu_info = self.get_gpu_info()

        return ModelStatus(
            model_name=model_name,
            status="ready" if models else "loading",
            uptime_seconds=time.time() - self._start_time,
            gpu_info=gpu_info,
        )

    async def get_queue_depth(self) -> dict:
        """Get pending/active request counts from vLLM metrics."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.vllm_base_url}/metrics")
                if resp.status_code == 200:
                    metrics_text = resp.text
                    pending = _parse_metric(metrics_text, "vllm:num_requests_waiting")
                    running = _parse_metric(metrics_text, "vllm:num_requests_running")
                    return {"pending": pending, "active": running}
        except (httpx.ConnectError, httpx.TimeoutException):
            pass
        return {"pending": 0, "active": 0}


def _parse_metric(metrics_text: str, metric_name: str) -> int:
    """Parse a single metric value from Prometheus-format metrics."""
    for line in metrics_text.split("\n"):
        if line.startswith(metric_name) and not line.startswith("#"):
            parts = line.split()
            if len(parts) >= 2:
                try:
                    return int(float(parts[-1]))
                except ValueError:
                    pass
    return 0
