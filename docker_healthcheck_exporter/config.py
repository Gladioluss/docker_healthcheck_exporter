from __future__ import annotations

import os
from dataclasses import dataclass


def _env(name: str, default: str | None = None) -> str | None:
    v = os.getenv(name)
    if v is None:
        return default
    v = v.strip()
    return v if v else default


def _parse_set_csv(value: str | None, default: set[str]) -> set[str]:
    if not value:
        return set(default)
    raw = value.strip()
    if raw == "IGNORE_ALL":
        return {"IGNORE_ALL"}
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    return set(default) | set(parts)


@dataclass(frozen=True)
class Settings:
    # Network
    listen_host: str
    listen_port: int

    # Identity
    instance_name: str

    # Collector
    refresh_interval_seconds: float
    services_ignore_list: set[str]
    include_label: str | None
    max_concurrency: int

    # Docker
    docker_host: str | None
    docker_tls_verify: str | None
    docker_cert_path: str | None


def load_settings() -> Settings:
    listen = _env("LISTEN", "0.0.0.0:9102")
    if ":" not in listen:
        raise ValueError("LISTEN must be like 0.0.0.0:9102")
    host, port_s = listen.rsplit(":", 1)
    port = int(port_s)

    instance = _env("INSTANCE_NAME") or _env("FQDN") or os.uname().nodename

    default_ignore = {"vmagent", "health-exporter"}
    ignore = _parse_set_csv(_env("SERVICES_IGNORE_LIST"), default_ignore)

    refresh = float(_env("REFRESH_INTERVAL_SECONDS", "5"))
    include_label = _env("INCLUDE_LABEL")
    max_concurrency = int(_env("MAX_CONCURRENCY", "20"))

    return Settings(
        listen_host=host,
        listen_port=port,
        instance_name=instance,
        refresh_interval_seconds=refresh,
        services_ignore_list=ignore,
        include_label=include_label,
        max_concurrency=max_concurrency,
        docker_host=_env("DOCKER_HOST"),
        docker_tls_verify=_env("DOCKER_TLS_VERIFY"),
        docker_cert_path=_env("DOCKER_CERT_PATH"),
    )
