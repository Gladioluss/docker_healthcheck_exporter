FROM python:3.14-slim AS builder

ARG POETRY_VERSION=2.5.1

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential \
      ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/poetry && \
    /opt/poetry/bin/pip install --no-cache-dir "poetry==${POETRY_VERSION}" && \
    python -m venv /opt/venv

ENV VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:/opt/poetry/bin:$PATH" \
    POETRY_NO_INTERACTION=1 \
    POETRY_INSTALLER_RE_RESOLVE=false

COPY pyproject.toml poetry.lock ./
RUN poetry sync --only main --no-root

COPY README.md LICENSE ./
COPY docker_healthcheck_exporter ./docker_healthcheck_exporter
RUN poetry check --lock && poetry build --format wheel && pip install --no-deps dist/*.whl


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
    PATH="/opt/venv/bin:$PATH" \
    LISTEN=0.0.0.0:9102 \
    REFRESH_INTERVAL_SECONDS=5 \
    SERVICES_IGNORE_LIST=vmagent \
    MAX_CONCURRENCY=20

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/venv /opt/venv

EXPOSE 9102

HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:9102/health')"

ENTRYPOINT ["docker-healthcheck-exporter"]
