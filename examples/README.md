# Examples

This directory contains minimal, runnable examples.

## Docker Compose (basic)

Run the exporter and a couple of sample containers:

```bash
docker compose -f examples/docker-compose.yml up -d
```

Check metrics:

```bash
curl -s localhost:9102/metrics | head
```

## Docker Compose (label filter)

This variant shows `INCLUDE_LABEL=monitor=true` filtering:

```bash
docker compose -f examples/docker-compose.labels.yml up -d
```

Only containers with the `monitor=true` label will appear in metrics.

## Prometheus config

Example scrape config is in `examples/prometheus.yml`.
