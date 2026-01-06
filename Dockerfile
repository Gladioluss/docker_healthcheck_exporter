FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    LISTEN=0.0.0.0:9102

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md LICENSE* /app/
COPY docker_healthcheck_exporter /app/docker_healthcheck_exporter

RUN pip install --upgrade pip && \
    pip install .

EXPOSE 9102

HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:9102/health').read()"

CMD ["docker-healthcheck-exporter"]
