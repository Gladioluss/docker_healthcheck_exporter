from __future__ import annotations

import uvicorn

from docker_healthcheck_exporter.app import app
from docker_healthcheck_exporter.config import load_settings


def main() -> None:
    s = load_settings()
    uvicorn.run(
        app,
        host=s.listen_host,
        port=s.listen_port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
