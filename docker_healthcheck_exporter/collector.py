from __future__ import annotations

import asyncio
from dataclasses import dataclass
from enum import IntEnum

import aiodocker

from docker_healthcheck_exporter.logger import get_logger

logger = get_logger(__name__)


class ServiceStatus(IntEnum):
    CRIT = -2  # not running / unreachable
    FAIL = -1  # unknown/failed
    UNHEALTHY = 0  # running but unhealthy
    RUNNING = 1  # running without healthcheck
    HEALTHY = 2  # healthy


@dataclass(frozen=True)
class ContainerStatus:
    name: str
    status: int
    status_text: str
    container_id: str
    image: str
    compose_project: str
    compose_service: str


def _is_ignored(name: str, ignore_list: set[str]) -> bool:
    """
    Check if a container should be ignored based on its name and the ignore_list.

    If "IGNORE_ALL" is in the ignore_list, all containers are ignored.
    Otherwise, the function checks if the container's name is in the ignore_list.

    Args:
        name (str): The name of the container.
        ignore_list (set[str]): A set of container names to ignore.

    Returns:
        bool: True if the container should be ignored, False otherwise.
    """
    if "IGNORE_ALL" in ignore_list:
        return True
    return name in ignore_list


def _parse_include_label(expr: str | None) -> tuple[str | None, str | None]:
    """
    Parse the include_label expression into a key-value pair.

    If the expression is None, returns (None, None).
    If the expression contains a "=", it is split into a key-value pair.
    Otherwise, the expression is returned as the key and None as the value.

    Args:
        expr (str | None): The include_label expression.

    Returns:
        tuple[str | None, str | None]: A tuple containing the key-value pair.
    """
    if not expr:
        return None, None
    if "=" in expr:
        k, v = expr.split("=", 1)
        return k.strip() or None, v.strip() or None
    return expr.strip() or None, None


class DockerCollector:
    def __init__(
        self,
        ignore_list: set[str],
        include_label: str | None,
        max_concurrency: int = 20,
    ):
        """
        Initializes a DockerCollector instance.

        Args:
            ignore_list (set[str]): A set of container names to ignore.
            include_label (str | None): A label to filter containers by.
            max_concurrency (int, optional): The maximum number of concurrent API requests. Defaults to 20.

        Attributes:
            ignore_list (set[str]): The set of container names to ignore.
            include_label_key (str | None): The key of the label to filter by.
            include_label_value (str | None): The value of the label to filter by.
            max_concurrency (int): The maximum number of concurrent API requests.
            docker (aio.Docker | None): The aiODocker client instance.
        """
        self.ignore_list = ignore_list
        self.include_label_key, self.include_label_value = _parse_include_label(include_label)
        self.max_concurrency = max(1, max_concurrency)
        self.docker: aiodocker.Docker | None = None

    async def start(self) -> None:
        """
        Starts the Docker collector.

        This method initializes the aiODocker client instance.
        The instance is stored in the `docker` attribute.

        :return: None
        """
        logger.info("Starting Docker client")
        self.docker = aiodocker.Docker()

    async def stop(self) -> None:
        """
        Stops the Docker collector.

        This method closes the aiODocker client instance and sets
        the `docker` attribute to None.

        :return: None
        """
        if self.docker is not None:
            logger.info("Stopping Docker client")
            await self.docker.close()
            self.docker = None

    def _label_match(self, labels: dict) -> bool:
        """
        Checks if a container's labels match the configured include label.

        If no include label is configured, this method always returns True.
        If the include label key is not present in the container's labels, this method returns False.
        If the include label value is None, this method returns True if the key is present in the container's labels.
        Otherwise, this method returns True if the value of the key matches the configured include label value.

        :param labels: The container's labels as a dictionary.
        :return: Whether the container's labels match the configured include label.
        """
        if not self.include_label_key:
            return True
        if self.include_label_key not in labels:
            return False
        if self.include_label_value is None:
            return True
        return str(labels.get(self.include_label_key)) == self.include_label_value

    async def collect(self) -> dict[str, ContainerStatus]:
        """
        Collects the health status of all Docker containers.

        This method starts a snapshot refresh loop that runs every
        `REFRESH_INTERVAL_SECONDS` seconds. The loop collects the
        health status of all Docker containers and caches the results.

        The method returns a dictionary with container names as keys and
        `ContainerStatus` instances as values. The dictionary contains
        only containers that match the configured include label.

        If the Docker collector is not started, this method raises a
        `RuntimeError`.

        :return: A dictionary with container names as keys and
            `ContainerStatus` instances as values.
        """
        if self.docker is None:
            raise RuntimeError("DockerCollector not started")

        containers = await self.docker.containers.list(all=True)

        sem = asyncio.Semaphore(self.max_concurrency)

        async def _one(c) -> ContainerStatus | None:
            async with sem:
                info = await c.show()

            name = (info.get("Name") or "").lstrip("/")
            if not name or _is_ignored(name, self.ignore_list):
                return None

            config = info.get("Config", {}) or {}
            labels = config.get("Labels", {}) or {}
            if not self._label_match(labels):
                return None

            state = info.get("State", {}) or {}
            status = state.get("Status", "")  # running/exited/restarting/paused...
            exit_code = state.get("ExitCode")
            running = bool(state.get("Running", False))
            health = (state.get("Health", {}) or {}).get("Status")
            restarting = bool(state.get("Restarting", False))

            if status == "exited" and exit_code == 0:
                return None

            if status == "restarting" or restarting:
                st = ServiceStatus.FAIL
            elif not running:
                st = ServiceStatus.CRIT
            elif health is None:
                st = ServiceStatus.RUNNING
            elif health == "healthy":
                st = ServiceStatus.HEALTHY
            elif health == "unhealthy":
                st = ServiceStatus.UNHEALTHY
            else:
                st = ServiceStatus.FAIL

            cid = (info.get("Id") or "")[:12]
            image = str(config.get("Image") or "")
            compose_project = str(labels.get("com.docker.compose.project") or "")
            compose_service = str(labels.get("com.docker.compose.service") or "")

            return ContainerStatus(
                name=name,
                status=int(st),
                status_text=st.name,
                container_id=cid,
                image=image,
                compose_project=compose_project,
                compose_service=compose_service,
            )

        results = await asyncio.gather(*(_one(c) for c in containers), return_exceptions=False)
        out: dict[str, ContainerStatus] = {}
        for item in results:
            if item is None:
                continue
            out[item.name] = item
        return out
