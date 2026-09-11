---
title: Rust
description: Install the htomd crate and extract Markdown and metadata with Rust.
---

Requires Rust 1.98 or later. Uses Serde, Serde JSON, and URL; no HTTP client or
async runtime is included.

## Install

```sh
cargo add htomd
```

Or add the dependency directly:

```toml
[dependencies]
htomd = "0.1.1"
```

## Quickstart

```rust
fn main() {
    let html = "<article><h1>Tea</h1><p>Steep gently.</p></article>";
    let markdown = htomd::convert(html, htomd::Options::default());
    let document = htomd::extract(
        html,
        htomd::Options { url: Some("https://example.org/tea") },
    );

    assert_eq!(markdown, "# Tea\n\nSteep gently.\n");
    assert_eq!(document.metadata.title.as_deref(), Some("Tea"));
}
```

## API

```rust
pub fn convert(html: &str, options: Options<'_>) -> String;
pub fn extract(html: &str, options: Options<'_>) -> Document;
```

`Options` contains `url: Option<&str>`. Use `Options::default()` for no source
URL; `Some("")` preserves an explicitly empty URL. Inputs are valid UTF-8 through
Rust's `&str` type. The functions return values directly, with best-effort HTML
recovery and no network access.

| Result        | Fields                                                                                                        |
| ------------- | ------------------------------------------------------------------------------------------------------------- |
| `Document`    | `markdown: String`, `metadata: Metadata`, `diagnostics: Diagnostics`                                          |
| `Metadata`    | `title`, `author`, `description`, `language`, `published_time`, `url`, `canonical_url`: each `Option<String>` |
| `Diagnostics` | `strategy: Strategy`, `notes: Vec<String>`                                                                    |

These are owned structs with public fields. Missing metadata is `None` and
serializes as `null`. `Strategy` variants are `Semantic`, `Scored`, `Fallback`,
and `None`; Serde serializes them in lowercase. Results derive `Serialize`.

## Native behavior

Relative references use WHATWG URL resolution. List counters use ASCII decimal
syntax, whitespace follows Rust's Unicode rules, and JSON-LD rejects nonstandard
`NaN`/`Infinity` tokens. See the
[package README](https://github.com/jamiedavenport/htomd/tree/main/rust#dependencies-and-native-behavior)
for details and dependency costs.

See [shared behavior and limitations](/#what-to-expect) and the [CLI](/cli/).
