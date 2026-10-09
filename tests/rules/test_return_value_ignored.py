"""Tests for ``return_value_ignored`` (SAFE802).

Covers the Python default set: the six ``os``/``pathlib`` functions that
return ``None`` (or, for ``Path.rename``, an unactionable ``Path``) are
excluded, while ``subprocess.run`` and ``f.write`` still fire.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from safelint.core.engine import LintResult
    from safelint.rules.base import Violation

import pytest

from safelint.core.config import DEFAULTS, deep_merge
from safelint.core.engine import SafetyEngine


def _engine() -> SafetyEngine:
    config = deep_merge(
        DEFAULTS,
        {"rules": {"return_value_ignored": {"enabled": True}}},
    )
    return SafetyEngine(config)


def _safe802(result: LintResult) -> list[Violation]:
    return [v for v in result.violations if v.code == "SAFE802"]


# ---------------------------------------------------------------------------
# Python defaults
# ---------------------------------------------------------------------------


def test_python_defaults_exclude_six_none_returning_names() -> None:
    """The six ``os``/``pathlib`` names that return ``None`` are absent from the Python defaults."""
    flagged = DEFAULTS["rules"]["return_value_ignored"]["flagged_calls"]
    excluded = {"remove", "unlink", "rename", "makedirs", "mkdir", "rmdir"}
    leaked = excluded & set(flagged)
    assert not leaked, f"names still in Python defaults: {leaked}"


def test_python_defaults_keep_replace_and_run() -> None:
    """``replace`` and ``run`` remain in the Python defaults (they carry a signal)."""
    flagged = DEFAULTS["rules"]["return_value_ignored"]["flagged_calls"]
    assert "replace" in flagged
    assert "run" in flagged


def test_subprocess_run_still_fires(tmp_path: Path) -> None:
    """``subprocess.run(...)`` with discarded return value fires SAFE802."""
    sample = tmp_path / "sub.py"
    sample.write_text(
        'import subprocess\nsubprocess.run(["echo", "hi"])\n', encoding="utf-8"
    )
    hits = _safe802(_engine().check_file(str(sample)))
    assert len(hits) == 1
    assert "run" in hits[0].message


def test_fwrite_still_fires(tmp_path: Path) -> None:
    """``f.write(...)`` with discarded return value fires SAFE802."""
    sample = tmp_path / "write.py"
    sample.write_text('f = open("/tmp/foo", "w")\nf.write("hello")\n', encoding="utf-8")
    hits = _safe802(_engine().check_file(str(sample)))
    assert len(hits) == 1
    assert "write" in hits[0].message


# ---------------------------------------------------------------------------
# Excluded names must NOT fire
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("name", "snippet"),
    [
        ("remove", 'import os\nos.remove("/tmp/foo")\n'),
        ("unlink", 'import os\nos.unlink("/tmp/foo")\n'),
        ("rename", 'import os\nos.rename("/tmp/a", "/tmp/b")\n'),
        ("makedirs", 'import os\nos.makedirs("/tmp/foo")\n'),
        ("mkdir", 'import os\nos.mkdir("/tmp/foo")\n'),
        ("rmdir", 'import os\nos.rmdir("/tmp/foo")\n'),
    ],
)
def test_excluded_os_names_do_not_fire(tmp_path: Path, name: str, snippet: str) -> None:
    """Each of the six excluded ``os`` functions produces zero SAFE802 findings."""
    sample = tmp_path / f"{name}.py"
    sample.write_text(snippet, encoding="utf-8")
    hits = _safe802(_engine().check_file(str(sample)))
    assert hits == [], f"{name}() should not fire SAFE802, got {len(hits)} hits"


def test_path_rename_does_not_fire(tmp_path: Path) -> None:
    """``Path.rename()`` is excluded from the Python defaults (returns an unactionable Path)."""
    sample = tmp_path / "pathrename.py"
    sample.write_text(
        'from pathlib import Path\np = Path("/tmp/a")\np.rename("/tmp/b")\n',
        encoding="utf-8",
    )
    hits = _safe802(_engine().check_file(str(sample)))
    assert hits == [], f"Path.rename() should not fire SAFE802, got {len(hits)} hits"
