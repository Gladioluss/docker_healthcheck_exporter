from importlib.metadata import version

from docker_healthcheck_exporter import __version__


def test_version_matches_package_metadata() -> None:
    assert __version__ == version("docker-healthcheck-exporter")
