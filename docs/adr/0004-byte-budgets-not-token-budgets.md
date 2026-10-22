# ADR 0004: Budgets are enforced in bytes, not in tokens

## Status

Accepted

## Context

A hydrated packet has to fit a context window, so it needs a budget. The obvious unit is tokens,
because that is what a model provider bills and counts. But this package does not call providers
and does not know which model will consume the packet, and the answer changes with the model: the
same text is a different number of tokens under every tokenizer, and the set of tokenizers is
large and moving. A budget expressed in tokens would therefore be either approximate, or accurate
only for a model this project cannot verify it is talking to.

## Decision

Budgets are enforced in **bytes**, exactly. `Ledger.pack()` measures the JSON encoding of the
packet; `context_expander.build_packet()` measures the packet plus the rendered prompt. Both add
attached context in priority order, re-measure after each addition, and report every blob that
did not fit in `omitted` with a reason of `byte_budget` or `expired`. Token counts appear only as
estimates and are labelled as such: `token_estimate` is a character-count heuristic, and
`token_count` is always `null`. The task's own `token_budget` is a separate concept — a ceiling on
the tokens a worker reports — and it is cumulative across attempts.

## Consequences

### Accepted benefits

- The budget is exact and reproducible. The same packet against the same ceiling always produces
  the same result, on any machine and in any locale.
- The budget is tokenizer-independent, so it does not silently change meaning when the consumer
  swaps models.
- The measurement is a plain byte count of an encoded document, which is cheap, deterministic,
  and easy to explain in an error message.
- Nothing in the output can be mistaken for provider metering. A `null` token count is a truthful
  value; an estimate presented as a measurement is not.

### Accepted costs

- A byte budget does not directly bound a provider's tokenisation. Four bytes per token is a
  useful approximation and nothing more, so the byte ceiling and the real context window are
  related but not equal.
- Two budget implementations exist and they are not identical: `pack` measures the packet alone,
  `expand` measures the packet plus the prompt. `expand` is therefore the stricter of the two,
  and this is a sharp edge for anyone reasoning about a single number.
- The worker's reported token count and the byte budget are separate numbers with separate
  meanings, which takes explaining.

## Alternatives considered

- **Count characters instead of bytes.** Rejected: not exact for non-ASCII text, and the encoded
  length is what actually reaches a transport.
- **Use a characters-per-token ratio as the primary budget.** Rejected: the ratio is an
  approximation of an approximation, and enforcing an approximation as a hard limit is worse than
  enforcing a real unit.
- **Ship per-model tokenizer tables.** Rejected: it means depending on a provider's tokenizer
  library, keeping up with every model release, and being wrong whenever a new model appears.
- **Count tokens locally with a tokenizer.** Rejected: it adds a dependency and a model download to
  the core, which is precisely what ADR 0001 rules out.
- **No budget at all.** Rejected: without a ceiling, the packet grows with every attached context
  blob until the consumer refuses it, and the failure happens somewhere else, with less
  information.

## Related pages

- [Context and packets](https://github.com/hamanakam1/el-hidratador/blob/main/docs/context-and-packets.md)
  — the budget and the omission list
- [Architecture](https://github.com/hamanakam1/el-hidratador/blob/main/docs/architecture.md) — the
  two budget implementations
