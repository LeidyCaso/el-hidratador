# Troubleshooting

Every refusal in El Hidratador is a typed error whose message names the cause. This page is the
lookup table: the exact message, why it happens, and the exact command that recovers.

---

## How to read a refusal

Every command prints one JSON object. A refusal looks like this:

```json
{
  "error": "resource scope reserved by M-1001: repo/api",
  "kind": "Conflict",
  "ok": false
}
```

| Field | Meaning |
|-------|---------|
| `ok` | Always `false` on a refusal |
| `kind` | `ValidationError`, `Conflict`, `NotFound`, `BudgetExceeded`, `LeaseExpired`, or the literal `adapter` |
| `error` | The message, which names the cause |

| Exit code | Meaning |
|-----------|---------|
| `0` | The command succeeded |
| `2` | A refused operation: validation, conflict, budget, expired lease, missing file |
| `3` | An adapter failure: `gh`, the dashboard, or Docker refused or was unreachable |
| `130` | Interrupted at the keyboard |

---

## The lookup table

| Symptom | Cause | First command |
|---------|-------|---------------|
| Task stuck in `BLOCKED` | Expired lease, exhausted budget, repeated evidence, or an explicit `fail` | `hidratador --compact status \| jq '.failures'` |
| `task is IN_PROGRESS; expected READY or INBOX` | The task already holds a lease, or it is past `READY` | `hidratador --compact task-show <id> \| jq '.status'` |
| `resource scope reserved by <id>: <keys>` | Another live task holds an overlapping scope key | `hidratador --compact task-list \| jq '.tasks[] \| {id, status, scope}'` |
| `task token budget exhausted across attempts` | Cumulative tokens across every attempt reached the budget | `hidratador task-update <id> --field token_budget --value 16000` |
| `cumulative token count cannot decrease` | The checkpoint reported fewer tokens than the previous one | `hidratador checkpoint <session> --tokens <same-or-higher>` |
| `unknown session: <id>` | The session id is wrong, or belongs to another ledger | `hidratador --compact status \| jq '.sessions[] \| {id, task_id, status}'` |
| `session is inactive or expired` | The lease ran out, or the session already ended | `hidratador reconcile` |
| `cannot accept a <STATUS> task` | The decision is not legal from that station | `hidratador --compact task-show <id> \| jq '.status'` |
| `budget cannot fit mandatory objective, acceptance, and checkpoint` | The byte budget is smaller than the ticket's own structure | `hidratador pack <id> --max-bytes 24000` |
| `sqlite3.OperationalError: unable to open database file` | The ledger path is wrong, is a directory, or is not writable | `hidratador doctor` |
| `gh <subcommand> failed: …` | The GitHub CLI refused, timed out, or is not installed | `gh auth status` |
| `dashboard host '…' is not loopback` | The preview URL points somewhere the adapter will not reach | `hidratador dashboard-preview --url http://127.0.0.1:8080/api/tasks` |
| `docker run failed: …` | The container could not start, or Docker is not running | `docker info` |

---

## A task is stuck in `BLOCKED`

**Message.** No error — the task is in `BLOCKED` and stays there.

**Why.** Four things block a task: an expired lease, a cumulative budget that was reached, three
consecutive checkpoints with an identical evidence hash, or an explicit `fail` call. The cause is
recorded as a failure row, grouped by fingerprint.

**Recovery.** Read the failure first, then act on its category.

```bash
hidratador --compact status | jq '.failures[] | {category, fingerprint, occurrences, summary}'
```

```bash
# The worker died: confirm it stopped, then take a new lease
hidratador reconcile
hidratador decide M-1001 retry --reason "Original worker confirmed stopped"
hidratador start M-1001 --owner terminal-2 --lease 900

# The worker was missing information: attach it, then retry
hidratador context-add M-1001 --text "Previous attempt failed: TypeError in router.py" \
  --source-label "failure/attempt-1" --priority 100
hidratador decide M-1001 retry --reason "Attached the attempt-1 error"
hidratador start M-1001 --owner terminal-1 --lease 900

# The work is no longer wanted
hidratador decide M-1001 cancel --reason "Superseded by M-1042"
```

