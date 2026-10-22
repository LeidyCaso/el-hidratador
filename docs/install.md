# Install

El Hidratador is a single Python package with no runtime dependencies. Every install path below
produces the same `hidratador` command.

---

## Requirements

| Requirement | Version | Needed for | Required |
|-------------|---------|------------|----------|
| Python | 3.11 or newer | the package and the CLI | yes |
| `sqlite3` | 3.35 or newer | the ledger | yes, bundled with CPython |
| `git` | any | cloning a repository for staging | no |
| `gh` | any | observing a repository, publishing reconciled comments | no |
| `docker` | any | creating a staging sandbox | no |

The last three are adapters. `hidratador doctor` reports a missing one as a warning, not a
failure. The core needs none of them.

```bash
python3 --version
python3 -c "import sqlite3; print(sqlite3.sqlite_version)"
```

---

## Path 1 — install from PyPI

```bash
python3 -m pip install el-hidratador
```

This installs the `hidratador` console script into the environment's `bin` directory. Use a
virtual environment if the system Python is managed by your operating system:

```bash
python3 -m venv ~/.venvs/hidratador
source ~/.venvs/hidratador/bin/activate
python3 -m pip install el-hidratador
```

---

## Path 2 — install from a checkout

Clone the repository and install it in editable mode. The `dev` extra brings in the toolchain the
checks need: `ruff`, `mypy`, `pytest`, and `coverage`.

```bash
git clone https://github.com/hamanakam1/el-hidratador.git
cd el-hidratador
python3 -m pip install -e ".[dev]"
```

The `docs` extra is separate, and installs `mkdocs` and `mkdocs-material` for building this site:

```bash
python3 -m pip install -e ".[dev,docs]"
```

---

## Path 3 — the container image

The repository ships a `Dockerfile` that builds the package into a `python:3.12-slim` image. The
image runs as an unprivileged user, and the ledger lives on a volume rather than inside the image.

```bash
make docker-build
```

Or build it directly:

```bash
docker build -t el-hidratador:local .
```

Run it:

```bash
make docker-run
```

```bash
docker run --rm el-hidratador:local --help
```

The ledger is at `/var/lib/hidratador/ledger.sqlite` inside the container, and that path is a
declared volume. Mount your own to keep state between runs:

```bash
docker run --rm \
  -v "$HOME/.el-hidratador:/var/lib/hidratador" \
  el-hidratador:local status
```

The container image is Linux only.

---

## Path 4 — the devcontainer

The repository does not ship a `.devcontainer/` directory, so there is no devcontainer to open
today. If you want one, add it to your own fork. The image built above is a working base:

```text
.devcontainer/devcontainer.json
```

```json
{
  "name": "El Hidratador",
  "image": "mcr.microsoft.com/devcontainers/python:3.12",
  "postCreateCommand": "python3 -m pip install -e \".[dev]\"",
  "customizations": {
    "vscode": {
      "extensions": ["ms-python.python", "charliermarsh.ruff"]
    }
  }
}
```

Open it with "Reopen in Container", then run the checks inside the container:

```bash
make check
```

The ledger stays on your host in that setup, because the package reads `$HIDRATADOR_DB` and
defaults to `~/.el-hidratador/ledger.sqlite` inside the container's home directory.

---

## Path 5 — run from source

No install at all. From the repository root, the module entry point works directly:

```bash
python3 -m el_hidratador --help
python3 -m el_hidratador demo --text
```

This is the form to use while you are working on the package. It is equivalent to the `hidratador`
script in every other respect, including exit codes and JSON output.

---

## Verify the install

Four checks, in order.

```bash
# 1. The console script is on PATH and reports its version
hidratador --version
```

```text
hidratador 0.1.0
```

```bash
# 2. The ledger can be created and read back
hidratador --db /tmp/hidratador-check.sqlite init
hidratador --db /tmp/hidratador-check.sqlite status | jq '.tasks_by_status'
```

```json
{}
```

```bash
# 3. The environment is ready
hidratador doctor | jq '{healthy, failed, warnings}'
```

```json
{
  "failed": [],
  "healthy": true,
  "warnings": []
}
```

A fresh machine reports `ledger` and `journal-mode` as warnings until `hidratador init` has run
against the default path, because there is no file to inspect yet. Both are warnings, not
failures: the exit code is still `0`.

```bash
# 4. A full lifecycle runs end to end, against a scratch ledger
hidratador demo --text
```

```text
El Hidratador demonstration
================================

Created the ticket M-1001 in status INBOX.
  Scope keys: repo/api, repo/edge
  A scope key is a resource, not a description. Two tickets that share a scope key cannot run at the same time.
```

Clean up the check file:

```bash
rm -f /tmp/hidratador-check.sqlite /tmp/hidratador-check.sqlite-wal /tmp/hidratador-check.sqlite-shm
```

---

## Environment variables

Two, and only two. Neither holds a credential.

| Variable | Default | Purpose |
|----------|---------|---------|
| `HIDRATADOR_DB` | `~/.el-hidratador/ledger.sqlite` | The ledger path. Used only when `--db` is absent. |
| `HIDRATADOR_GITHUB_DB` | `~/.el-hidratador/github.sqlite` | The GitHub adapter's observation and outbox database. |

Resolution order for the ledger is `--db PATH`, then `$HIDRATADOR_DB`, then the default. Both
variables expand `~`.

```bash
export HIDRATADOR_DB="$HOME/.el-hidratador/ledger.sqlite"
export HIDRATADOR_GITHUB_DB="$HOME/.el-hidratador/github.sqlite"
```

There is no configuration file, no config file search path, and no other environment variable.
Everything else is a flag. See the
[example configuration](https://github.com/hamanakam1/el-hidratador/blob/main/examples/config/hidratador.example.yaml)
for a deployment shape you can turn into real flags.

---

## Uninstall

```bash
python3 -m pip uninstall el-hidratador
```

Removing the package does not remove the ledger. To delete the state as well:

```bash
rm -rf "$HOME/.el-hidratador"
```

If you installed from a checkout in editable mode, remove the checkout too:

```bash
rm -rf /path/to/el-hidratador
```

Check that nothing is left on PATH:

```bash
command -v hidratador || echo "hidratador is gone"
```

---

## Related pages

- [Getting started](getting-started.md) — the first five minutes
- [Operations](operations.md) — ledger location, backups, and the stuck-task runbook
- [Troubleshooting](troubleshooting.md) — when the install does not behave
- [Development](development.md) — the development toolchain in detail
