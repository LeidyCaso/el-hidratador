# ADR 0002: The ledger is one SQLite file in WAL mode

## Status

Accepted

## Context

The ledger holds the facts that decide whether two workers may touch the same resource: the
tickets, the sessions, the leases, the checkpoints, the failures, and the append-only event log.
That state has to survive a process restart, it has to be readable by two workers at once on the
same machine, and it has to be inspectable by a human who wants to know why a task is blocked. It
also has to be movable: an operator backing up or archiving a ledger should be able to copy one
file. A coordination service would satisfy the concurrency requirement but adds a daemon to run,
a port to secure, a schema to migrate over the network, and a failure mode where the service is
down and nothing can be recorded at all.

## Decision

All state lives in a single SQLite database, opened by `Ledger.__init__` with
`PRAGMA foreign_keys=ON`, `PRAGMA journal_mode=WAL`, and `PRAGMA busy_timeout=10000`. The file
lives at `~/.el-hidratador/ledger.sqlite` by default, overridable with `--db PATH` or
`$HIDRATADOR_DB`. The parent directory is created with mode `0700` and the database file is
chmod'd to `0600`. Every mutation runs inside an immediate transaction and appends an event to the
audit log. Migrations are additive and idempotent, and the current version is stored in the `meta`
table.

## Consequences

### Accepted benefits

- One file is the whole state. Copying it, moving it, or reading it with the `sqlite3` CLI needs
  no tooling from this project.
- WAL mode lets readers proceed while a writer holds the write lock, so a dashboard poll does not
  stall a worker that is recording a checkpoint.
- Foreign keys are enforced by the database rather than by application logic, so an orphaned
  checkpoint cannot exist even if a caller gets the order of operations wrong.
- Transactions give atomicity for free: a state change and its audit event are committed together
  or not at all.
- The ledger survives a crash, and `reconcile()` can reconstruct what was in flight from it.

### Accepted costs

- The ledger is a single coordination point. Concurrent writers serialise, and the busy timeout
  is the only backstop before a writer is refused.
- WAL mode leaves `-wal` and `-shm` sidecar files next to the database while it is open, so a
  naive `cp` of the `.sqlite` file alone can produce an inconsistent copy.
- The ledger does not span machines. A worker on another host cannot share it over the network,
  because the core has no network access at all.
- Migrations are necessarily small and incremental, so an old ledger may need several passes to
  bring forward, and a column cannot be renamed or dropped without a data migration.

## Alternatives considered

- **PostgreSQL.** Rejected: it needs a server, a connection string, a credential, and a network
  path into the core. The concurrency this project needs is local, and SQLite covers it.
- **Redis.** Rejected: it is a good fit for ephemeral leases and a poor fit for an audit log that
  has to survive restarts and be read by a human months later.
- **A JSON or YAML file per task.** Rejected: no transactions, no uniqueness enforcement, and
  read-modify-write races on the same task are trivial.
- **LMDB.** Rejected: excellent for read-mostly workloads, awkward for the multi-table relational
  shape the ledger actually has, and it is not in the standard library.
- **DuckDB.** Rejected: it is an analytics engine, not a transactional store with foreign keys and
  partial unique indexes.

## Related pages

- [Operations](https://github.com/hamanakam1/el-hidratador/blob/main/docs/operations.md) — where
  the ledger lives, and how to back it up
- [Architecture](https://github.com/hamanakam1/el-hidratador/blob/main/docs/architecture.md) — the
  data model
