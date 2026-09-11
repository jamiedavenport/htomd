---
title: HTML to Markdown
description: Extract focused Markdown and metadata from HTML in Python, TypeScript, Go, and Rust.
sidebar:
  label: Introduction
---

htomd extracts readable Markdown and metadata from HTML. Give it a decoded HTML
string and get back the content, without navigation and other page clutter.

```html
<article>
  <h1>Tea</h1>
  <p>Steep gently.</p>
</article>
```

```markdown
# Tea

Steep gently.
```

Read the original announcement: [Introducing htomd](https://jamiedavenport.me/blog/introducing-htomd/).

## Get started

| Language                   | Runtime      | Installation                        |
| -------------------------- | ------------ | ----------------------------------- |
| [Python](/python/)         | Python 3.12+ | `pip install htomd`                 |
| [TypeScript](/typescript/) | Node 24+     | `npm install @jamiedavenport/htomd` |
| [Go](/go/)                 | Go 1.27+     | Build from the repository           |
| [Rust](/rust/)             | Rust 1.98+   | `cargo add htomd`                   |

Each implementation also provides the same [command-line interface](/cli/).
Python, TypeScript, and Go have no runtime dependencies. Rust uses Serde,
Serde JSON, and URL.

## What to expect

Use `convert` for Markdown, or `extract` for Markdown, metadata, and extraction
diagnostics. The language guides show their native signatures and result types.

- htomd never fetches a page or runs JavaScript. An optional source URL resolves
  relative links and images; fetch and decode HTML separately.
- Missing metadata stays absent. Empty content produces an empty string;
  nonempty Markdown ends with a newline.
- Diagnostics report the selection strategy: `semantic`, `scored`, `fallback`,
  or `none`, alongside notes about parsing and recovery.
- Malformed HTML is recovered best-effort. Articles and documentation work best;
  extraction can miss content or retain clutter.
- Browser layout, math, and SVG rendering are unsupported. Simple tables use
  GFM; complex tables become row/cell text. Unsafe URL schemes are omitted.

Python is the behavioral reference. Ports use native APIs and runtime behavior;
see the [shared conformance fixtures](https://github.com/jamiedavenport/htomd/blob/main/tests/fixtures/conformance.json)
for intentional differences.

## Project

htomd is [open source under the MIT license](https://github.com/jamiedavenport/htomd).
Visit the repository for [development instructions](https://github.com/jamiedavenport/htomd#development),
[releases](https://github.com/jamiedavenport/htomd/releases), and
[benchmarks](https://github.com/jamiedavenport/htomd/tree/main/tools/benchmark).
