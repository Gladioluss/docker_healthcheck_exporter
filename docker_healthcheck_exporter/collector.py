from __future__ import annotations

import asyncio
from dataclasses import dataclass
from enum import IntEnum

import aiodocker


class ServiceStatus(IntEnum):
    CRIT = -2  # not running / unreachable
    FAIL = -1  # unknown/failed
    UNHEALTHY = 0  # running but unhealthy
    RUNNING = 1  # running without healthcheck
    HEALTHY = 2  # healthy


@dataclass(frozen=True)
class ContainerStatus:
    name: str
    status: int
    status_text: str
    container_id: str
    image: str
    compose_project: str
    compose_service: str


def _is_ignored(name: str, ignore_list: set[str]) -> bool:
    if "IGNORE_ALL" in ignore_list:
        return True
    return name in ignore_list


def _parse_include_label(expr: str | None) -> tuple[str | None, str | None]:
    if not expr:
        return None, None
    if "=" in expr:
        k, v = expr.split("=", 1)
        return k.strip() or None, v.strip() or None
    return expr.strip() or None, None


class DockerCollector:
    def __init__(
        self,
        ignore_list: set[str],
        include_label: str | None,
        max_concurrency: int = 20,
    ):
        self.ignore_list = ignore_list
        self.include_label_key, self.include_label_value = _parse_include_label(include_label)
        self.max_concurrency = max(1, max_concurrency)
        self.docker: aiodocker.Docker | None = None

    async def start(self) -> None:
        self.docker = aiodocker.Docker()

    async def stop(self) -> None:
        if self.docker is not None:
            await self.docker.close()
            self.docker = None

    def _label_match(self, labels: dict) -> bool:
        if not self.include_label_key:
            return True
        if self.include_label_key not in labels:
            return False
        if self.include_label_value is None:
            return True
        return str(labels.get(self.include_label_key)) == self.include_label_value

    async def collect(self) -> dict[str, ContainerStatus]:
        if self.docker is None:
            raise RuntimeError("DockerCollector not started")

        containers = await self.docker.containers.list(all=True)

        sem = asyncio.Semaphore(self.max_concurrency)

        async def _one(c) -> ContainerStatus | None:
            async with sem:
                info = await c.show()

            name = (info.get("Name") or "").lstrip("/")
            if not name or _is_ignored(name, self.ignore_list):
                return None

            config = info.get("Config", {}) or {}
            labels = config.get("Labels", {}) or {}
            if not self._label_match(labels):
                return None

            state = info.get("State", {}) or {}
            status = state.get("Status", "")  # running/exited/restarting/paused...
            exit_code = state.get("ExitCode")
            running = bool(state.get("Running", False))
            health = (state.get("Health", {}) or {}).get("Status")

            if status == "exited" and exit_code == 0:
                return None

            if not running:
                st = ServiceStatus.CRIT
            elif health is None:
                st = ServiceStatus.RUNNING
            elif health == "healthy":
                st = ServiceStatus.HEALTHY
            elif health == "unhealthy":
                st = ServiceStatus.UNHEALTHY
            else:
                st = ServiceStatus.FAIL

            cid = (info.get("Id") or "")[:12]
            image = str(config.get("Image") or "")
            compose_project = str(labels.get("com.docker.compose.project") or "")
            compose_service = str(labels.get("com.docker.compose.service") or "")

            return ContainerStatus(
                name=name,
                status=int(st),
                status_text=st.name,
                container_id=cid,
                image=image,
                compose_project=compose_project,
                compose_service=compose_service,
            )

        results = await asyncio.gather(*(_one(c) for c in containers), return_exceptions=False)
        out: dict[str, ContainerStatus] = {}
        for item in results:
            if item is None:
                continue
            out[item.name] = item
        return out
