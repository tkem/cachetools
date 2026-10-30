# Copilot Instructions for cachetools

Project conventions (stack, commands, code style, architecture constraints, boundaries
and git workflow) live in [`AGENTS.md`](../AGENTS.md). This file adds only the code
review process.

## Code Review

- Reviews **amend `.github/copilot-review.md` in place** (header: date, commit, CI
  status, coverage, one *Verified* paragraph); never new files, dated sections or a
  per-commit change summary (git history is the record).
- Findings are tables ordered High, Medium, Low, Info with columns
  `# | Priority | Location | Finding`; renumber after changes; cross-reference as
  "Code #3". **Resolved issues are removed**, never marked resolved.
- Keep it brief: one or two sentences per row, numbers only where they decide
  something, current snapshot only (no comparisons with earlier releases). Record
  settled matters under *Maintainer Decisions*. A review changes nothing; fix only
  when asked.

## Maintainer Decisions (do not re-raise)

- Pickling caches is documented only as working within one release; the format stays
  unstable. Pickling and deep-copying objects that use `@cachedmethod` is supported
  (#417) and must keep working.
- `copy.copy()` of an instance with an active `@cachedmethod` wrapper shares the
  wrapper; accepted.
- Stacking `@cachedmethod` decorators is unsupported and untested.
- Class access to `@cachedmethod` (`Cls.method(obj, ...)`) builds and discards a
  wrapper per call; accepted.
- A `condition` must provide the full `threading.Condition` interface; `notify()` is
  reserved for future use. Do not propose relaxing the protocol.
