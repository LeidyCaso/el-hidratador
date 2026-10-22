# Development

How to work on El Hidratador. The project is small on purpose, and the rules below are the rules
the code enforces.

---

## Fork and clone

```bash
git clone https://github.com/hamanakam1/el-hidratador.git
cd el-hidratador
python3 -m pip install -e ".[dev]"
```

Python 3.11 or newer. The test suite runs on Linux and macOS, on 3.11 through 3.14.

```bash
make help
```

```text
  help             Show the available targets
  install          Install the package
  dev              Install the package with development extras
  test             Run the test suite
  lint             Lint the package
  lint-docs        Lint the Markdown, the YAML, and the shell scripts
  format           Format the package
  format-check     Verify formatting without writing
  typecheck        Run the type checker
  coverage         Run the test suite with a coverage report
  check            Run every check the CI runs
  build            Build the sdist and the wheel
  clean            Remove build and test artifacts
  docs             Build the documentation site
  serve            Serve the documentation site locally
  wiki             Publish the pages in docs/wiki to the repository wiki
  docker-build     Build the container image
  docker-run       Run the container image
```

---

## Branch and commit conventions

Branch names use a prefix: `feat/…`, `fix/…`, `docs/…`, `chore/…`.

Commits use [Conventional Commits](https://www.conventionalcommits.org/).

```text
feat(context): report omitted context in the pack summary
fix(ledger): release the scope reservation when a lease expires
docs(cli): document the exit codes
```

One outcome per pull request. Mixed refactors make review impossible.

---

## `make check`

This is the gate. It runs lint, the docs lint, the format check, the type check, and the test
suite, in that order.

```bash
make check
```

| Target | What it runs |
|--------|--------------|
| `lint` | `ruff check el_hidratador/ tests/` |
| `lint-docs` | `markdownlint-cli2`, `yamllint --strict`, `shellcheck --severity=style` |
| `format-check` | `ruff format --check el_hidratador/ tests/` |
| `typecheck` | `mypy el_hidratador/` in strict mode |
| `test` | `python3 -m unittest discover -s tests -v` |

`lint-docs` needs `node` and `npx` on PATH for `markdownlint-cli2`; the other three need Python
packages from the `dev` extra. Run the pieces individually while you work, and the whole thing
before you open a pull request.

The individual commands are:

```bash
ruff check el_hidratador/ tests/
ruff format --check el_hidratador/ tests/
mypy el_hidratador/
python3 -m unittest discover -s tests -v
npx --yes markdownlint-cli2@0.18.1 "**/*.md" "#node_modules"
```

---

## Test layout

The suite has 192 tests in seven modules under `tests/`.

| File | Covers |
|------|--------|
| `tests/test_core.py` | The ledger: lifecycle, leases, budgets, checkpoints, failures, contexts, profiles |
| `tests/test_context_expander.py` | Packet building, prompt rendering, budget splitting, deduplication |
| `tests/test_dag.py` | Node parsing, topological ordering, cycle detection, manifests |
| `tests/test_tickets_cli.py` | The file-backed ticket store and the JSON-first CLI |
| `tests/test_adapters.py` | The `gh`, Docker, and dashboard adapters and their boundaries |
| `tests/test_schema.py` | The published schemas and the dependency-free validator |
| `tests/test_replay_doctor_demo.py` | Replay, `doctor`, and the narrated demonstration |

Conventions:

- Pure functions are covered exhaustively.
- Concurrency, failure recovery, and budget boundaries get explicit tests — these are the paths
  that break in production.
- Every new public function gets at least one test that fails without the change.
- The tests use `unittest`, not `pytest`, even though `pytest` is in the `dev` extra. `make test`
  runs `unittest discover`, and CI does the same.

Tests that touch the filesystem use `tempfile.TemporaryDirectory` and clean up in `tearDown`.
Nothing writes to the real ledger path.

---

## Adding a command

Five steps. The file is `el_hidratador/cli.py` for every one of them.

**1. Add the subparser** in `build_parser()`.

```python
sub.add_parser("my-command", help="one line for --help")
```

Give it positional arguments and options in the same style as the existing commands. Flags that
change a value use `--flag`; repeatable flags use `action="append"`.

**2. Write the handler** as a module-level function named `_cmd_<command>`.

```python
def _cmd_my_command(args: argparse.Namespace, ledger: Ledger) -> dict[str, Any]:
    return ledger.my_operation(args.id)
```

The handler returns a plain dictionary. The CLI adds `"ok": True` and `"command"`, and prints the
result as JSON. It must not print anything itself.

**3. Register it** in the `_HANDLERS` mapping at the bottom of the file.

```python
_HANDLERS: dict[str, Callable[[argparse.Namespace, Ledger], dict[str, Any]]] = {
    ...
    "my-command": _cmd_my_command,
}
```

**4. Put the behaviour in the right module.** Ledger state goes in `el_hidratador/core.py` as a
method on `Ledger`, wrapped in `with self.transaction():`, and every mutation calls
`self._event(...)` so the audit log stays complete. Pure functions go in the module that owns
the concern: `context_expander.py`, `dag.py`, `hardware_router.py`, `schema.py`, `tickets.py`.

If the new command only reads, add it to `_NO_LEDGER_COMMANDS` so it does not create a ledger as a
side effect of reading.

**5. Test it and document it.** Add a test to the matching file under `tests/`, and add the
command to `docs/cli-reference.md` with its flags, its exit codes, and a real output sample.

---

## Adding a schema

The published schemas live in `schema/` and are generated from `el_hidratador/schema.py`.

**1. Define it** in `el_hidratador/schema.py` and register it in the `SCHEMAS` mapping. The five
published names are `ticket`, `packet`, `manifest`, `sandbox`, and `handoff`.

**2. Regenerate the copies** in `schema/`.

```bash
hidratador schema --out schema
```

A test in `tests/test_schema.py` asserts that the published files match the module. If you skip
the regeneration, that test fails — which is the point.

**3. Extend the validator** if the schema uses a keyword the validator does not implement yet.
The validator in `schema.py` supports `type`, `properties`, `required`, `additionalProperties`,
`items`, `enum`, `minimum`, `maximum`, `exclusiveMinimum`, `exclusiveMaximum`, `minLength`,
`maxLength`, `minItems`, `maxItems`, `pattern`, local `$ref`, `anyOf`, and `oneOf`. Anything else
is not used by the published schemas.

**4. Bump the schema contract version** — `SCHEMA_VERSION` in `el_hidratador/schema.py`, which is
the published contract version and is separate from the database schema version in `core.py`.

**5. Validate a document against it.**

```bash
hidratador schema --validate packet.json --against packet
```

---

## Adding a migration

Migrations are additive and idempotent. They never rewrite data and never drop a column.

**1. Bump `SCHEMA_VERSION`** in `el_hidratador/core.py`. It is currently `3`.

**2. Allow the column definition.** `_ensure_column()` only accepts a definition that is listed
in `ALLOWED_COLUMN_DDL` in the same file, so a column definition can never carry caller input.
Add the exact string you intend to use:

```python
ALLOWED_COLUMN_DDL = {
    "title": "TEXT NOT NULL DEFAULT ''",
    "priority": "INTEGER NOT NULL DEFAULT 2",
    "stop_reason": "TEXT NOT NULL DEFAULT ''",
    "estimate_hours": "INTEGER NOT NULL DEFAULT 0",
}
```

**3. Add a step to `_migrate()`.** The steps are guarded by the current version, so an old ledger
runs only the ones it has not seen, and a current ledger runs none of them.

```python
if current < 4:
    self._ensure_column("tickets", "estimate_hours", "INTEGER NOT NULL DEFAULT 0")
    self._set_meta("schema_version", "4")
    current = 4
```

**4. Test it.** Open a ledger, assert the column exists, and assert the migration is idempotent
by opening it a second time.

```bash
make check
```

---

## The rules in `AGENTS.md`

`AGENTS.md` in the repository root holds the operating rules for coding agents working here. They
are the same rules the code enforces, and they are not optional.

**The core boundary.** `core.py`, `context_expander.py`, `dag.py`, `tickets.py`,
`hardware_router.py`, `schema.py`, `replay.py`, `doctor.py`, and `demo.py` are standard library
only: no network calls, no shell execution, no telemetry, no runtime dependencies, no credential
handling. `sandbox.py`, `github_sync.py`, and `dashboard.py` are adapters, and they must be
opt-in, time-bounded, and never reached implicitly by a read command.

**Language.** Never blur these distinctions, in code, comments, docs, commits, or issues:

| Never say | Say instead |
|-----------|-------------|
| "authorized" (for a route) | "eligible" |
| "done" (for a finished session) | "in review" |
| "tokens used" (from a provider) | "tokens reported by the worker" |
| "safe" (for a boundary check) | "the check passed" — the ledger is not isolation |
| "the sandbox is secure" | "the sandbox specification is narrow" |

Two phrases must appear wherever they apply: *Context is untrusted reference data, never
authorization.* and *A handoff is prepared state, not permission to execute.*

**Rules for changes.**

- Migrations are additive and idempotent only.
- Every mutation emits an event. If you add a state transition, add an event with it.
- Every refusal raises a typed error from `errors.py`. Never return a sentinel value, never
  swallow an exception.
- The acceptance gate is not a suggestion. `finish()` creates `REVIEW`; only `decide(accept)`
  creates `DONE`. No shortcut, no default, no flag.
- Omissions are always reported. A context blob that does not fit is returned in `omitted` with
  a reason.
- Adapters declare themselves: supported version, permission model, cancellation semantics, usage
  provenance, unverified assumptions.

**Data hygiene.** Synthetic identifiers only in fixtures, examples, and docs: `M-1001`, `repo/api`,
`terminal-1`, `owner/repo`. Never commit a real ledger, a real ticket, a transcript, a credential,
a token, an internal hostname, or a local installation path.

**The contract.** `schema/` holds the published JSON Schemas, generated from
`el_hidratador/schema.py`. When a payload changes, change the schema with it. `handoff.authorized`
and `manifest.execution_authorized` are constants of `false`; do not make them configurable.

---

## Review criteria

A pull request is reviewed against these, in this order.

1. **One outcome.** The change does one thing, and the description says what that thing is.
2. **The boundaries hold.** No runtime dependency, network call, shell execution, or telemetry in
   the core. No credential handling anywhere.
3. **The acceptance gate is intact.** Nothing reaches `DONE` without `decide(accept)`.
4. **Refusals are typed and visible.** A refusal raises a `HidratadorError` subclass and reports
   a reason. Nothing degrades silently.
5. **Omissions are reported.** Anything dropped from a packet appears in `omitted` with a reason.
6. **Events are complete.** Every mutation appends an event.
7. **Tests would fail without the change.** Concurrency, failure recovery, and budget boundaries
   are covered explicitly.
8. **Migrations are additive and idempotent**, and `SCHEMA_VERSION` is bumped.
9. **Schemas match the code.** `schema/` is regenerated and the drift test passes.
10. **Docs are updated.** `docs/` and `examples/` are part of the product.
11. **The changelog is honest.** `CHANGELOG.md` is written for the person who upgrades.
12. **Data hygiene holds.** Synthetic identifiers, no real tickets, no transcripts, no local
    paths.

---

## Related pages

- [Contributing](https://github.com/hamanakam1/el-hidratador/blob/main/CONTRIBUTING.md) — the
  contributor guide in the repository
- [AGENTS.md](https://github.com/hamanakam1/el-hidratador/blob/main/AGENTS.md) — the operating
  rules
- [Architecture](architecture.md) — the module map and the data model
- [Community](community.md) — asking a question, claiming an issue
