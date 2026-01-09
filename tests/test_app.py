from __future__ import annotations

import pytest

import docker_healthcheck_exporter.app as app_module


class DummyState:
    def __init__(self, text: str) -> None:
        self._text = text

    def metrics_text(self) -> str:
        return self._text


@pytest.mark.asyncio
async def test_metrics_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    dummy = DummyState("metrics-ok")
    monkeypatch.setattr(app_module, "state", dummy)

    result = await app_module.metrics()
    assert result == "metrics-ok"


@pytest.mark.asyncio
async def test_health_endpoint() -> None:
    result = await app_module.health()
    assert result == "{'status': 'ok'}"
