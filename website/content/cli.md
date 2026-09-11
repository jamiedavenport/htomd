---
title: Command line
description: Convert UTF-8 HTML from stdin to Markdown or structured JSON.
---

All four implementations provide the same commands and JSON field names.

## Install

Choose one implementation:

| Implementation | Command                                               |
| -------------- | ----------------------------------------------------- |
| Python         | `uv tool install htomd`                               |
| TypeScript     | `npm install -g @jamiedavenport/htomd`                |
| Rust           | `cargo install htomd`                                 |
| Go             | [Install from the checkout](/go/#install-from-source) |

With the Python package installed, `python -m htomd` also works. You can run the
Node CLI without a global installation using `npx @jamiedavenport/htomd`.

## Convert HTML

```sh
cat page.html | htomd convert > page.md
cat page.html | htomd extract > page.json
curl -fsSL https://example.com/article | htomd convert --url https://example.com/article
```

Both commands read UTF-8 HTML from stdin until EOF, stripping an initial BOM.
They accept no file arguments; use pipes or redirection. `--url URL` supplies
source context and resolves relative references. In the last example, `curl`
fetches the page; htomd does not.

`convert` writes Markdown. `extract` writes indented JSON with this shape:

```json
{
  "markdown": "",
  "metadata": {
    "title": null,
    "author": null,
    "description": null,
    "language": null,
    "published_time": null,
    "url": null,
    "canonical_url": null
  },
  "diagnostics": {
    "strategy": "none",
    "notes": []
  }
}
```

Absent metadata stays `null`. Strategy values are `semantic`, `scored`,
`fallback`, and `none`; notes describe extraction and recovery. The JSON keys
are the same across implementations, including `published_time` and
`canonical_url`.

## Help and errors

```sh
htomd --help
htomd help extract
htomd extract --help
htomd --version
```

Help and version commands do not read stdin. `htomd` with no command shows help.
`htomd version` is an alias for `htomd --version`.

| Exit code | Meaning                                                             |
| --------- | ------------------------------------------------------------------- |
| `0`       | Success, including help and version                                 |
| `1`       | Input/output error, including invalid UTF-8 or a broken output pipe |
| `2`       | Invalid arguments                                                   |

Errors go to stderr. Broken output pipes exit quietly. Malformed HTML alone is
not an error; see [shared behavior and limitations](/#what-to-expect).
