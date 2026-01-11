from __future__ import annotations

import os
import subprocess
import time

import pytest

from docker_healthcheck_exporter.collector import DockerCollector


def _docker_available() -> bool:
    if subprocess.run(["which", "docker"], capture_output=True, text=True).returncode != 0:
        return False
    try:
        subprocess.run(
            ["docker", "version"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
        return True
    except Exception:
        return False


def _pick_local_image() -> str | None:
    candidates = ["busybox:latest", "alpine:latest", "ubuntu:latest"]
    for image in candidates:
        if (
            subprocess.run(["docker", "image", "inspect", image], capture_output=True).returncode
            == 0
        ):
            return image
    return None


def _wait_for_health(container_name: str, timeout_s: float = 8.0) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        result = subprocess.run(
            ["docker", "inspect", "--format", "{{.State.Health.Status}}", container_name],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            time.sleep(0.2)
            continue
        status = result.stdout.strip()
        if status in {"healthy", "unhealthy"}:
            return
        time.sleep(0.2)


def _wait_for_exit(container_name: str, timeout_s: float = 8.0) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        result = subprocess.run(
            ["docker", "inspect", "--format", "{{.State.Status}}", container_name],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            time.sleep(0.2)
            continue
        status = result.stdout.strip()
        if status == "exited":
            return
        time.sleep(0.2)


def _wait_for_running(container_name: str, timeout_s: float = 8.0) -> bool:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        result = subprocess.run(
            ["docker", "inspect", "--format", "{{.State.Running}}", container_name],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            time.sleep(0.2)
            continue
        status = result.stdout.strip().lower()
        if status == "true":
            return True
        if status == "false":
            return False
        time.sleep(0.2)
    return False


@pytest.mark.asyncio
async def test_collect_with_real_docker() -> None:
    if not _docker_available():
        pytest.skip("docker is not available")

    image = _pick_local_image()
    if image is None:
        pytest.skip("no suitable local docker image to run")

    name = f"dhe-test-{os.getpid()}-{int(time.time())}"
    try:
        subprocess.run(
            [
                "docker",
                "run",
                "-d",
                "--name",
                name,
                "--health-cmd",
                "exit 0",
                "--health-interval=1s",
                "--health-retries=1",
                "--health-timeout=1s",
                image,
                "sh",
                "-c",
                "sleep 30",
            ],
            check=True,
            capture_output=True,
            text=True,
        )

        _wait_for_health(name)

        collector = DockerCollector(ignore_list=set(), include_label=None, max_concurrency=2)
        await collector.start()
        try:
            snap = await collector.collect()
        finally:
            await collector.stop()

        assert name in snap
        st = snap[name]
        assert st.container_id
        assert st.image
        assert st.status_text
    finally:
        subprocess.run(["docker", "rm", "-f", name], capture_output=True, text=True)


@pytest.mark.asyncio
async def test_collect_unhealthy_and_oneshot_filtered() -> None:
    if not _docker_available():
        pytest.skip("docker is not available")

    image = _pick_local_image()
    if image is None:
        pytest.skip("no suitable local docker image to run")

    unhealthy_name = f"dhe-unhealthy-{os.getpid()}-{int(time.time())}"
    oneshot_name = f"dhe-oneshot-{os.getpid()}-{int(time.time())}"
    try:
        subprocess.run(
            [
                "docker",
                "run",
                "-d",
                "--name",
                unhealthy_name,
                "--health-cmd",
                "exit 1",
                "--health-interval=1s",
                "--health-retries=1",
                "--health-timeout=1s",
                image,
                "sh",
                "-c",
                "sleep 30",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            [
                "docker",
                "run",
                "-d",
                "--name",
                oneshot_name,
                image,
                "sh",
                "-c",
                "exit 0",
            ],
            check=True,
            capture_output=True,
            text=True,
        )

        if not _wait_for_running(unhealthy_name):
            pytest.skip("container did not stay running; health status not reliable")

        _wait_for_health(unhealthy_name)
        _wait_for_exit(oneshot_name)

        collector = DockerCollector(ignore_list=set(), include_label=None, max_concurrency=2)
        await collector.start()
        try:
            snap = await collector.collect()
        finally:
            await collector.stop()

        assert unhealthy_name in snap
        assert snap[unhealthy_name].status_text == "UNHEALTHY"
        assert oneshot_name not in snap
    finally:
        subprocess.run(["docker", "rm", "-f", unhealthy_name], capture_output=True, text=True)
        subprocess.run(["docker", "rm", "-f", oneshot_name], capture_output=True, text=True)
