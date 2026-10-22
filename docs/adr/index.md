# Architecture decision records

The decisions that shape El Hidratador, written down so that they can be argued with.

Each record states the context, the decision, and what the decision costs. A record is not a
justification — it is a record, written at the moment the decision was made, so that later readers
can see what was known then.

| Record | Decision |
|--------|----------|
| [ADR 0001](0001-stdlib-only-core.md) | The core has no runtime dependencies |
| [ADR 0002](0002-sqlite-wal-ledger.md) | One local SQLite file in WAL mode |
| [ADR 0003](0003-lease-and-scope-keys.md) | Leases and scope keys instead of an external coordinator |
| [ADR 0004](0004-byte-budgets-not-token-budgets.md) | Exact byte budgets, estimated tokens |
| [ADR 0005](0005-untrusted-context.md) | Attached context is reference data, not instructions |
| [ADR 0006](0006-explicit-acceptance-gate.md) | Finishing never implies acceptance |
| [ADR 0007](0007-idempotent-outbox.md) | A reconciled outbox instead of blind writes |

## The shape of a record

```markdown
# ADR 0000: Title

## Status

Accepted

## Context

What made the decision necessary.

## Decision

What was decided, in the active voice.

## Consequences

What this makes easy, and what it makes expensive.

## Alternatives considered

What else was on the table, and why it was not chosen.
```

## Proposing a change

A change to a decision in this directory is a change to the guarantees the code advertises. Open a
[request for comments](https://github.com/hamanakam1/el-hidratador/issues/new?template=rfc.yml)
first, and let the discussion settle the shape before the record is written. When the decision is
made, add a new record with the next number; do not edit an accepted one. The history of what was
believed is worth more than a tidy file.

## Related pages

- [Architecture](../architecture.md) — the system the records describe
- [Development](../development.md) — how to work on the project
- [Community](../community.md) — how decisions get made
