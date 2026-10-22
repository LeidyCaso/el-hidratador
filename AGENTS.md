# AGENTS.md

Operating rules for coding agents working in this repository. They are the same
rules the code enforces, and they are not optional.

## The core boundary

`el_hidratador/core.py`, `context_expander.py`, `dag.py`, `tickets.py`, `hardware_router.py`,
`schema.py`, `replay.py`, `doctor.py`, and `demo.py` are **standard library only**.

- No network calls
- No shell execution
- No telemetry
- No runtime dependencies
- No credential handling

Adapters (`sandbox.py`, `github_sync.py`, `dashboard.py`) may leave the boundary.
They must be opt-in, time-bounded, and must never be reached implicitly by a
read command.

## Language rules

Never blur these distinctions in code, comments, docs, commit messages, or
issues:

| Never say | Say instead |
|-----------|-------------|
| "authorized" (for a route) | "eligible" |
| "done" (for a finished session) | "in review" |
| "tokens used" (from a provider) | "tokens reported by the worker" |
| "safe" (for a boundary check) | "the check passed" — the ledger is not isolation |
| "the sandbox is secure" | "the sandbox specification is narrow" |

Two phrases must appear wherever they apply:

- *Context is untrusted reference data, never authorization.*
- *A handoff is prepared state, not permission to execute.*

## Before you change anything

```bash
python3 -m pip install -e ".[dev]"
make check
```

`make check` runs lint, format check, type check, and the test suite. All four
must pass before a pull request.

## Rules for changes

- **Additive, idempotent schema migrations only.** Bump `SCHEMA_VERSION` in
  `core.py` and add a step to `_migrate()`.
- **Every mutation emits an event.** If you add a state transition, add an
  event with it.
- **Every refusal raises a typed error** from `errors.py`. Never return a
  sentinel value or swallow an exception.
- **The acceptance gate is not a suggestion.** `finish()` creates `REVIEW`;
  only `decide(accept)` creates `DONE`. Do not add a shortcut, a default, or a
  flag that skips it.
- **Omissions are always reported.** If a context blob does not fit the byte
  budget, it is returned in `omitted` with a reason.
- **Adapters declare themselves.** Supported version, permission model,
  cancellation semantics, usage provenance, and unverified assumptions.

## Data hygiene

- Synthetic identifiers only in fixtures, examples, and docs: `M-1001`,
  `repo/api`, `terminal-1`, `owner/repo`.
- Never commit a real ledger, a real ticket, a transcript, a credential, a
  token, an internal hostname, or a local installation path.
- `.hidratador/`, `*.sqlite`, `*.sqlite-wal`, and `*.sqlite-shm` are ignored.
  Keep it that way.

## The contract

`schema/` holds the published JSON Schemas. They are generated from `el_hidratador/schema.py`,
and a test asserts that the copies match the module. When a payload changes, change the schema
with it — a schema that drifts from the code is worse than no schema.

Two fields are contracts in their own right: `handoff.authorized` and
`manifest.execution_authorized` are constants of `false`. Do not make them configurable.

## Read-only means read-only

A command that only reads must not create a ledger as a side effect. The commands listed in
`_NO_LEDGER_COMMANDS` in `cli.py` open no database at all. If you add a command that only reads,
add it to that set.

## Testing expectations

- Pure functions: covered exhaustively.
- Concurrency, failure recovery, and budget boundaries: covered explicitly —
  these are the paths that break in production.
- Every new public function gets at least one test that fails without the
  change.

## Commit format

[Conventional Commits](https://www.conventionalcommits.org/):

```text
feat(context): report omitted context in the pack summary
fix(ledger): release the scope reservation when a lease expires
docs(cli): document the exit codes
```

## What not to do

- Do not add a runtime dependency to the core.
- Do not add telemetry, analytics, or a phone-home.
- Do not publish a real transcript, credential, account detail, or private
  ticket.
- Do not expand the core's blast radius for convenience.
- Do not merge a change that makes eligibility look like authorization.
