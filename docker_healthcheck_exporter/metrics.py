from __future__ import annotations

from collections.abc import Mapping

from docker_healthcheck_exporter.collector import ContainerStatus


def _esc(v: str) -> str:
    return v.replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')


def render_metrics(
    instance_name: str,
    snapshot: Mapping[str, ContainerStatus],
    exporter_up: int,
    refresh_errors_total: int,
    refresh_duration_seconds: float,
    snapshot_age_seconds: float,
) -> str:
    lines: list[str] = []

    lines.append(
        "# HELP docker_healthcheck_exporter_up Exporter is running and can talk to Docker (1/0)."
    )
    lines.append("# TYPE docker_healthcheck_exporter_up gauge")
    lines.append(
        f'docker_healthcheck_exporter_up{{instance="{_esc(instance_name)}"}} {exporter_up}'
    )

    lines.append(
        "# HELP docker_healthcheck_exporter_refresh_errors_total Number of Docker refresh errors."
    )
    lines.append("# TYPE docker_healthcheck_exporter_refresh_errors_total counter")
    lines.append(
        f'docker_healthcheck_exporter_refresh_errors_total{{instance="{_esc(instance_name)}"}} {refresh_errors_total}'
    )

    lines.append(
        "# HELP docker_healthcheck_exporter_refresh_duration_seconds Last refresh duration in seconds."
    )
    lines.append("# TYPE docker_healthcheck_exporter_refresh_duration_seconds gauge")
    lines.append(
        f'docker_healthcheck_exporter_refresh_duration_seconds{{instance="{_esc(instance_name)}"}} {refresh_duration_seconds}'
    )

    lines.append(
        "# HELP docker_healthcheck_exporter_snapshot_age_seconds Age of the last successful snapshot in seconds."
    )
    lines.append("# TYPE docker_healthcheck_exporter_snapshot_age_seconds gauge")
    lines.append(
        f'docker_healthcheck_exporter_snapshot_age_seconds{{instance="{_esc(instance_name)}"}} {snapshot_age_seconds}'
    )

    lines.append(
        "# HELP docker_container_health_status Container health status (-2 crit, -1 fail, 0 unhealthy, 1 running(no healthcheck), 2 healthy)."
    )
    lines.append("# TYPE docker_container_health_status gauge")

    for name, st in snapshot.items():
        lines.append(
            "docker_container_health_status{"
            f'instance="{_esc(instance_name)}",'
            f'name="{_esc(name)}",'
            f'container_id="{_esc(st.container_id)}",'
            f'image="{_esc(st.image)}",'
            f'compose_project="{_esc(st.compose_project)}",'
            f'compose_service="{_esc(st.compose_service)}",'
            f'status_text="{_esc(st.status_text)}"'
            f"}} {st.status}"
        )

    return "\n".join(lines) + "\n"
