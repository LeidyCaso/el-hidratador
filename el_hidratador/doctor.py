"""Environment checks.

`doctor` answers one question: is this machine ready to run El Hidratador? It
checks the interpreter, the ledger, the storage, and the optional adapters,
and it says what it found in plain language.

The checks never repair anything. A diagnosis that quietly fixes the problem is
a diagnosis you cannot trust.
"""

from __future__ import annotations

import os
import shutil
import sqlite3
import sys
from pathlib import Path
from typing import Any

from .core import default_db_path

OK = "ok"
WARN = "warn"
FAIL = "fail"

MINIMUM_PYTHON = (3, 11)


def _check(name: str, status: str, detail: str, remedy: str = "") -> dict[str, Any]:
    entry: dict[str, Any] = {"name": name, "status": status, "detail": detail}
    if remedy:
        entry["remedy"] = remedy
    return entry


def check_python() -> dict[str, Any]:
    """The interpreter must be new enough and must not be a prerelease."""
    version = ".".join(str(part) for part in sys.version_info[:3])
    if sys.version_info[:2] < MINIMUM_PYTHON:
        return _check(
            "python",
            FAIL,
            f"Python {version} is older than the required {MINIMUM_PYTHON[0]}.{MINIMUM_PYTHON[1]}",
            f"Install Python {MINIMUM_PYTHON[0]}.{MINIMUM_PYTHON[1]} or newer and reinstall the package",
        )
    if sys.version_info.releaselevel != "final":
        return _check(
            "python",
            WARN,
            f"Python {version} is a prerelease ({sys.version_info.releaselevel})",
            "Use a stable release for reproducible runs",
        )
    return _check("python", OK, f"Python {version}")


def check_sqlite() -> dict[str, Any]:
    """The SQLite build must support the features the ledger relies on."""
    version = sqlite3.sqlite_version
    if sqlite3.sqlite_version_info < (3, 35):
        return _check(
            "sqlite",
            WARN,
            f"SQLite {version} is older than 3.35",
            "Update SQLite so that UPSERT and window functions behave as documented",
        )
    return _check("sqlite", OK, f"SQLite {version}")


def check_ledger(path: Path) -> dict[str, Any]:
    """The ledger must exist, be reachable, and have restrictive permissions."""
    if not path.exists():
        return _check(
            "ledger",
            WARN,
            f"no ledger at {path}",
            "Run `hidratador init` to create one",
        )
    mode = path.stat().st_mode & 0o777
    if mode & 0o077:
        return _check(
            "ledger",
            WARN,
            f"{path} is readable by others (mode {mode:04o})",
            f"chmod 0600 {path}",
        )
    try:
        connection = sqlite3.connect(str(path), timeout=5)
        try:
            integrity = connection.execute("PRAGMA quick_check").fetchone()[0]
        finally:
            connection.close()
    except sqlite3.Error as exc:
        return _check("ledger", FAIL, f"{path} could not be opened: {exc}")
    if integrity != "ok":
        return _check("ledger", FAIL, f"{path} failed the integrity check: {integrity}")
    return _check("ledger", OK, f"{path} (mode {mode:04o}, integrity ok)")


def check_wal(path: Path) -> dict[str, Any]:
    """The journal mode should be WAL, because the ledger is written concurrently."""
    if not path.exists():
        return _check("journal-mode", WARN, "no ledger to inspect")
    try:
        connection = sqlite3.connect(str(path), timeout=5)
        try:
            mode = connection.execute("PRAGMA journal_mode").fetchone()[0]
        finally:
            connection.close()
    except sqlite3.Error as exc:
        return _check("journal-mode", FAIL, f"could not read the journal mode: {exc}")
    if mode.lower() != "wal":
        return _check(
            "journal-mode",
            WARN,
            f"the journal mode is {mode}, not wal",
            "Reopen the ledger with a recent version of the package; migrations set the mode",
        )
    return _check("journal-mode", OK, "wal")


def check_adapters() -> list[dict[str, Any]]:
    """The optional command line tools, and what they are used for."""
    results: list[dict[str, Any]] = []
    for tool, purpose in (
        ("git", "cloning a repository for staging"),
        ("gh", "observing a repository and publishing reconciled comments"),
        ("docker", "creating a staging sandbox"),
    ):
        path = shutil.which(tool)
        if path:
            results.append(_check(f"adapter:{tool}", OK, f"{tool} at {path} ({purpose})"))
        else:
            results.append(
                _check(
                    f"adapter:{tool}",
                    WARN,
                    f"{tool} is not on PATH, so the {purpose} adapter cannot run",
                    f"Install {tool} if you need that adapter; the core does not require it",
                )
            )
    return results


def check_disk(path: Path) -> dict[str, Any]:
    """There must be room for the write-ahead log."""
    target = path.parent if str(path.parent) else Path(".")
    try:
        usage = shutil.disk_usage(target)
    except OSError as exc:
        return _check("disk", WARN, f"could not read the free space of {target}: {exc}")
    free_mb = usage.free // (1024 * 1024)
    if free_mb < 50:
        return _check(
            "disk",
            WARN,
            f"only {free_mb} MiB free on {target}",
            "The event log is append-only; free space before a long run",
        )
    return _check("disk", OK, f"{free_mb} MiB free on {target}")


def check_environment() -> list[dict[str, Any]]:
    """The configuration environment variables, and whether they are set."""
    results: list[dict[str, Any]] = []
    for name, purpose in (
        ("HIDRATADOR_DB", "the ledger location"),
        ("HIDRATADOR_GITHUB_DB", "the GitHub observation and outbox location"),
    ):
        value = os.environ.get(name)
        if value:
            results.append(_check(f"env:{name}", OK, f"{name}={value} ({purpose})"))
        else:
            results.append(
                _check(
                    f"env:{name}",
                    OK,
                    f"{name} is not set, so the default location is used ({purpose})",
                )
            )
    return results


def run_checks(db_path: Path | None = None) -> dict[str, Any]:
    """Run every check and summarise the result."""
    path = Path(db_path) if db_path else default_db_path()
    checks: list[dict[str, Any]] = [check_python(), check_sqlite()]
    checks.append(check_ledger(path))
    checks.append(check_wal(path))
    checks.extend(check_adapters())
    checks.append(check_disk(path))
    checks.extend(check_environment())

    failed = [check["name"] for check in checks if check["status"] == FAIL]
    warned = [check["name"] for check in checks if check["status"] == WARN]
    return {
        "healthy": not failed,
        "checks": checks,
        "failed": failed,
        "warnings": warned,
        "database": str(path),
        "note": "The checks report. They never repair anything.",
    }
