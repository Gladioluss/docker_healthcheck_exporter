from __future__ import annotations

import pytest

from docker_healthcheck_exporter import config


def test_env_default_and_trim(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DHE_TEST", raising=False)
    assert config._env("DHE_TEST", "x") == "x"

    monkeypatch.setenv("DHE_TEST", "  value  ")
    assert config._env("DHE_TEST") == "value"

    monkeypatch.setenv("DHE_TEST", "   ")
    assert config._env("DHE_TEST", "fallback") == "fallback"


def test_parse_set_csv() -> None:
    assert config._parse_set_csv(None, {"a"}) == {"a"}
    assert config._parse_set_csv("", {"a"}) == {"a"}
    assert config._parse_set_csv("IGNORE_ALL", {"a"}) == {"IGNORE_ALL"}
    assert config._parse_set_csv("a, b, c", {"base"}) == {"base", "a", "b", "c"}


def test_load_settings_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LISTEN", "127.0.0.1:9999")
    monkeypatch.setenv("INSTANCE_NAME", "test-instance")
    monkeypatch.setenv("REFRESH_INTERVAL_SECONDS", "7.5")
    monkeypatch.setenv("SERVICES_IGNORE_LIST", "one,two")
    monkeypatch.setenv("INCLUDE_LABEL", "monitor=true")
    monkeypatch.setenv("MAX_CONCURRENCY", "3")

    settings = config.load_settings()

    assert settings.listen_host == "127.0.0.1"
    assert settings.listen_port == 9999
    assert settings.instance_name == "test-instance"
    assert settings.refresh_interval_seconds == 7.5
    assert settings.services_ignore_list == {"vmagent", "health-exporter", "one", "two"}
    assert settings.include_label == "monitor=true"
    assert settings.max_concurrency == 3


def test_load_settings_invalid_listen(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LISTEN", "127.0.0.1")
    with pytest.raises(ValueError):
        config.load_settings()


def test_load_settings_instance_from_uname(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("INSTANCE_NAME", raising=False)
    monkeypatch.delenv("FQDN", raising=False)
    monkeypatch.setenv("LISTEN", "0.0.0.0:9102")

    class DummyUname:
        nodename = "dummy-host"

    monkeypatch.setattr(config.os, "uname", lambda: DummyUname())

    settings = config.load_settings()
    assert settings.instance_name == "dummy-host"
