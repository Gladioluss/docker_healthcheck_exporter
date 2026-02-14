FROM python:3.14-slim AS builder

ARG VERSION=dev
ARG VCS_REF=unknown
ARG BUILD_DATE=unknown

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential \
      ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY docker_healthcheck_exporter ./docker_healthcheck_exporter

RUN pip install --upgrade pip && \
    pip install . --prefix=/install


FROM python:3.14-slim AS runtime

ARG VERSION=dev
ARG VCS_REF=unknown
ARG BUILD_DATE=unknown

LABEL org.opencontainers.image.title="docker-healthcheck-exporter" \
      org.opencontainers.image.description="Prometheus exporter for Docker container healthchecks" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.source="https://github.com/Gladioluss/docker_healthcheck_exporter"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    LISTEN=0.0.0.0:9102 \
    REFRESH_INTERVAL_SECONDS=5 \
    SERVICES_IGNORE_LIST=vmagent \
    MAX_CONCURRENCY=20

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /usr/local

EXPOSE 9102

HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:9102/health')"

ENTRYPOINT ["docker-healthcheck-exporter"]