A `BLOCKED` task still reserves its scope keys, so it holds other work back until it is retried or
cancelled.

---

## `task is IN_PROGRESS; expected READY or INBOX`

**Message.**

```json
{
  "error": "task is IN_PROGRESS; expected READY or INBOX",
  "kind": "Conflict",
  "ok": false
}
```

**Why.** `start` accepts a task only in `INBOX` or `READY`. A task already in `IN_PROGRESS` has a
live lease — most likely your own, from an earlier command in the same session.

**Recovery.** Read the session, then decide whether the lease is still wanted.

```bash
hidratador --compact status | jq '.sessions[] | select(.task_id == "M-1001") | {id, owner, status}'
```

If a worker is still running, leave it alone. If it died, reconcile and retry:

```bash
hidratador reconcile
hidratador decide M-1001 retry --reason "Worker terminal-1 confirmed stopped"
hidratador start M-1001 --owner terminal-2 --lease 900
```

---

## `resource scope reserved by <id>: <keys>`

**Message.**

```json
{
  "error": "resource scope reserved by M-1001: repo/api",
  "kind": "Conflict",
  "ok": false
}
```

**Why.** Another live task holds an overlapping scope key. Tasks in `IN_PROGRESS`, `BLOCKED`, and
`REVIEW` all reserve their keys, so a task sitting in review still blocks a second worker.

**Recovery.** Find the holder, then release it or wait.

```bash
hidratador --compact task-list | jq '.tasks[] | {id, status, scope}'
hidratador decide M-1001 retry --reason "Handing repo/api to M-1002"
hidratador decide M-1001 cancel --reason "Superseded by M-1002"
```

If the two tasks genuinely do not touch the same resource, their scope keys are too coarse. Narrow
them:

```bash
hidratador task-update M-1002 --field scope --value repo/api/router
```

---

## `task token budget exhausted across attempts`

**Message.**

```json
{
  "error": "task token budget exhausted across attempts",
  "kind": "BudgetExceeded",
  "ok": false
}
```

**Why.** The token budget is cumulative across every attempt. A retry does not reset it, so a task
that spent its budget is still spent. `start` refuses before it creates a session.

**Recovery.** Raise the budget, then retry. The alternative is to split the work into smaller
tickets with their own budgets.

```bash
hidratador task-update M-1001 --field token_budget --value 16000
hidratador decide M-1001 retry --reason "Budget raised to 16000"
hidratador start M-1001 --owner terminal-1 --lease 900
```

---

## `cumulative token count cannot decrease`

**Message.**

```json
{
  "error": "cumulative token count cannot decrease",
  "kind": "Conflict",
  "ok": false
}
```

**Why.** The `--tokens` flag is a cumulative count for the session, not a delta. Reporting fewer
tokens than the previous checkpoint would let a worker hide how much it actually spent.

**Recovery.** Report the running total, not the increment. The previous checkpoint said 900, so
the new total is 1500, not 600.

```bash
hidratador checkpoint "$SESSION" \
  --summary "Header middleware wired" \
  --evidence "diff 8ab3e1: middleware reads X-Request-Id" \
  --next "Write the unit test" \
  --tokens 1500
```

The running total is in the session record:

```bash
hidratador --compact status | jq '.sessions[] | select(.task_id == "M-1001") | {id, tokens}'
```

---

## `unknown session: <id>`

**Message.**

```json
{
  "error": "unknown session: deadbeef",
  "kind": "NotFound",
  "ok": false
}
```

**Why.** The session id does not exist in this ledger. The usual cause is pointing at a different
ledger than the one the session was created in — `--db` or `$HIDRATADOR_DB` changed between the
two commands.

**Recovery.** List the sessions in the ledger you are actually talking to, and check which ledger
that is.

```bash
hidratador --compact status | jq '.sessions[] | {id, task_id, owner, status}'
hidratador status | jq -r '.database'
```

Note that `hidratador checkpoints <session>` returns an empty list rather than an error for an
unknown session; the `NotFound` refusal comes from `checkpoint`, `finish`, and `fail`.

---

