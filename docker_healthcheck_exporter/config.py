from __future__ import annotations

import os
from dataclasses import dataclass


def _env(name: str, default: str | None = None) -> str | None:
    """
    Retrieves an environment variable.

    If the variable does not exist, returns the default value.
    If the variable exists but is empty (after stripping), returns the default value.
    If the variable exists and is not empty, returns its value.

    :param name: Name of the environment variable
    :param default: Default value to return if the variable does not exist or is empty
    :return: Value of the environment variable, or the default value
    :rtype: str | None
    """
    v = os.getenv(name)
    if v is None:
        return default
    v = v.strip()
    return v if v else default


def _parse_set_csv(value: str | None, default: set[str]) -> set[str]:
    """
    Parses a set of values from a comma-separated string.

    If the input value is None or empty (after stripping), returns the default set.

    If the input value is "IGNORE_ALL", returns a set containing only that string.

    Otherwise, splits the input value on commas, strips each part, and returns a set containing the default values and the parsed parts.

    :param value: Input value to parse
    :param default: Default set to return if the input value is None or empty
    :return: Parsed set
    :rtype: set[str]
    """
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
    metrics_file: str | None

    # Docker
    docker_host: str | None
    docker_tls_verify: str | None
    docker_cert_path: str | None


def load_settings() -> Settings:
    """
    Loads settings from environment variables.

    Environment variables used:

    - LISTEN: host and port to listen on, like 0.0.0.0:9102
    - INSTANCE_NAME: name of the instance, defaults to FQDN or hostname
    - SERVICES_IGNORE_LIST: comma-separated list of services to ignore, defaults to vmagent and health-exporter
    - REFRESH_INTERVAL_SECONDS: interval between snapshots in seconds, defaults to 5
    - INCLUDE_LABEL: label to include in metrics, defaults to None
    - MAX_CONCURRENCY: maximum number of concurrent snapshot collection, defaults to 20
    - METRICS_FILE: path to write metrics to, defaults to None
    - DOCKER_HOST: optional Docker host to connect to
    - DOCKER_TLS_VERIFY: optional Docker TLS verification setting
    - DOCKER_CERT_PATH: optional Docker certificate path

    Returns a Settings object with the loaded values.
    """
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
    metrics_file = _env("METRICS_FILE")

    return Settings(
        listen_host=host,
        listen_port=port,
        instance_name=instance,
        refresh_interval_seconds=refresh,
        services_ignore_list=ignore,
        include_label=include_label,
        max_concurrency=max_concurrency,
        metrics_file=metrics_file,
        docker_host=_env("DOCKER_HOST"),
        docker_tls_verify=_env("DOCKER_TLS_VERIFY"),
        docker_cert_path=_env("DOCKER_CERT_PATH"),
    )
