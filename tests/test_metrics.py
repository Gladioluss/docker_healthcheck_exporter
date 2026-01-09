from __future__ import annotations

from docker_healthcheck_exporter.collector import ContainerStatus
from docker_healthcheck_exporter.metrics import _esc, render_metrics


def test_escape() -> None:
    assert _esc('a"b') == 'a\\"b'
    assert _esc("a\\b") == "a\\\\b"
    assert _esc("a\nb") == "a\\nb"


def test_render_metrics() -> None:
    snapshot = {
        "web": ContainerStatus(
            name="web",
            status=2,
            status_text="HEALTHY",
            container_id="abc123",
            image="img:latest",
            compose_project="proj",
            compose_service="svc",
        )
    }
    text = render_metrics(
        instance_name='host"name',
        snapshot=snapshot,
        exporter_up=1,
        refresh_errors_total=2,
        refresh_duration_seconds=0.5,
        snapshot_age_seconds=1.5,
    )

    assert 'docker_healthcheck_exporter_up{instance="host\\"name"} 1' in text
    assert "docker_healthcheck_exporter_refresh_errors_total" in text
    assert "docker_healthcheck_exporter_refresh_duration_seconds" in text
    assert "docker_healthcheck_exporter_snapshot_age_seconds" in text
    assert 'name="web"' in text
    assert 'status_text="HEALTHY"' in text