## `session is inactive or expired`

**Message.**

```json
{
  "error": "session is inactive or expired",
  "kind": "LeaseExpired",
  "ok": false
}
```

**Why.** The lease ran out, or the session already ended. Every lease-bearing command renews the
lease, so this usually means the worker stopped checking in — it crashed, it was suspended, or it
finished without recording a checkpoint.

**Recovery.** Reconcile, then take a new lease. The old session cannot be finished, because the
lease is gone. Renew the lease sooner next time with a longer `--lease`.

```bash
hidratador reconcile
hidratador decide M-1001 retry --reason "Lease expired; worker confirmed stopped"
hidratador start M-1001 --owner terminal-2 --lease 900
```

---

## `cannot accept a <STATUS> task`

**Message.** The refusal names the station the task is actually in.

```json
{
  "error": "cannot accept a READY task",
  "kind": "Conflict",
  "ok": false
}
```

**Why.** `accept` is legal from exactly one station: `REVIEW`, which `finish` produces. Every
other status is refused — a task in `READY` has not been worked on yet, a task in `DONE` has
already been accepted, and a task in `BLOCKED` failed.

**Recovery.** Get the task to `REVIEW` first.

```bash
# A task that was never started
hidratador start M-1001 --owner terminal-1 --lease 900
hidratador checkpoint "$SESSION" --summary "Route table registered" \
  --evidence "diff 4f1c2d: router.py adds GET /healthz" --next "Read the header" --tokens 900
hidratador finish "$SESSION" --evidence "GET /healthz returns 200 with X-Request-Id"
hidratador decide M-1001 accept --reason "Reviewed the diff and the test output"

# A task that failed: fix it and retry first
hidratador decide M-1001 retry --reason "Dependency satisfied"

# A task that was already accepted
hidratador decide M-1001 cancel --reason "Superseded by M-1042"
```

`cancel` is legal from `READY`, `BLOCKED`, and `REVIEW`. It is not legal from `DONE`.

---

## `budget cannot fit mandatory objective, acceptance, and checkpoint`

**Message.**

```json
{
  "error": "budget cannot fit mandatory objective, acceptance, and checkpoint; increase max_bytes",
  "kind": "Conflict",
  "ok": false
}
```

**Why.** The byte budget is smaller than the ticket's own mandatory structure. No amount of
context trimming helps: the objective, the acceptance criterion, and the latest checkpoint do not
fit at all.

**Recovery.** Raise the byte budget. The default is `12000` for both `pack` and `expand`, and
`expand` measures the packet *and* the rendered prompt, so it is the stricter of the two. The same
situation through `expand` reads `mandatory ticket structure does not fit max_bytes; increase the
budget or shorten the ticket`.

```bash
hidratador pack M-1001 --max-bytes 24000
```

The other option is to shorten the objective or the acceptance text, which is often the better fix
— a ticket whose objective does not fit in a few kilobytes is usually a ticket that says too much.

---

## The ledger will not open

**Message.** The ledger path is wrong, is a directory, or is not writable. `doctor` reports it
cleanly.

```json
{
  "detail": "/var/tmp/ledger.sqlite could not be opened: unable to open database file",
  "name": "ledger",
  "status": "fail"
}
```

**Why.** `doctor` exits `2` when a check fails. A ledger command against the same path raises
`sqlite3.OperationalError: unable to open database file` and exits `1`, because the failure
happens below the CLI's typed error layer.

**Recovery.** Check the path, then the permissions.

```bash
# Which path is the package using?
hidratador status | jq -r '.database'
echo "${HIDRATADOR_DB:-$HOME/.el-hidratador/ledger.sqlite}"
ls -la "$HOME/.el-hidratador/"

# The directory must be writable and private, the file readable and private
chmod 700 "$HOME/.el-hidratador"
chmod 600 "$HOME/.el-hidratador/ledger.sqlite"

# If the path is wrong, point somewhere valid and re-create the ledger
export HIDRATADOR_DB="$HOME/.el-hidratador/ledger.sqlite"
hidratador init
```

If the ledger is corrupt rather than unreachable, restore it from a backup — see
[Operations](operations.md).

