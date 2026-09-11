# htomd for Rust

Extract Markdown and metadata from decoded HTML without network access.
Requires Rust 1.98 or newer, using edition 2024.

```toml
[dependencies]
htomd = "0.1.1"
```

```rust
let document = htomd::extract(
    "<article><h1>Tea</h1></article>",
    htomd::Options { url: Some("https://example.org/article") },
);
assert_eq!(document.markdown, "# Tea\n");
```

`extract(&str, Options)` returns an owned `Document`; `convert` returns its
Markdown as a `String`. Use `Options::default()` without source context. Results
are ordinary owned structs with public fields. Missing metadata uses
`Option<String>` and serializes as null; `Some("")` retains an empty source URL.
Malformed HTML is recovered best-effort. No URL is fetched.

Install the CLI with `cargo install htomd`. It reads UTF-8 stdin through
`htomd convert` or `htomd extract`, with optional `--url URL`. Help and version
never read stdin. Argument errors exit 2; input/output errors exit 1, and broken
pipes are quiet.

## Dependencies and native behavior

Three direct dependencies avoid maintaining JSON and URL parsers:

- `serde` with derives serializes the public structs with stable wire names.
- `serde_json` parses JSON-LD and produces JSON output. Its `arbitrary_precision`
  feature prevents unrelated large JSON numbers from rejecting useful metadata.
- `url` supplies WHATWG URL parsing and resolution. Its transitive IDNA and ICU
  Unicode support is the main dependency cost. No HTTP client or async runtime
  is included, and optional URL Serde integration is disabled.

The initial lockfile resolves 40 dependency packages, including compile-time
proc macros. Inspect the current graph with `cargo tree --locked`; the committed
lockfile makes repository and CLI builds reproducible. Library consumers resolve
versions using Cargo's normal dependency rules.

Shared fixtures record native whitespace handling (Python-only control
separators and BOM are retained), ASCII list-counter syntax, WHATWG relative URL
normalization, and rejection of nonstandard NaN/Infinity JSON tokens. JSON-LD's
native recursion limit remains enabled. No Python runtime internals are vendored.
HTML entity data comes from WHATWG; see NOTICE. Regenerate it at development time
with `python tools/generate_rust_entities.py`; packaged code needs only its own
static table. Decimal list counters preserve arbitrary precision without an
additional crate. Arena node IDs keep traversal and destruction stack-safe.

## Development

From the repository root run `mise run setup`, `mise run build`, and
`mise run check`. Native tests use the shared root fixtures. The `.crate` includes
unit tests and documentation examples; repository fixture tests remain outside
the package. Packaging and isolated consumer checks run through the root tooling.
