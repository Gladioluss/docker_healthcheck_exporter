from __future__ import annotations

import asyncio
import time
from types import SimpleNamespace

import pytest

import docker_healthcheck_exporter.app as app_module
from docker_healthcheck_exporter.collector import ContainerStatus


class DummyCollector:
    def __init__(self, snapshots, delay: float = 0.0) -> None:
        self._snapshots = list(snapshots)
        self._delay = delay
        self.started = False
        self.stopped = False

    async def start(self) -> None:
        self.started = True

    async def stop(self) -> None:
        self.stopped = True

    async def collect(self):
        if self._delay:
            await asyncio.sleep(self._delay)
        if not self._snapshots:
            raise RuntimeError("boom")
        return self._snapshots.pop(0)


def _make_state(monkeypatch: pytest.MonkeyPatch, collector: DummyCollector):
    settings = SimpleNamespace(
        refresh_interval_seconds=0.01,
        services_ignore_list=set(),
        include_label=None,
        max_concurrency=1,
        instance_name="test",
    )
    monkeypatch.setattr(app_module, "load_settings", lambda: settings)
    monkeypatch.setattr(app_module, "DockerCollector", lambda **kwargs: collector)
    return app_module.ExporterState()


@pytest.mark.asyncio
async def test_exporter_state_success_cycle(monkeypatch: pytest.MonkeyPatch) -> None:
    snapshot = {
        "svc": ContainerStatus(
            name="svc",
            status=2,
            status_text="HEALTHY",
            container_id="abc",
            image="img",
            compose_project="p",
            compose_service="s",
        )
    }
    collector = DummyCollector([snapshot])
    state = _make_state(monkeypatch, collector)

    await state.start()
    await asyncio.sleep(0.03)
    try:
        await state.stop()
    except asyncio.CancelledError:
        pass

    assert collector.started is True
    assert collector.stopped is True
    assert state.exporter_up == 1
    assert state.snapshot == snapshot
    assert state.last_ok_ts > 0.0
    assert state.refresh_errors_total == 0
    assert state.refresh_duration_seconds >= 0.0


@pytest.mark.asyncio
async def test_exporter_state_error_cycle(monkeypatch: pytest.MonkeyPatch) -> None:
    collector = DummyCollector([])
    state = _make_state(monkeypatch, collector)

    await state.start()
    await asyncio.sleep(0.03)
    try:
        await state.stop()
    except asyncio.CancelledError:
        pass

    assert state.exporter_up == 0
    assert state.refresh_errors_total >= 1


@pytest.mark.asyncio
async def test_lifespan_calls_start_stop(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    async def fake_start() -> None:
        calls.append("start")

    async def fake_stop() -> None:
        calls.append("stop")

    monkeypatch.setattr(app_module.state, "start", fake_start)
    monkeypatch.setattr(app_module.state, "stop", fake_stop)

    async with app_module.lifespan(app_module.app):
        pass

    assert calls == ["start", "stop"]


def test_metrics_text_age(monkeypatch: pytest.MonkeyPatch) -> None:
    state = _make_state(monkeypatch, DummyCollector([]))
    state.last_ok_ts = time.time()
    state.snapshot = {}
    text = state.metrics_text()
    assert "docker_healthcheck_exporter_snapshot_age_seconds" in text
