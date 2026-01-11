from __future__ import annotations

import uvicorn

from docker_healthcheck_exporter.app import app
from docker_healthcheck_exporter.config import load_settings
from docker_healthcheck_exporter.logger import configure_logging, get_logger

logger = get_logger(__name__)


def main() -> None:
    configure_logging()
    s = load_settings()
    logger.info(
        f"Starting server on {s.listen_host}:{s.listen_port} (metrics_file={s.metrics_file})"
    )
    uvicorn.run(
        app,
        host=s.listen_host,
        port=s.listen_port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
