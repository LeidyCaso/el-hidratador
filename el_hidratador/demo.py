"""A narrated demonstration.

`demo` runs a complete ticket lifecycle against a scratch ledger in a
temporary directory and narrates what happens. It never touches the operator's
own ledger, and it needs no repository, no network, and no Docker.

It exists because the fastest way to understand a system is to watch it work.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

from .core import create_ledger

TICKET_ID = "M-1001"
SCOPE = ("repo/api", "repo/edge")
OBJECTIVE = "Expose GET /healthz that returns the request id assigned by the edge proxy."
ACCEPTANCE = "GET /healthz returns 200 with the X-Request-Id header; a unit test covers it."


def _narrate(steps: list[dict[str, Any]]) -> list[str]:
    """Render the steps as plain lines a newcomer can read."""
    lines: list[str] = []
    for step in steps:
        lines.append(step["headline"])
        for detail in step.get("details", []):
            lines.append(f"  {detail}")
    return lines


def run_demo(db_path: str | None = None, keep: bool = False) -> dict[str, Any]:
    """Run the demonstration and return the transcript."""
    temporary: tempfile.TemporaryDirectory[str] | None = None
    if db_path:
        path = Path(db_path).expanduser()
    else:
        temporary = tempfile.TemporaryDirectory(prefix="hidratador-demo-")
        path = Path(temporary.name) / "demo.sqlite"

    steps: list[dict[str, Any]] = []
    ledger = create_ledger(path)
    try:
        created = ledger.add_task(
            task_id=TICKET_ID,
            objective=OBJECTIVE,
            acceptance=ACCEPTANCE,
            title="Add a request id echo endpoint",
            scope=list(SCOPE),
            tags=["api", "health"],
            token_budget=4000,
            owner="terminal-1",
        )
        steps.append(
            {
                "step": "task-add",
                "command": f"hidratador task-add {TICKET_ID} --objective ... --acceptance ...",
                "headline": f"Created the ticket {TICKET_ID} in status INBOX.",
                "details": [
                    f"Scope keys: {', '.join(SCOPE)}",
                    "A scope key is a resource, not a description. Two tickets that share a"
                    " scope key cannot run at the same time.",
                ],
                "result": created,
            }
        )

        attached = ledger.add_context(
            TICKET_ID,
            "# Edge proxy\n\nThe edge proxy sets X-Request-Id on every response.\n",
            "repo readme",
            priority=10,
        )
        steps.append(
            {
                "step": "context-add",
                "command": f"hidratador context-add {TICKET_ID} --file README.md --source-label 'repo readme'",
                "headline": "Attached one context blob, content-addressed by its hash.",
                "details": [
                    f"Hash: {attached['hash'][:16]} ({attached['bytes']} bytes)",
                    "Attached context is reference data. It is quoted inside explicit"
                    " banners and never treated as an instruction.",
                ],
                "result": attached,
            }
        )

        ticket = ledger.triage(TICKET_ID)
        steps.append(
            {
                "step": "triage",
                "command": f"hidratador triage {TICKET_ID}",
                "headline": "Triaged the ticket: INBOX to READY.",
                "details": [f"Status is now {ticket['status']}."],
                "result": ticket,
            }
        )

        session = ledger.start(TICKET_ID, "terminal-1", 900)
        steps.append(
            {
                "step": "start",
                "command": f"hidratador start {TICKET_ID} --owner terminal-1 --lease 900",
                "headline": "Took the execution lease. The task is IN_PROGRESS.",
                "details": [
                    f"Session: {session['session_id'][:12]}",
                    f"Lease expires at {session['lease_until_iso']}.",
                    "The lease reserves the scope. A second worker asking for the same"
                    " scope is refused until the lease is released or expires.",
                ],
                "result": session,
            }
        )

        first = ledger.checkpoint(
            session["session_id"],
            "Route table registered",
            "diff 4f1c2d: router.py adds GET /healthz",
            "Read the request id header",
            900,
        )
        steps.append(
            {
                "step": "checkpoint",
                "command": "hidratador checkpoint <session> --summary ... --evidence ... --next ... --tokens 900",
                "headline": "Recorded the first checkpoint with evidence.",
                "details": [
                    f"Tokens reported so far: {first['tokens']}",
                    "Evidence is hashed. Three checkpoints with the same evidence hash"
                    " block the task as no_progress.",
                ],
                "result": first,
            }
        )

        ledger.checkpoint(
            session["session_id"],
            "Header middleware wired",
            "diff 8ab3e1: middleware reads X-Request-Id",
            "Write the unit test",
            1500,
        )
        finished = ledger.finish(
            session["session_id"],
            "GET /healthz returns 200 with X-Request-Id; unit test green",
        )
        steps.append(
            {
                "step": "finish",
                "command": "hidratador finish <session> --evidence '...'",
                "headline": "Requested review. The task is in REVIEW, not DONE.",
                "details": [
                    "Finishing is not accepting. Only an operator decision can move work to DONE.",
                ],
                "result": finished,
            }
        )

        decided = ledger.decide(TICKET_ID, "accept", "Reviewed the diff and the test output")
        steps.append(
            {
                "step": "decide",
                "command": f"hidratador decide {TICKET_ID} accept --reason '...'",
                "headline": f"Accepted the work. The task is {decided['status']}.",
                "details": ["The acceptance gate is explicit and never bypassed."],
                "result": decided,
            }
        )

        status = ledger.status()
        metrics = status["metrics"]
        steps.append(
            {
                "step": "status",
                "command": "hidratador status",
                "headline": "Read the ledger back.",
                "details": [
                    f"Accepted work: {metrics['accepted']}",
                    f"Tokens reported by the worker: {metrics['reported_tokens']}",
                    "Reported tokens are declared by the worker. They are not metered by"
                    " a provider, and the measured cost stays null.",
                ],
                "result": {"metrics": metrics, "tasks_by_status": status["tasks_by_status"]},
            }
        )

        event_types = [event["type"] for event in ledger.events()]
        steps.append(
            {
                "step": "events",
                "command": "hidratador events",
                "headline": f"Read the audit log: {len(event_types)} events.",
                "details": [" -> ".join(event_types)],
                "result": {"events": event_types},
            }
        )

        return {
            "database": str(path),
            "temporary": db_path is None,
            "steps": steps,
            "narrative": _narrate(steps),
            "note": "The demonstration ran against a scratch ledger. Your ledger was not touched.",
        }
    finally:
        ledger.close()
        if temporary is not None and not keep:
            temporary.cleanup()


def demo_text(result: dict[str, Any]) -> str:
    """Render the demonstration as plain text."""
    lines = ["El Hidratador demonstration", "=" * 32, ""]
    lines.extend(result["narrative"])
    lines.extend(["", f"Ledger used: {result['database']}", result["note"]])
    return "\n".join(lines) + "\n"


def demo_json(result: dict[str, Any]) -> str:
    """Render the demonstration as JSON."""
    return json.dumps(result, indent=2, sort_keys=True, default=str) + "\n"
