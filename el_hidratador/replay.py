"""Replay a task from its event log.

The ledger keeps two things: the current state of a task, and the ordered log
of everything that happened to it. The second one is the richer record, and it
is the one a post-mortem needs.

`replay` rebuilds the lifecycle of a task from the events alone, then compares
that reconstruction with the current state. A divergence is not hidden: it is
reported, because a ledger whose log and state disagree is a ledger you cannot
trust.

Replay is read-only. It never writes to the ledger.
"""

from __future__ import annotations

from typing import Any

from .core import Ledger, TicketStatus

#: How each event type moves a task between stations.
TRANSITIONS: dict[str, str] = {
    "task.created": TicketStatus.INBOX.value,
    "task.triaged": TicketStatus.READY.value,
    "session.started": TicketStatus.IN_PROGRESS.value,
    "failure.recorded": TicketStatus.BLOCKED.value,
    "operator.retry": TicketStatus.READY.value,
    "session.finished": TicketStatus.REVIEW.value,
    "operator.accept": TicketStatus.ACCEPTED.value,
    "task.done": TicketStatus.DONE.value,
    "operator.cancel": TicketStatus.CANCELLED.value,
}

#: Events that do not move a task but are part of its story.
ANNOTATIONS = (
    "task.updated",
    "context.attached",
    "session.checkpoint",
    "handoff.recorded",
)


def reconstruct(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Rebuild the lifecycle of a task from its events."""
    steps: list[dict[str, Any]] = []
    station = ""
    for event in events:
        kind = event.get("type", "")
        data = event.get("data") or {}
        target = TRANSITIONS.get(kind)
        if target:
            station = target
        steps.append(
            {
                "seq": event.get("seq"),
                "event": kind,
                "station": station,
                "moved": bool(target),
                "detail": _detail(kind, data),
            }
        )
    return {
        "steps": steps,
        "final_station": station,
        "transitions": [
            {
                "seq": step["seq"],
                "event": step["event"],
                "station": step["station"],
            }
            for step in steps
            if step["moved"]
        ],
    }


def _detail(kind: str, data: dict[str, Any]) -> str:
    if kind == "session.started":
        return f"owner={data.get('owner', '')} lease_until={data.get('lease_until', '')}"
    if kind == "session.checkpoint":
        return f"tokens={data.get('tokens', 0)} evidence={data.get('evidence_hash', '')[:12]}"
    if kind == "failure.recorded":
        return f"category={data.get('category', '')} fingerprint={data.get('fingerprint', '')}"
    if kind == "operator.accept" or kind == "operator.retry" or kind == "operator.cancel":
        return str(data.get("reason", ""))
    if kind == "context.attached":
        return f"source={data.get('source', '')} hash={str(data.get('hash', ''))[:12]}"
    if kind == "task.created":
        return f"scope={', '.join(data.get('scope', []) or [])}"
    if kind == "handoff.recorded":
        return f"handoff={data.get('handoff', '')}"
    return ""


def replay(ledger: Ledger, task_id: str) -> dict[str, Any]:
    """Replay one task and compare the reconstruction with the current state."""
    task = ledger.task(task_id)
    events = [event for event in ledger.events() if event.get("task_id") == task_id]
    reconstruction = reconstruct(events)
    current = task["status"]

    divergences: list[dict[str, Any]] = []
    if events and reconstruction["final_station"] != current:
        divergences.append(
            {
                "kind": "station_mismatch",
                "reconstructed": reconstruction["final_station"],
                "recorded": current,
                "detail": "the event log and the ticket table disagree about the current station",
            }
        )
    if not events:
        divergences.append(
            {
                "kind": "no_events",
                "reconstructed": None,
                "recorded": current,
                "detail": "the task has no events; the reconstruction is empty",
            }
        )

    checkpoints = [
        checkpoint
        for session in ledger.status()["sessions"]
        if session["task_id"] == task_id
        for checkpoint in ledger.checkpoints(session["id"])
    ]

    return {
        "task_id": task_id,
        "current_station": current,
        "reconstructed_station": reconstruction["final_station"],
        "event_count": len(events),
        "steps": reconstruction["steps"],
        "transitions": reconstruction["transitions"],
        "checkpoints": checkpoints,
        "divergences": divergences,
        "consistent": not divergences,
        "note": "Replay is read-only. A divergence is reported, never repaired.",
    }


def replay_all(ledger: Ledger) -> dict[str, Any]:
    """Replay every task in the ledger."""
    reports = [replay(ledger, task["id"]) for task in ledger.tasks()]
    inconsistent = [report["task_id"] for report in reports if not report["consistent"]]
    return {
        "tasks": reports,
        "count": len(reports),
        "inconsistent": inconsistent,
        "note": "Replay is read-only. A divergence is reported, never repaired.",
    }
