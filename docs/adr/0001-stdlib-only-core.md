# ADR 0001: The core has no runtime dependencies

## Status

Accepted

## Context

El Hidratador is expected to run on whatever machine a developer already has, and its core is the
part that has to be trustworthy: the ledger that records who owns what, what evidence was
produced, and whether work was accepted. A core that pulls in a third-party dependency tree
inherits that tree's update cadence, its supply-chain surface, and its ability to reach the
network — and it makes the trust boundary something you have to audit by reading someone else's
package metadata rather than the project's own imports. The project also needs to run in places
where installing a wheel with native extensions is inconvenient: a container staging image, a
workstation, a laptop with no package manager configured.

## Decision

The core modules — `core.py`, `errors.py`, `context_expander.py`, `dag.py`, `tickets.py`,
`hardware_router.py`, `schema.py`, `replay.py`, `doctor.py`, and `demo.py` — import nothing outside
the Python standard library, and `pyproject.toml` declares no runtime dependencies at all. The core
performs no network calls, no shell execution, and no telemetry, and it handles no credentials.
Anything that must leave the process lives in an adapter — `sandbox.py`, `github_sync.py`, or
`dashboard.py` — and those adapters are opt-in, time-bounded, and never reached implicitly by a
read command.

## Consequences

### Accepted benefits

- The install is a single wheel with no dependency resolution, so it installs cleanly on a bare
  interpreter and inside a slim container image.
- The trust boundary is auditable by reading the import statements of the core: if a module has no
  third-party imports and no socket or subprocess calls, it cannot reach the network.
- The ledger is inspectable with tools that ship with Python and with the `sqlite3` CLI, so an
  operator can answer questions about state without this project's own code.
- A dependency cannot be compromised upstream, because there is no dependency to compromise.

### Accepted costs

- The JSON Schema validator in `schema.py` is hand-written and supports only the subset of the
  specification the published schemas use; a full validator would have been a dependency.
- Logging, configuration parsing, and structured error reporting are all hand-rolled, because
  `structlog`, `pydantic-settings`, and friends are all dependencies.
- Some conveniences of the standard library ecosystem are unavailable, and features that would
  normally be a package choice become code this project has to own and test.

## Alternatives considered

- **A third-party validation library (`pydantic`, `jsonschema`).** Rejected: it would make the
  core's trust boundary depend on another project's release process, and the published schemas
  need only a narrow subset of the specification.
- **An HTTP client (`httpx`, `requests`) for the dashboard adapter.** Rejected for the core, and
  kept out of the package entirely: `urllib.request` from the standard library is enough for a
  loopback-only fetch with no redirects.
- **An asynchronous runtime (`asyncio`, `aiohttp`) for concurrent workers.** Rejected: the core's
  concurrency comes from SQLite's WAL mode and a lease, not from in-process concurrency, so an
  event loop would add a dependency without adding a capability.
- **A plugin system with entry points.** Rejected: it would make the installed set of adapters
  depend on the environment, which is exactly the variability the core boundary exists to remove.

## Related pages

- [Architecture](https://github.com/hamanakam1/el-hidratador/blob/main/docs/architecture.md) — the
  module map and the boundary
- [Security](https://github.com/hamanakam1/el-hidratador/blob/main/docs/security.md) — the
  boundaries in detail
