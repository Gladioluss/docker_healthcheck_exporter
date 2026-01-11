from __future__ import annotations

import pytest

from docker_healthcheck_exporter.collector import (
    ContainerStatus,
    DockerCollector,
    ServiceStatus,
    _is_ignored,
    _parse_include_label,
)


class FakeContainer:
    def __init__(self, info: dict) -> None:
        self._info = info

    async def show(self) -> dict:
        return self._info


class FakeContainers:
    def __init__(self, items: list[FakeContainer]) -> None:
        self._items = items

    async def list(self, all: bool = True) -> list[FakeContainer]:
        return self._items


class FakeDocker:
    def __init__(self, items: list[FakeContainer]) -> None:
        self.containers = FakeContainers(items)


def test_is_ignored() -> None:
    assert _is_ignored("anything", {"IGNORE_ALL"}) is True
    assert _is_ignored("name", {"name"}) is True
    assert _is_ignored("name", {"other"}) is False


def test_parse_include_label() -> None:
    assert _parse_include_label(None) == (None, None)
    assert _parse_include_label("  ") == (None, None)
    assert _parse_include_label("monitor") == ("monitor", None)
    assert _parse_include_label("monitor=true") == ("monitor", "true")
    assert _parse_include_label("monitor=") == ("monitor", None)


@pytest.mark.asyncio
async def test_collect_maps_statuses_and_filters() -> None:
    infos = [
        {
            "Id": "healthy1234567890",
            "Name": "/healthy",
            "Config": {"Image": "img", "Labels": {"monitor": "true"}},
            "State": {"Status": "running", "Running": True, "Health": {"Status": "healthy"}},
        },
        {
            "Id": "unhealthy123456",
            "Name": "/unhealthy",
            "Config": {"Image": "img", "Labels": {"monitor": "true"}},
            "State": {"Status": "running", "Running": True, "Health": {"Status": "unhealthy"}},
        },
        {
            "Id": "nohealth123456",
            "Name": "/nohealth",
            "Config": {"Image": "img", "Labels": {"monitor": "true"}},
            "State": {"Status": "running", "Running": True},
        },
        {
            "Id": "notrunning12345",
            "Name": "/notrunning",
            "Config": {"Image": "img", "Labels": {"monitor": "true"}},
            "State": {"Status": "exited", "Running": False, "ExitCode": 1},
        },
        {
            "Id": "unknownhealth12",
            "Name": "/unknownhealth",
            "Config": {"Image": "img", "Labels": {"monitor": "true"}},
            "State": {"Status": "running", "Running": True, "Health": {"Status": "starting"}},
        },
        {
            "Id": "restarting1234",
            "Name": "/restarting",
            "Config": {"Image": "img", "Labels": {"monitor": "true"}},
            "State": {"Status": "restarting", "Running": True},
        },
        {
            "Id": "oneshot1234567",
            "Name": "/oneshot",
            "Config": {"Image": "img", "Labels": {"monitor": "true"}},
            "State": {"Status": "exited", "Running": False, "ExitCode": 0},
        },
        {
            "Id": "ignored1234567",
            "Name": "/ignored",
            "Config": {"Image": "img", "Labels": {"monitor": "true"}},
            "State": {"Status": "running", "Running": True},
        },
        {
            "Id": "labelskip12345",
            "Name": "/labelskip",
            "Config": {"Image": "img", "Labels": {"monitor": "false"}},
            "State": {"Status": "running", "Running": True},
        },
    ]

    collector = DockerCollector(
        ignore_list={"ignored"}, include_label="monitor=true", max_concurrency=2
    )
    collector.docker = FakeDocker([FakeContainer(info) for info in infos])

    snap = await collector.collect()

    assert set(snap.keys()) == {
        "healthy",
        "unhealthy",
        "nohealth",
        "notrunning",
        "unknownhealth",
        "restarting",
    }

    assert snap["healthy"].status == int(ServiceStatus.HEALTHY)
    assert snap["unhealthy"].status == int(ServiceStatus.UNHEALTHY)
    assert snap["nohealth"].status == int(ServiceStatus.RUNNING)
    assert snap["notrunning"].status == int(ServiceStatus.CRIT)
    assert snap["unknownhealth"].status == int(ServiceStatus.FAIL)
    assert snap["restarting"].status == int(ServiceStatus.FAIL)
    assert isinstance(snap["healthy"], ContainerStatus)


@pytest.mark.asyncio
async def test_collect_requires_start() -> None:
    collector = DockerCollector(ignore_list=set(), include_label=None, max_concurrency=1)
    with pytest.raises(RuntimeError):
        await collector.collect()


def test_label_match() -> None:
    collector = DockerCollector(ignore_list=set(), include_label="monitor=true", max_concurrency=1)
    assert collector._label_match({"monitor": "true"}) is True
    assert collector._label_match({"monitor": "false"}) is False
    assert collector._label_match({"other": "true"}) is False

    collector_any = DockerCollector(ignore_list=set(), include_label="monitor", max_concurrency=1)
    assert collector_any._label_match({"monitor": "anything"}) is True
    assert collector_any._label_match({"other": "x"}) is False

    collector_none = DockerCollector(ignore_list=set(), include_label=None, max_concurrency=1)
    assert collector_none._label_match({}) is True
