# Pure-Python optimization results

Five alternating rounds on Apple M5 Max, Python 3.14.7, macOS ARM64,
using all 115 existing offline snapshots and the same public `htomd.convert()` call.
Both versions were installed from wheels in separate fresh environments.

| Metric | Before | After | Change |
| --- | ---: | ---: | ---: |
| Median corpus seconds | 1.732 | 1.250 | 27.9% less time |
| Pages/second | 66.4 | 92.0 | 38.6% more throughput |
| Peak process RSS MiB | 127.17 | 127.67 | Essentially unchanged |
| Runtime Python source lines | 1,138 | 1,175 | +37 (3.3%) |
| Runtime Python source bytes | 38,440 | 39,972 | +1,532 (4.0%) |
| Runtime dependencies | 0 | 0 | Unchanged |

The five round medians span 1.713–1.825 seconds before
and 1.240–1.275 seconds after. These are observed ranges, not confidence intervals.
The earlier published baseline was 1.751 seconds; the comparison above remeasures
both versions together rather than attributing all run-to-run variation to code.
See [comparison data](optimization.json), the [original full run](macos-arm64-baseline.json),
and the [latest six-library comparison](macos-arm64.md).

In that full rerun, htomd took 1.260 seconds and html2text took 1.262 seconds,
with overlapping round ranges: effectively tied. htomd was 1.94× faster than
markdownify and 2.58× faster than Trafilatura. The two Rust-backed converters
remained about 5.8× and 7.7× faster than htomd. Default extraction behavior differs
between libraries, so these are not equivalent-output or quality comparisons.

## What changed

- Accumulate the nine statistics fields explicitly instead of dynamic attribute access.
- Reuse subtree statistics after cleaning, recomputing only changed nodes and ancestors.
- Filter the private parsed tree in place after explicit metadata has been read.
- Replace per-node generator construction with simple iterative tree walks.
- Compile hint patterns and construct constant tag sets once; avoid work on absent hints.
- Read JSON-LD during the metadata scan and avoid searching for author/date fallbacks
  when explicit values already exist.
- Skip rendering descendants inside literal code elements, whose serializers use raw text.
- Avoid temporary neighbor lists and repeated parser scope-set allocations.

These changes add **37 net lines across five runtime files**, with no new functions,
classes, public API, dependencies, native extensions or persistent content caches.
Both versions contain 57 functions and six classes.
Source-line counts include blank lines and comments across `src/htomd/*.py`;
tests, benchmark code, documentation and measurements are excluded.

Most changes simplify repeated work. Two invariants need care: statistics for a
removed node's ancestors must be invalidated before selection, and explicit metadata
must be read before filtering the tree. The new cleanup tests compare cached evidence
with fresh accumulation; metadata tests cover precedence and cleanup. Literal-code
rendering has a focused regression test. The parser and extraction heuristics remain
the same; there is no faster mode that drops extraction work.

## Verification

The optimized implementation matched the original Markdown, metadata and diagnostics
exactly for all 115 snapshots with and without source URLs (230 cases), plus 2,000
seeded generated documents covering nested and unclosed markup. Existing captured
outputs and fixtures were not changed. Five new regression cases cover changed
ancestor evidence, JSON-LD precedence and nested code markup.

Development fixtures were used for quick timing trials. Final reported measurements
use the full corpus, without profiling. No page-specific shortcuts were introduced.
The implementation remains pure Python with `dependencies = []`.

Final validation passed: 470 tests on each of Python 3.12.14, 3.13.15 and 3.14.7
(one existing unreviewed-fixture skip per version), Ruff lint/format checks, strict
mypy, generated-report consistency and both distribution builds. Isolated wheel
and source-distribution installations passed without competitor packages or runtime
dependencies; both archives also passed Twine validation.

## Reproduce the comparison

The original runtime source is at revision
`8f7c57f1d0487fb8dcf32e0cc2a5f4930601c8e9`. Build that revision and the optimized source
into separate wheel directories using `mise exec -- uv build --wheel --no-sources`.
Create two Python 3.14.7 environments with `uv venv`, then install the corresponding
wheel into each with `uv pip install --python <environment>/bin/python --no-deps <wheel>`.
The JSON records both source hashes and the actual wheel hashes used here.

For each of five rounds, invoke the existing benchmark worker once per environment:

```sh
<environment>/bin/python -I -B tools/benchmark/worker.py htomd speed <output.json>
```

Use before/after order on odd rounds and after/before on even rounds. Workers use
one warm-up corpus pass, at least five measured passes, at least two timed seconds,
and garbage collection enabled. Apply a 300-second subprocess timeout. Compute each
round's median, then the median of those five medians. Run three additional workers
per environment with `rss` instead of `speed` for memory. The comparison JSON retains
per-document timings and warm-up diagnostics; each full benchmark JSON retains every
pass's output diagnostics as well. Timing excludes loading, imports and bookkeeping.

Run `python -m tools.benchmark.run` and regenerate the main report as described in
[the benchmark instructions](../README.md) to refresh the competitor comparison.
