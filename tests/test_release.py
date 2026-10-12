import os
import shutil
import subprocess
from pathlib import Path

import pytest


@pytest.mark.parametrize("uncommitted_version", [None, "9.8.8"])
def test_make_tag_uses_committed_project_version(
    tmp_path: Path, uncommitted_version: str | None
) -> None:
    root = Path(__file__).resolve().parents[1]
    for name in ("Makefile", "pyproject.toml"):
        shutil.copy(root / name, tmp_path / name)

    subprocess.run(["poetry", "version", "9.8.7"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.com",
            "commit",
            "-qm",
            "Initial",
        ],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    if uncommitted_version:
        subprocess.run(
            ["poetry", "version", uncommitted_version],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )
    tagged = subprocess.run(
        ["make", "tag"],
        cwd=tmp_path,
        env={
            **os.environ,
            "GIT_COMMITTER_NAME": "Test",
            "GIT_COMMITTER_EMAIL": "test@example.com",
        },
        capture_output=True,
    )
    result = subprocess.run(
        ["git", "tag", "--list"], cwd=tmp_path, check=True, capture_output=True, text=True
    )
    if uncommitted_version:
        assert tagged.returncode != 0
        assert result.stdout.strip() == ""
    else:
        assert tagged.returncode == 0, tagged.stderr.decode()
        assert result.stdout.strip() == "v9.8.7"
