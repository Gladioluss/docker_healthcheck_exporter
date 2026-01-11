# Docker Healthcheck Exporter

**A fast, secure Prometheus exporter for Docker container healthchecks**  
Debian/Ubuntu `.deb` • systemd service • low-overhead snapshot collector • production-ready

[![Release](https://img.shields.io/github/v/release/Gladioluss/docker_healthcheck_exporter?sort=semver)](https://github.com/Gladioluss/docker_healthcheck_exporter/releases)
[![CI](https://img.shields.io/github/actions/workflow/status/Gladioluss/docker_healthcheck_exporter/ci.yml?branch=main)](https://github.com/Gladioluss/docker_healthcheck_exporter/actions)
[![Release](https://img.shields.io/github/actions/workflow/status/Gladioluss/docker_healthcheck_exporter/release.yml?label=release)](https://github.com/Gladioluss/docker_healthcheck_exporter/actions)
[![License](https://img.shields.io/github/license/Gladioluss/docker_healthcheck_exporter)](LICENSE)

> Python package: `docker_healthcheck_exporter`  
> CLI / deb / service: `docker-healthcheck-exporter`

---

## Project status

- Stable for production usage
- Actively maintained
- Backward compatibility: best effort for minor releases

## Why this exists

Prometheus scrapes exporters often. Many Docker exporters **inspect containers on every scrape**, which can be:

- noisy on the Docker API,
- slow under load,
- flaky when Docker is busy.

**Docker Healthcheck Exporter** runs a **background refresh loop** and exposes a **cached snapshot** at `/metrics`.

That means:

- stable scrape latency,
- predictable Docker API usage,
- better production behavior.

---

## Features

- ✅ **Accurate Docker health states**
  - running without healthcheck vs healthy vs unhealthy vs not running
  - skips one-shot containers that exited with code `0`
- ⚡ **Low overhead**
  - refresh interval is configurable
  - `/metrics` is instant (snapshot-based)
- 🔐 **Secure by default**
  - dedicated non-root user
  - hardened systemd unit
- 📦 **Easy installation**
  - Debian/Ubuntu `.deb` package with systemd service
  - upgrades preserve config
- 🎯 **Filtering**
  - ignore container names
  - include only containers with a label (great for shared hosts)
- 🧠 **Exporter self-metrics**
  - `up`, refresh errors, refresh duration, snapshot age
- 🧩 **Compose-friendly**
  - exposes `compose_project` and `compose_service` labels if available

---

## Requirements

- Linux host with **Docker Engine**
- Access to the Docker socket:
  - default: `/var/run/docker.sock`
  - exporter user must be in the `docker` group (see troubleshooting)
  - for remote Docker: set `DOCKER_HOST`, `DOCKER_TLS_VERIFY`, `DOCKER_CERT_PATH`

---

## Quickstart (Debian/Ubuntu)

### Install from a local `.deb`

Download the latest `.deb` from **Releases**, then install:

```bash
sudo apt install -y ./docker-healthcheck-exporter_x.y.z_amd64.deb
```

### Verify the service

```bash
systemctl status docker-healthcheck-exporter --no-pager
```

### Verify metrics

```bash
curl -fsSL localhost:9102/metrics | head
```

---

## Install from GitHub Release (one-liner)

```bash
VERSION="x.y.z"
ARCH="amd64"

curl -fsSL -o /tmp/dhe.deb \
  "https://github.com/Gladioluss/docker_healthcheck_exporter/releases/download/v${VERSION}/docker-healthcheck-exporter_${VERSION}_${ARCH}.deb" \
  && sudo apt install -y /tmp/dhe.deb
```

## Run with Docker

> Image is published to GHCR: `ghcr.io/Gladioluss/docker_healthcheck_exporter`

### Quick run

```bash
docker run -d --name docker-healthcheck-exporter \
  -p 9102:9102 \
  -v /var/run/docker.sock:/var/run/docker.sock:ro \
  -e LISTEN=0.0.0.0:9102 \
  ghcr.io/Gladioluss/docker_healthcheck_exporter:latest
```

## Verify:

```bash
curl -s localhost:9102/metrics | head
```

---

## Prometheus config

```yaml
scrape_configs:
  - job_name: docker-healthcheck-exporter
    static_configs:
      - targets:
          - "server-ip:9102"
```

---

## Configuration

The exporter is configured via environment variables.

systemd loads environment config from:

```text
/etc/docker-healthcheck-exporter.env
```

Example:

```env
# Where exporter listens
LISTEN=0.0.0.0:9102

# Snapshot refresh interval (seconds)
REFRESH_INTERVAL_SECONDS=5

# Comma-separated list of container names to ignore, or IGNORE_ALL
SERVICES_IGNORE_LIST=vmagent,health-exporter

# Include only containers with this label:
# - "monitor" means key exists
# - "monitor=true" means key equals value
# INCLUDE_LABEL=monitor=true

# Limits parallel Docker inspect calls
MAX_CONCURRENCY=20

# Optional: write metrics to a file for textfile collectors
# METRICS_FILE=/var/lib/node_exporter/textfile_collector/docker_healthcheck_exporter.prom

# Optional: override instance label value
# INSTANCE_NAME=prod-node-01
```

Apply changes:

```bash
sudo systemctl restart docker-healthcheck-exporter
```

---

## Examples

See `examples/README.md` for Docker Compose and Prometheus examples.

---

## Metrics

### Container health metric

```text
docker_container_health_status{
  instance="host01",
  name="api",
  container_id="abc123",
  image="nginx:1.27",
  compose_project="prod",
  compose_service="api",
  status_text="HEALTHY"
} 2
```

Value mapping:

| Value | Meaning |
|------:|---------|
| 2     | healthy |
| 1     | running (no healthcheck configured) |
| 0     | unhealthy |
| -1    | failed / unknown |
| -2    | critical (not running) |

### Exporter self-metrics

| Metric | Type | Description |
|---|---|---|
| `docker_healthcheck_exporter_up` | gauge | exporter can talk to Docker |
| `docker_healthcheck_exporter_refresh_errors_total` | counter | refresh errors count |
| `docker_healthcheck_exporter_refresh_duration_seconds` | gauge | last refresh duration |
| `docker_healthcheck_exporter_snapshot_age_seconds` | gauge | age of current snapshot |

---

## Upgrade / rollback

### Upgrade

```bash
sudo apt install -y ./docker-healthcheck-exporter_0.0.3_amd64.deb
```

Config is preserved.

### Remove

```bash
sudo apt remove -y docker-healthcheck-exporter
```

### Rollback

```bash
sudo apt install -y ./docker-healthcheck-exporter_0.0.2_amd64.deb
```

---

## Security model

Runs as user:

```text
healthcheck-exporter
```

Uses systemd hardening (example):

```ini
NoNewPrivileges=true
PrivateTmp=true
ProtectHome=true
ProtectSystem=strict
StateDirectory=docker-healthcheck-exporter
RuntimeDirectory=docker-healthcheck-exporter
```

Docker access is granted via the `docker` group.

---

## Troubleshooting

### Service fails with `status=226/NAMESPACE`

This usually means required directories do not exist.

Create the directory and fix ownership:

```bash
sudo mkdir -p /var/lib/docker-healthcheck-exporter
sudo chown healthcheck-exporter:healthcheck-exporter /var/lib/docker-healthcheck-exporter
sudo systemctl restart docker-healthcheck-exporter
```

### `docker_healthcheck_exporter_up 0`

Exporter can’t access the Docker socket.

Check socket and user groups:

```bash
ls -l /var/run/docker.sock
id healthcheck-exporter
```

Fix (add user to `docker` group):

```bash
sudo usermod -aG docker healthcheck-exporter
sudo systemctl restart docker-healthcheck-exporter
```

> Note: group changes may require a restart/re-login of the service user session — restarting the systemd service is usually enough.

---

## Development

### Local setup

Install dependencies:

```bash
poetry install
```

Run exporter:

```bash
poetry run docker-healthcheck-exporter
```

Or:

```bash
poetry run python -m docker_healthcheck_exporter
```

### Linting and formatting

```bash
make lint
make format
```

### Tests

```bash
make test
```

Integration tests use the local Docker Engine and will be skipped if Docker
is not available or no suitable local image exists.

### Coverage

CI enforces test coverage. Locally you can run:

```bash
poetry run pytest --cov=docker_healthcheck_exporter --cov-report=term-missing
```

---

## CI/CD (how releases are built)

Releases are built automatically on tag push:

```bash
git tag vX.Y.Z
git push origin vX.Y.Z
```

GitHub Actions pipeline:

- builds a Linux binary using **PyInstaller**
- packages `.deb` via **nfpm**
- builds/pushes Docker image to GHCR
- uploads artifacts to **GitHub Release**

---

## Contributing

See `CONTRIBUTING.md` for the workflow and expectations.

---

## Security

See `SECURITY.md` for reporting vulnerabilities.

---

## Code of Conduct

This project follows the Contributor Covenant. See `CODE_OF_CONDUCT.md`.

---

## Support

For usage questions and support, see `SUPPORT.md`.

---

## License

MIT © Gladioluss
