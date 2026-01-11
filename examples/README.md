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

## Docker Compose (textfile output)

This variant writes metrics to a local file for textfile collectors:

```bash
mkdir -p examples/textfile
docker compose -f examples/docker-compose.textfile.yml up -d
```

The metrics file will be written to `examples/textfile/docker_healthcheck_exporter.prom`.

## Prometheus config

Example scrape config is in `examples/prometheus.yml`.

## Textfile collector output

To write metrics to a file for Node Exporter textfile collector:

```bash
export METRICS_FILE=/var/lib/node_exporter/textfile_collector/docker_healthcheck_exporter.prom
poetry run docker-healthcheck-exporter
```
