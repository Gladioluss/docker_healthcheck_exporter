from __future__ import annotations

import types

import docker_healthcheck_exporter.__main__ as main_module


def test_main_runs_uvicorn(monkeypatch) -> None:
    settings = types.SimpleNamespace(
        listen_host="127.0.0.1",
        listen_port=1234,
        metrics_file=None,
    )

    called = {}

    def fake_run(app, host: str, port: int, log_level: str) -> None:
        called["app"] = app
        called["host"] = host
        called["port"] = port
        called["log_level"] = log_level

    monkeypatch.setattr(main_module, "load_settings", lambda: settings)
    monkeypatch.setattr(main_module.uvicorn, "run", fake_run)

    main_module.main()

    assert called["app"] is main_module.app
    assert called["host"] == "127.0.0.1"
    assert called["port"] == 1234
    assert called["log_level"] == "info"


def test_module_entrypoint_executes(monkeypatch) -> None:
    import runpy
    import sys
    import types as pytypes

    called = {}

    def fake_run(app, host: str, port: int, log_level: str) -> None:
        called["app"] = app
        called["host"] = host
        called["port"] = port
        called["log_level"] = log_level

    fake_uvicorn = pytypes.ModuleType("uvicorn")
    fake_uvicorn.run = fake_run
    monkeypatch.setitem(sys.modules, "uvicorn", fake_uvicorn)
    monkeypatch.setenv("LISTEN", "127.0.0.1:7777")
    if "docker_healthcheck_exporter.__main__" in sys.modules:
        monkeypatch.delitem(sys.modules, "docker_healthcheck_exporter.__main__", raising=False)

    runpy.run_module("docker_healthcheck_exporter.__main__", run_name="__main__")

    assert called["host"] == "127.0.0.1"
    assert called["port"] == 7777
    assert called["log_level"] == "info"
