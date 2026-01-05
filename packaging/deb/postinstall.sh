#!/usr/bin/env bash
set -euo pipefail

# user
if ! id -u healthcheck-exporter >/dev/null 2>&1; then
  useradd --system --no-create-home --shell /usr/sbin/nologin healthcheck-exporter
fi

# docker group may not exist on minimal systems
if ! getent group docker >/dev/null 2>&1; then
  groupadd docker || true
fi

usermod -aG docker healthcheck-exporter || true

install -d -o healthcheck-exporter -g healthcheck-exporter /var/lib/docker-healthcheck-exporter

systemctl daemon-reload || true
systemctl enable --now docker-healthcheck-exporter.service || true
