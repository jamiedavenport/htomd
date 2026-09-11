---
title: TypeScript
description: Install the ESM htomd package for Node and use its typed API.
---

Requires Node 24 or later. The package is ESM and has no runtime dependencies.

## Install

```sh
npm install @jamiedavenport/htomd
```

## Quickstart

```ts
import { convert, extract } from "@jamiedavenport/htomd";

const html = "<article><h1>Tea</h1><p>Steep gently.</p></article>";
const markdown = convert(html);
const document = extract(html, { url: "https://example.org/tea" });

console.log(markdown); // "# Tea\n\nSteep gently.\n"
console.log(document.metadata.title); // "Tea"
```

## API

```ts
convert(html: string, options?: ExtractOptions): string;
extract(html: string, options?: ExtractOptions): Document;
```

Both functions are synchronous. `ExtractOptions` has one optional `url` field,
accepting a string, `null`, or `undefined`. It supplies context without fetching.
An explicitly empty URL stays `""` in metadata. Invalid HTML or URL argument
types throw `TypeError`.

The package exports the `Document`, `Metadata`, `Diagnostics`, and
`ExtractOptions` types:

| Result        | Fields                                                                                                      |
| ------------- | ----------------------------------------------------------------------------------------------------------- |
| `Document`    | `markdown: string`, `metadata: Metadata`, `diagnostics: Diagnostics`                                        |
| `Metadata`    | `title`, `author`, `description`, `language`, `publishedTime`, `url`, `canonicalUrl`: each `string \| null` |
| `Diagnostics` | `strategy`: `"semantic"`, `"scored"`, `"fallback"`, or `"none"`; `notes: readonly string[]`                 |

Results, nested objects, and notes are readonly and frozen at runtime. Missing
metadata is `null`. The JavaScript API uses camelCase; the CLI's JSON uses
`published_time` and `canonical_url`.

## Native behavior

Relative URLs use Node's WHATWG `URL`. Whitespace follows JavaScript's Unicode
rules, list counters accept ASCII decimal digits, and JSON-LD uses `JSON.parse`.
These can differ from Python on edge cases; the
[package README](https://github.com/jamiedavenport/htomd/tree/main/typescript#behavior-and-limitations)
records the details.

See [shared behavior and limitations](/#what-to-expect) and the [CLI](/cli/).