---

## A `gh` failure

**Message.**

```json
{
  "error": "gh issue failed: GraphQL: Could not resolve to a Repository with the name 'acme/api'. (repository)",
  "kind": "adapter",
  "ok": false
}
```

**Why.** The adapter shells out to the `gh` CLI with a fixed argv, a 30-second timeout, and a
16 MiB output cap. It never reads a token; `gh` owns authentication. Anything `gh` refuses comes
back as an adapter failure with exit code `3`. Other shapes of the same refusal are
`gh executable not found on PATH`, `gh issue view timed out after 30s`, and
`gh response exceeded the 16 MiB limit`.

**Recovery.** Check that `gh` is installed, authenticated, and can see the repository, then run
the adapter again. Both `github-poll` and `github-publish` are dry runs by default, so you can
inspect the result before anything is written.

```bash
gh --version
gh auth status
gh issue list --repo acme/api --limit 1
hidratador github-poll --repo acme/api
hidratador github-publish --repo acme/api --issue 42 \
  --key handoff-M-1001 --body "Handoff prepared for M-1001"
```

Pass `--apply` when you actually want the write. The `gh` boundary is documented in
[GitHub sync](github-sync.md).

---

## The dashboard is refused

**Message.** The refusal names the rule that was broken.

```json
{
  "error": "dashboard host 'example.com' is not loopback",
  "kind": "ValidationError",
  "ok": false
}
```

**Why.** The preview adapter is deliberately narrow: HTTP only, loopback hosts only, no redirects,
at most 8 MiB, at most 10 seconds, and no credentials in the URL. The limits are enforced before
the socket opens, so a remote host, an `https://` URL, and a URL carrying a password are all
refused on purpose. A dashboard that is reachable but broken is an adapter failure instead, with
exit code `3` and a message such as `dashboard unreachable: [Errno 61] Connection refused`.

**Recovery.** Use a loopback `http://` URL with no credentials in it.

```bash
hidratador dashboard-preview --url http://127.0.0.1:8080/api/tasks --status planned --offset 0 --limit 50
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8080/api/tasks
```

`localhost`, `127.0.0.1`, and `::1` are the accepted hosts.

---

## The Docker sandbox will not start

**Message.** The sandbox adapter raises one of these.

```text
docker executable not found on PATH
docker run failed: <the first 400 characters of stderr>
docker run timed out after 60s
```

**Why.** `apply_sandbox()` is opt-in and defaults to a dry run. When it is asked to really create
the container, it shells out to the `docker` CLI with a fixed argv, a 60-second timeout, and an
environment of `PATH` and `HOME` only — no credential environment is inherited. A failure there
is Docker's failure, reported as an `AdapterError`.

**Recovery.** Check Docker, then dry-run the specification before applying it.

```bash
docker info
hidratador sandbox-apply --id M-1001 --workdir /tmp/work/M-1001
```

The dry run prints the exact command it would run, which you can paste into a terminal to see
Docker's own error message in full. Common causes are a Docker daemon that is not running, a
`--workdir` path that does not exist, and a relative `--workdir`, which is refused outright because
the sandbox path must be absolute.

```bash
mkdir -p /tmp/work/M-1001
ls -ld /tmp/work/M-1001
```

The same thing is available in the library, which is where the specification itself comes from:

```python
from el_hidratador.sandbox import apply_sandbox, build_sandbox

spec = build_sandbox("M-1001", "/tmp/work/M-1001")
print(apply_sandbox(spec))              # dry run: prints the argv, creates nothing
print(apply_sandbox(spec, dry_run=False))
```

You do not need Docker at all. `build_sandbox()` returns the specification as plain data with a
`spec_hash`, and you can hand that to whatever runtime you do use. See
[DAG and sandbox](dag-and-sandbox.md).

---

## Related pages

- [Failure playbook](failure-playbook.md) — one page per failure category, with the recovery paths
- [CLI reference](cli-reference.md) — every command and flag used above
- [Operations](operations.md) — backups, restores, and the stuck-task runbook
- [Security](security.md) — the trust boundaries behind these refusals
