---
title: Python
description: Install htomd and extract Markdown and metadata with Python.
---

Requires Python 3.12 or later. No runtime dependencies.

## Install

```sh
python -m pip install htomd
```

## Quickstart

```python
import htomd

html = "<article><h1>Tea</h1><p>Steep gently.</p></article>"
markdown = htomd.convert(html)
document = htomd.extract(html, url="https://example.org/tea")

assert markdown == "# Tea\n\nSteep gently.\n"
assert document.metadata.title == "Tea"
```

## API

```python
htomd.convert(html: str, *, url: str | None = None) -> str
htomd.extract(html: str, *, url: str | None = None) -> htomd.Document
```

Both functions are synchronous. Pass decoded HTML, not bytes. `url` is
keyword-only and provides context without fetching anything. Incorrect HTML or
URL argument types raise `TypeError`. An explicitly empty URL remains `""` in
metadata.

`Document`, `Metadata`, and `Diagnostics` are exported, frozen dataclasses:

| Result        | Fields                                                                                                     |
| ------------- | ---------------------------------------------------------------------------------------------------------- |
| `Document`    | `markdown: str`, `metadata: Metadata`, `diagnostics: Diagnostics`                                          |
| `Metadata`    | `title`, `author`, `description`, `language`, `published_time`, `url`, `canonical_url`: each `str \| None` |
| `Diagnostics` | `strategy`: `"semantic"`, `"scored"`, `"fallback"`, or `"none"`; `notes: tuple[str, ...]`                  |

Missing metadata is `None`; published times remain strings. Use
`dataclasses.asdict(document)` when you need a dictionary for serialization.

See [shared behavior and limitations](/#what-to-expect), the [CLI](/cli/), and
the [Python source](https://github.com/jamiedavenport/htomd/tree/main/python/src/htomd).
