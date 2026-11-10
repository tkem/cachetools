# Copilot Instructions for cachetools

Project conventions (stack, commands, code style, architecture constraints, boundaries
and git workflow) live in [`AGENTS.md`](../AGENTS.md). This file adds only the code
review process.

## Code Review

- Reviews **amend `.github/copilot-review.md` in place** (header: date, commit, CI
  status, coverage); never new files, dated sections, a per-commit change summary or
  a list of what was verified (git history is the record).
- Findings are tables ordered High, Medium, Low, Info with columns
  `# | Priority | Location | Finding`; renumber after changes; cross-reference as
  "Code #3". **Resolved issues are removed**, never marked resolved.
- Name the reviewed tree by its base commit (hash and subject, release tag if any)
  plus "this review commit", never by the review commit's own hash, which changes
  with every rebase; replace stale hashes instead of narrating history. List only
  interpreter versions actually run.
- Keep it brief: under 100 lines, one or two sentences per row, numbers only where
  they decide something, current snapshot only (no comparisons with earlier releases).
  Drop "no issues" sections and Info rows that only restate accepted design. Record
  settled matters under *Maintainer Decisions*. A review changes nothing; fix only
  when asked.
- `CHANGELOG.rst` is reviewed, never edited: entries are imperative one-liners with
  ``double backticks`` and no issue numbers, tagged "(breaking change)", "(potentially
  breaking change)" or "(broken since vX.Y.Z)". Every `Fix #123` commit and every
  user-visible behavior change needs an entry; docs-only, test-only and speed-up work
  is one "Minor/Various ... improvements." line each; two blank lines between releases.
- Verify before reporting: probe behavior with scripts, compare cache semantics with a
  random trace against the base release, and measure as *Testing* in `AGENTS.md`
  prescribes. Record cache state with `list(cache)`: `items()` and `values()` read
  through `__getitem__` and count as a use of every item. `LFUCache` ties discard the
  least recently used key (documented since 7.3), so check it against a model.
- Whatever could not be verified must show up: mark the finding, figure or status as
  unverified where it stands (e.g. "unmeasured", "not run on 3.13", "CI not run for
  this commit") and say why. Never state an unchecked claim as fact or leave it out.
- This file and the review differ per branch. After rebasing a development branch
  onto a release, make sure both are still that branch's versions, not the release's.

## Maintainer Decisions (do not re-raise)

- Pickling caches is documented only as working within one release; the format stays
  unstable. Pickling and deep-copying objects that use `@cachedmethod` is supported
  (#417) and must keep working.
- `copy.copy()` of an instance with an active `@cachedmethod` wrapper shares the
  wrapper; accepted.
- The wrapper stored in `obj.__dict__` shadows later changes to the class attribute
  (e.g. `mock.patch.object`) for instances that already used the method, and keeps
  the instance in a reference cycle; accepted and deliberately not documented.
- Stacking `@cachedmethod` decorators is unsupported and untested.
- Class access to `@cachedmethod` (`Cls.method(obj, ...)`) builds and discards a
  wrapper per call; accepted.
- A `condition` must provide the full `threading.Condition` interface, although only
  `wait()` and `notify_all()` are called. Do not propose relaxing the protocol.
- A `condition` passed together with a separate `lock` must be created with that
  lock; this is enforced by documentation only, not at decoration time.
