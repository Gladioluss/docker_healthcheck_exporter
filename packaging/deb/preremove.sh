#!/usr/bin/env bash
set -euo pipefail

systemctl disable --now docker_healthcheck_exporter.service || true
systemctl daemon-reload || true
