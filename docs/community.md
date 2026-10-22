# Community

El Hidratador is a small project with a short list of rules. This page is where to ask, where to
report, and how to get involved.

---

## Where to ask

| You want to… | Go to |
|---------------|-------|
| Ask a usage question | [Discussions](https://github.com/hamanakam1/el-hidratador/discussions), or the [question form](https://github.com/hamanakam1/el-hidratador/issues/new/choose) |
| Report a defect | [Bug report form](https://github.com/hamanakam1/el-hidratador/issues/new/choose) |
| Propose a feature | [Feature request form](https://github.com/hamanakam1/el-hidratador/issues/new/choose) |
| Point out a documentation problem | [Documentation form](https://github.com/hamanakam1/el-hidratador/issues/new/choose) |
| Report a vulnerability | [Private security advisory](https://github.com/hamanakam1/el-hidratador/security/advisories/new) — never a public issue |
| Contribute code | [CONTRIBUTING.md](https://github.com/hamanakam1/el-hidratador/blob/main/CONTRIBUTING.md) |
| Read the wiki | [Repository wiki](https://github.com/hamanakam1/el-hidratador/wiki) |

Check the [open issues](https://github.com/hamanakam1/el-hidratador/issues) and
[Discussions](https://github.com/hamanakam1/el-hidratador/discussions) first. The `roadmap` label
marks work that is already planned.

---

## How to ask a good question

Questions are welcome and get answered. Three things make them answerable:

1. **Say what you are trying to do**, not only what went wrong. "I want two workers to run
   different tickets against the same repository without colliding" is a better question than
   "scope conflict".
2. **Paste the exact commands and the exact JSON.** The CLI prints one JSON object per command,
   so the whole output is machine-readable. `hidratador --compact status` gives you a complete
   answer in one line.
3. **Give the version and the environment.** `hidratador --version`, the operating system, the
   Python version, and how you installed it.

Never include credentials, tokens, transcripts, internal hostnames, or real ticket data.
Synthetic identifiers are enough to reproduce anything: `M-1001`, `repo/api`, `terminal-1`,
`owner/repo`.

A question that arrives with all three of those usually gets an answer in the first reply.

---

## How to report a bug

Use the [bug report form](https://github.com/hamanakam1/el-hidratador/issues/new/choose). It
asks for four things:

- **What happens**, and what you expected instead.
- **Reproduction steps** — the exact commands, in order, from a clean state.
- **The expected output or exit code.**
- **The environment** — operating system, Python version, `hidratador --version`, and how the
  package was installed.

One defect per report. If two defects happen to appear together, say so in the description rather
than filing one report that covers both — the second one will get lost.

A useful reproduction is short:

```bash
export HIDRATADOR_DB="$(mktemp -d)/ledger.sqlite"
hidratador task-add M-1001 --objective "x" --acceptance "y" --scope repo/api
hidratador triage M-1001
hidratador start M-1001 --owner terminal-1
hidratador start M-1001 --owner terminal-2
```

```json
{
  "error": "task is IN_PROGRESS; expected READY or INBOX",
  "kind": "Conflict",
  "ok": false}
```

---

## How to propose a change

Open a [feature request](https://github.com/hamanakam1/el-hidratador/issues/new/choose) before
you write the code. The form asks for the problem, the proposed solution in terms of observable
behavior, the alternatives you considered, the pipeline layer it touches, and — the one people
skip — the **privacy and telemetry impact**.

State explicitly whether the change adds network access, telemetry, local state, or credential
handling. The core stays standard library only and does not phone home, and a proposal that
quietly adds any of those things is a much harder conversation than one that names them up front.

A proposal that can be measured is easier to accept than one that lists features. "Repeated
context is re-expanded by hand for every handoff, and the repeated part is not observable in the
ledger" is a problem statement. "Add a cache" is a solution.

Small pull requests are welcome without an issue first, as long as they do one thing.

---

## How to claim an issue

Comment on the issue before you start, saying what you intend to do. That is enough to claim it;
there is no assignment queue to wait for.

The claim is a scope, in the same sense the ledger uses the word. Say which part you are taking:

> I am taking the CLI surface for this. I will add the `schema --validate` round trip and the
> matching test, and I will not touch the adapter files.

That keeps two people from writing the same function and keeps a change inside the boundary it
claims. If you are working inside El Hidratador itself, the scope keys are the module paths,
which the repository labels `area/ledger`, `area/cli`, `area/context`, `area/dag`, `area/sandbox`,
`area/github`, `area/hardware`, `area/dashboard`, `area/docs`, `area/tests`, and `area/ci`.

If you start and then stop, say so on the issue and release the claim. A silent stall blocks
everyone else.

---

## Code of conduct

Participation is governed by the
[Contributor Covenant](https://github.com/hamanakam1/el-hidratador/blob/main/CODE_OF_CONDUCT.md),
version 2.1. It applies in every project space — issues, pull requests, discussions, wiki edits —
and when you are representing the project in public.

The short version: be decent to each other. Assume the other person is trying to help. Ask before
you assume. Take responsibility when you get something wrong.

To report a problem, use GitHub's private reporting on this repository, or open a confidential
report with the maintainers. Every complaint is reviewed, and the reporter's privacy is
respected.

---

## How decisions are made

The repository is small enough that decisions are made in the open.

- **Changes** are proposed as pull requests and reviewed. The pull request template asks for the
  behavior change, the ticket it belongs to, how it was verified, and a checklist of the
  boundaries it respects.
- **Architecture decisions** are recorded as ADRs under `docs/adr/`, in the standard shape:
  context, decision, consequences, and the alternatives that were considered. Each one has a
  status of `Accepted`.
- **Disagreement** is settled by the reasoning, not by seniority. If you think a decision is
  wrong, open an issue that states the case. If it turns out to be right, a new record with the
  next number is added — an accepted record is not edited, because what was believed at the time
  is worth more than a tidy file.
- **Security issues** are handled privately, through
  [SECURITY.md](https://github.com/hamanakam1/el-hidratador/blob/main/SECURITY.md), and are
  disclosed after a timeline is agreed with the reporter.

The rules in
[AGENTS.md](https://github.com/hamanakam1/el-hidratador/blob/main/AGENTS.md) and
[CONTRIBUTING.md](https://github.com/hamanakam1/el-hidratador/blob/main/CONTRIBUTING.md) are the
ones the code enforces. They are not aspirational, and a pull request that blurs one of them will
be sent back.

---

## How to become a maintainer

There is no application process. Maintainership grows out of sustained, good-faith work:

- You have opened pull requests that were merged, across more than one part of the project.
- Your reviews are thorough and kind — you read the change, you say what you actually think, and
  you explain why.
- You have answered questions in issues and discussions, or helped someone else past a wall.
- You understand the boundaries well enough that you can tell when a change is about to break one.

When that is true, the existing maintainer will ask. In the meantime, everything the maintainers
do is visible in the history: the issue triage, the review comments, the CI configuration, and the
changelog.

---

## Related pages

- [Support](https://github.com/hamanakam1/el-hidratador/blob/main/SUPPORT.md) — the same channels,
  in the repository
- [Development](development.md) — the toolchain, the test layout, and the review criteria
- [FAQ](faq.md) — the questions that come up most often
