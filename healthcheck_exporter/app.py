from __future__ import annotations

import asyncio
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse

from healthcheck_exporter.collector import DockerCollector, ContainerStatus
from healthcheck_exporter.config import load_settings
from healthcheck_exporter.metrics import render_metrics


class ExporterState:
    def __init__(self) -> None:
        self.settings = load_settings()
        self.collector = DockerCollector(
            ignore_list=self.settings.services_ignore_list,
            include_label=self.settings.include_label,
            max_concurrency=self.settings.max_concurrency,
        )

        self.snapshot: dict[str, ContainerStatus] = {}
        self.last_ok_ts: float = 0.0

        self.exporter_up: int = 0
        self.refresh_errors_total: int = 0
        self.refresh_duration_seconds: float = 0.0

        self._stop = asyncio.Event()
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        await self.collector.start()
        self._task = asyncio.create_task(self._loop(), name="docker-refresh-loop")

    async def stop(self) -> None:
        self._stop.set()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except Exception:
                pass
        await self.collector.stop()

    async def _loop(self) -> None:
        interval = max(1.0, self.settings.refresh_interval_seconds)
        while not self._stop.is_set():
            t0 = time.perf_counter()
            try:
                snap = await self.collector.collect()
                self.snapshot = snap
                self.last_ok_ts = time.time()
                self.exporter_up = 1
            except Exception:
                self.refresh_errors_total += 1
                self.exporter_up = 0
            finally:
                self.refresh_duration_seconds = max(0.0, time.perf_counter() - t0)

            try:
                await asyncio.wait_for(self._stop.wait(), timeout=interval)
            except asyncio.TimeoutError:
                pass

    def metrics_text(self) -> str:
        now = time.time()
        age = (now - self.last_ok_ts) if self.last_ok_ts else float("inf")
        return render_metrics(
            instance_name=self.settings.instance_name,
            snapshot=self.snapshot,
            exporter_up=self.exporter_up,
            refresh_errors_total=self.refresh_errors_total,
            refresh_duration_seconds=self.refresh_duration_seconds,
            snapshot_age_seconds=age if age != float("inf") else 0.0,
        )


state = ExporterState()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await state.start()
    yield
    await state.stop()


app = FastAPI(lifespan=lifespan)


@app.get("/metrics", response_class=PlainTextResponse)
async def metrics():
    return state.metrics_text()


@app.get("/health", response_class=PlainTextResponse)
async def health():
    # health of exporter itself (not services)
    return "ok\n"
