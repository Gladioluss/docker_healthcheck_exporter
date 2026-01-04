#!/usr/bin/env bash
set -euo pipefail
systemctl disable --now docker-healthcheck-exporter.service || true
systemctl daemon-reload || true
