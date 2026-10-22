# ADR 0007: GitHub writes go through a reconciled outbox

## Status

Accepted

## Context

Publishing a comment to a GitHub issue is a write to a system this project does not control, over
a network, that can fail after the request was accepted but before the response was read. A
retried publish must not produce two identical comments on the same issue, because a duplicate
status comment is worse than no comment: it makes the issue harder to read and it erodes trust in
the automation. The write path also has to be reviewable before it happens, and a half-completed
run has to be resumable without guessing what already went out.

## Decision

Every GitHub write goes through an **outbox** that is reconciled before it is sent. Each entry
carries an idempotency key supplied by the caller and a hash of the body, and each published body
carries a marker comment: `<!-- hidratador:{key}:{digest} -->`. Before sending anything, the
adapter reads the issue's existing comments and looks for that marker. If the marker is already
there, the entry is marked `reconciled` and nothing is sent; if it is not, the body is posted and
the entry is marked `published`. Reusing a key with a different body is refused rather than
silently rewritten. Both `github-poll` and `github-publish` are dry runs until `--apply` is
passed, and the `gh` CLI owns authentication — this package never reads, stores, or forwards a
token.

## Consequences

### Accepted benefits

- A repeated run never double-posts, which is the failure mode that matters most for a comment
  that is written on a schedule.
- The idempotency key is the caller's own token, so the caller already knows how to make its own
  operations repeatable; the package does not have to invent a key scheme.
- A partially completed run resumes cleanly, because the marker on the issue is the source of
  truth rather than the local outbox state.
- The marker is visible to a human reading the issue, so a comment can be traced back to the
  operation that produced it.
- The refusal on a changed body forces a decision instead of making one silently.

### Accepted costs

- Publishing costs an extra read of the issue's comments before every send, so the adapter makes
  more API calls than a naive write would.
- The marker is part of the published body, so the body hash covers it, and a body edited by hand
  after publication no longer matches its own marker.
- The outbox is a second database, at `~/.el-hidratador/github.sqlite` by default, and it has to
  be backed up and cleaned up alongside the ledger.
- The marker relies on GitHub preserving HTML comments in issue comments. It does today, but it
  is a property of another system that this project does not control.

## Alternatives considered

- **Write directly and hope the retry does not happen.** Rejected: the failure mode is a
  duplicate comment, which is exactly the outcome the outbox exists to prevent.
- **Detect duplicates by searching the comments for the body text.** Rejected: it is fuzzy, it
  breaks the moment the text is edited or reformatted, and it cannot distinguish "the same
  operation ran twice" from "someone wrote a similar sentence".
- **Rely on a server-side idempotency key.** Rejected: the GitHub issue-comment API has no such
  parameter, so there is nothing to rely on.
- **Post to a separate tracking issue instead of the issue itself.** Rejected: it moves the
  evidence away from where a reader will look for it.
- **Use an at-most-once queue and drop anything that fails.** Rejected: it silently loses
  messages, which trades a visible duplicate for an invisible omission.

## Related pages

- [GitHub sync](https://github.com/hamanakam1/el-hidratador/blob/main/docs/github-sync.md) — the
  outbox, the marker, and the reconciliation algorithm
- [Security](https://github.com/hamanakam1/el-hidratador/blob/main/docs/security.md) — the `gh`
  boundary and the write path
