# Docker Healthcheck Exporter

**A fast, secure Prometheus exporter for Docker container healthchecks**  
Debian/Ubuntu `.deb` • systemd service • low-overhead snapshot collector • production-ready

[![Release](https://img.shields.io/github/v/release/Gladioluss/docker_healthcheck_exporter?sort=semver)](https://github.com/Gladioluss/docker_healthcheck_exporter/releases)
[![CI](https://img.shields.io/github/actions/workflow/status/Gladioluss/docker_healthcheck_exporter/release.yml?branch=main)](https://github.com/Gladioluss/docker_healthcheck_exporter/actions)
[![License](https://img.shields.io/github/license/Gladioluss/docker_healthcheck_exporter)](LICENSE)

> Python package: `docker_healthcheck_exporter`  
> CLI / deb / service: `docker-healthcheck-exporter`

---

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

Replace `<ORG>` and `<REPO>`:

```bash
VERSION="x.y.z"
ARCH="amd64"

curl -fsSL -o /tmp/dhe.deb \
  "https://github.com/Gladioluss/docker_healthcheck_exporter/releases/download/v${VERSION}/docker-healthcheck-exporter_${VERSION}_${ARCH}.deb" \
  && sudo apt install -y /tmp/dhe.deb
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

# Optional: override instance label value
# INSTANCE_NAME=prod-node-01
```

Apply changes:

```bash
sudo systemctl restart docker-healthcheck-exporter
```

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
- uploads artifacts to **GitHub Release**

---

## Roadmap

- [ ] Grafana dashboard JSON
- [ ] Example Prometheus alert rules
- [ ] Regex / glob ignore patterns
- [ ] Remote Docker hosts (`DOCKER_HOST`)
- [ ] `--version` flag
- [ ] Apt repository (GitHub Pages)
- [ ] Docker image / GHCR publish
- [ ] Kubernetes DaemonSet

---

## Contributing

Open-source friendly ❤️

- Issues: bug reports, feature requests, questions
- PRs: small, focused changes are preferred
- Please keep backward compatibility when possible

---

## License

MIT © Gladioluss
