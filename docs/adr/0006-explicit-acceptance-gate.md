# ADR 0006: Acceptance is an explicit operator decision

## Status

Accepted

## Context

A worker finishing and a human accepting the work are different acts. Finishing says the worker
believes it is done; accepting says a person looked at the evidence and agreed. Collapsing them
would mean that the output of an automated agent promotes itself to accepted work, and the whole
audit trail would show a task going from "in progress" to "done" with no human present. It would
also mean there is no record of who accepted what, or why — which is the first question anyone
asks after something goes wrong.

## Decision

`finish()` moves a task to `REVIEW`. Only `decide(accept)` moves it through `ACCEPTED` to `DONE`,
and it does so with a mandatory reason that is written into the audit event alongside
`operator.accept` and `task.done`. There is no flag, no default, no timeout, and no shortcut that
produces `DONE` by any other route. `decide` also offers `retry`, which returns a task to `READY`
with its cumulative token count intact, and `cancel`, which retires it.

## Consequences

### Accepted benefits

- A human is always in the loop between work and acceptance, which is the property the rest of the
  design depends on.
- The audit log records the decision, its reason, and its author, so the reasoning survives with
  the outcome and can be reviewed months later.
- Execution and acceptance stay separate concepts, which keeps "the agent did what it was told"
  distinct from "the result is good".
- The state machine stays small: eight stations, one of which (`ACCEPTED`) is a transit point
  written and cleared inside the same transaction.

### Accepted costs

- Work can sit in `REVIEW` indefinitely without an operator, and the pipeline has one more command
  in it than it would without the gate.
- A task in `REVIEW` keeps its scope reservation, so a review nobody performs holds a resource
  that other work needs.
- The `ACCEPTED` station is never observed, because `decide(accept)` writes it and `DONE` in the
  same transaction; it exists for legibility in the event stream rather than as a resting state.
- Automating a pipeline end to end requires an automated acceptance step, and that step is a
  decision this project deliberately does not make for the operator.

## Alternatives considered

- **Let `finish()` mark the task `DONE`.** Rejected: it removes the gate entirely, and "the
  worker says it is done" would be recorded as "the work is accepted".
- **Add a configuration flag such as `auto_accept`.** Rejected: it turns the gate into a
  preference, and a preference is not a gate.
- **Accept automatically after a timeout.** Rejected: it accepts work that nobody looked at,
  which is the same outcome as removing the gate, with extra machinery.
- **Let the executing agent issue the acceptance.** Rejected: the agent is not the reviewer; it
  is the party whose output needs checking.
- **Record acceptance in a separate ledger.** Rejected: it splits the state an operator has to
  read across two places, and makes the lifecycle harder to reconstruct from one file.

## Related pages

- [Architecture](https://github.com/hamanakam1/el-hidratador/blob/main/docs/architecture.md) — the
  lifecycle of a ticket
- [Failure playbook](https://github.com/hamanakam1/el-hidratador/blob/main/docs/failure-playbook.md)
  — the recovery paths out of `BLOCKED` and `REVIEW`
