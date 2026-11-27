# Copilot Instructions for cachetools

Project conventions (stack, commands, code style, architecture constraints, boundaries
and git workflow) live in [`AGENTS.md`](../AGENTS.md). This file adds only the code
review process.

## Code Review

- Reviews **amend `.github/copilot-review.md` in place** (header: date, commit, CI
  status, coverage); no new files, dated sections, change summaries or lists of what
  was verified. A review changes nothing; fix only when asked.
- Findings are tables ordered High, Medium, Low, Info with columns
  `# | Priority | Location | Finding` (no Location outside code and performance),
  renumbered after changes and cross-referenced as "Code #3". **Resolved issues are
  removed**, never marked resolved.
- Run `git status` and `git log` first: the maintainer rebases and amends, so the base,
  hashes and staged work change between looks. Name the reviewed tree by its base commit
  (hash, subject, release tag if any) plus "this review commit", never by the review
  commit's own hash. Cite no other commit hash anywhere in the review: a rebase
  invalidates it, so name the issue or the release instead. List only interpreters
  actually run, and say whether Actions ran for the reviewed code. Read a failed job's
  log and reproduce it with the interpreter version named there; report it even when it
  cannot be reproduced here, with what was tried.
- Keep it brief: under 100 lines, at most ten rows per section, one or two sentences per
  row, numbers only where they decide something, current snapshot only. Drop "no issues"
  sections and, when a section is over the limit, Info rows that only restate accepted
  design. Record settled matters under *Maintainer Decisions*. When rewriting a row,
  keep what the maintainer asked it to say (e.g. a finding's practical reach, or that a
  fix would be a potentially breaking change).
- `CHANGELOG.rst` is reviewed, and edited only when the maintainer asks: imperative
  one-liners with ``double backticks`` and no issue numbers, tagged "(breaking change)",
  "(potentially breaking change)" or "(broken since vX.Y.Z)", the latter checked against
  that release's tag. Every `Fix #123` commit and user-visible change needs exactly one
  entry (look for duplicates after a rebase); docs-only, test-only and speed-up work is
  one "Minor/Various ... improvements." line each; two blank lines between releases.
  Before a release, check that the heading has the date and matches `__version__`. Name
  a fix's side effects (e.g. a changed iteration order); the maintainer decides on the
  entry.
- Verify before reporting: probe behavior with scripts, compare cache semantics with a
  random trace against the base release, and measure with `.github/copilot-bench.py`,
  extending it for any new figure. Before calling a moved figure a change, rerun it and
  the base release in the same session: timed-cache hits differ by 20 ns and the
  1000-item rows by 15% between processes. After a speed-up, re-measure its rows (best
  of three runs) and date them. Record cache state with `list(cache)`, since `items()`
  and `values()` count as a use of every item. That only changes `LRUCache` in practice,
  so say which classes a finding really affects before proposing a fix or docs. Modify
  caches while iterating over them, too. Read comments against the code; a stale example
  is a finding. Find test gaps by reading the tests against the code and coverage (a fix
  commit that touches no test is one) and confirm each by reverting the code it calls
  unguarded for one run; run mutation tests only when asked. After a test refactor,
  compare test names and assertion counts per test with the base tree, then break a stub
  on purpose in both and compare pyright's error counts, since tests calling through
  `Any` or `**kwargs` check no stubs. Check that a new test fails without its fix under
  a timeout, since a loop bug hangs the suite; a test for a hang runs the call in a
  daemon thread and joins it with a timeout. Probe on PyPy whatever relies on an object
  being freed, and timed caches with a timer advancing on each call or read. Try a
  suggested fix as a temporary edit, time its variants, and probe every reader of the
  mapping protocol (`dict(cache)`, `update(cache)`, `values()`) with the real clock
  before reporting what it breaks. Check whether the last release had a finding: one
  caused by unreleased work is fixed in that work.
- Pickle (protocols 2 to 5, also with `pickle._Pickler`, #474; the obsolete protocols 0
  and 1 are unsupported, do not report them), copy and deep-copy caches in a used state,
  on the oldest supported Python too, and compare the clones' later evictions. Repeat
  with a timer object (also one defining `__deepcopy__`), a bound-method `getsizeof`,
  subclass attributes and `__slots__`. When a fix touches pickled state, load the
  previous release's pickles with it and the reverse, and keep the format where that is
  cheap.
- Probe decorators with awkward callables: one without `__qualname__` (a
  `functools.partial`), a parameter named `self`, other decorators stacked on top.
- Issue text for a fix, when asked for: a title, a minimal example with its output, the
  cause in a sentence or two, the releases it reproduces in ("not a regression" if it
  never worked) and the expected behavior. Keep it short, one long line per paragraph.
- Verify a reported issue in three steps: the mechanism in the code, the reporter's
  script on the interpreters at hand (say when the reported version is not installed),
  and the implied fix applied temporarily with the suite and the measurement, then
  reverted. Report its side effects, too. Docs wording for a measured effect names the
  mechanism and hedges the size ("slightly faster"); the figures stay in the review.
- Docs promise only what is meant to last: leave implementation details unspecified
  (e.g. modifying a timed cache while iterating), name the exact scope ("instance
  methods"), skip what is obvious to a developer, keep each decorator's section
  self-contained and write two sentences instead of joining them with a semicolon.
  Before a release, soften new wording that a planned change would contradict. Before
  proposing a fix, look for an issue or PR, closed ones included.
- Keep probe scripts, logs and old trees in `.cache/tmp/` inside the workspace, never
  in `/tmp`, and remove it when done. Exception: pyright skips files under `.cache/`
  and reports "0 errors", so check stubs with a temporary file in the repository root
  (`tox -e pyright -- <file>`) that contains one deliberate error as a control. A
  worktree there is checked by running `tox -e pyright` inside it, in a subshell.
- Mark whatever could not be verified where it stands ("unmeasured", "not run on
  3.13", "CI not run for this commit") and say why. Never state an unchecked claim as
  fact or leave it out.
- This file and the review differ per branch; after a rebase onto a release, make
  sure both are still this branch's versions, and check `git stash list` and the last
  commit for findings another session dropped without a fix.

## Maintainer Decisions (do not re-raise)

- Cache subclasses that define `__slots__` are unsupported: a shallow copy lacks the
  slot values, and deep-copying or pickling such an `LFUCache` or `TTLCache` subclass
  raises `ValueError`. A subclass with state of its own provides its own `__copy__`
  (and `__setstate__`). Slots gain nothing: every `Cache` has a `__dict__` anyway.
- The docs need not say that `cache_lock` is the condition object when `condition` is
  given without `lock`: obvious to any developer, as the condition is the lock then.
- `dict(cache)` on a timed cache may raise `KeyError`: it lists all keys before the
  first lookup, which no class can prevent. The docs recommend `dict(cache.items())`.
