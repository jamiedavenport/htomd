# htomd

[Documentation](https://htomd.dev/typescript/)

Extract Markdown and metadata from decoded HTML, with no runtime dependencies
or network access. Requires Node 24 or later; the package is ESM.

```sh
npm install @jamiedavenport/htomd
```

```ts
import { convert, extract, type Document } from "@jamiedavenport/htomd";

const html = "<article><h1>Hello</h1><p>Readable text.</p></article>";
console.log(convert(html));

const document: Document = extract(html, {
  url: "https://example.com/article",
});
console.log(document.metadata.title);
```

`extract(html, options?)` returns `{ markdown, metadata, diagnostics }`.
`convert(html, options?)` returns its Markdown string. Both functions are
synchronous. HTML must be a primitive string; invalid HTML or URL argument types
throw `TypeError`. The optional `url` accepts a string, `null`, or `undefined`.
It provides source context and resolves relative references without fetching.
An empty URL remains an empty string in metadata.

Metadata fields are `title`, `author`, `description`, `language`, `publishedTime`,
`url`, and `canonicalUrl`. Missing values are `null`. Diagnostics contain a
`strategy` (`semantic`, `scored`, `fallback`, or `none`) and a `notes` array.
Results, nested metadata, diagnostics, and notes are frozen at runtime and
readonly in TypeScript. Nonempty Markdown ends with a newline; empty content
produces `""`.

## CLI

```sh
cat page.html | npx @jamiedavenport/htomd convert > page.md
cat page.html | npx @jamiedavenport/htomd extract > page.json
cat page.html | npx @jamiedavenport/htomd convert --url https://example.com/article
```

Both commands read strict UTF-8 from stdin, stripping an initial BOM. `convert`
writes Markdown and `extract` writes indented JSON. JSON retains the Python wire
keys `published_time` and `canonical_url`. Use `htomd --help`, `htomd help extract`,
or `htomd --version` after installing the CLI. Help and version do not read stdin.
Invalid arguments exit with status 2; input/output errors exit with status 1.
A broken output pipe exits quietly with status 1.

## Behavior and limitations

The maintained implementation follows the [Python reference](../python/src/htomd):
an ordered HTML tree, explicit metadata extraction, visibility and clutter
filtering, content scoring and sibling recovery, then iterative Markdown
serialization. Selected headings and local author/date information refine the
metadata. Deep trees do not depend on the JavaScript call stack.

Extraction is best-effort, intended for articles and documentation. It does not
execute JavaScript or implement browser layout. Simple tables use GFM; complex
tables become row/cell text. Active and unknown URL schemes are omitted.

The [shared conformance cases](../tests/fixtures/conformance.json) record runtime
differences explicitly:

- Whitespace normalization uses Unicode `White_Space`, with JavaScript trimming.
  Python-only control separators are not treated as ordinary whitespace; BOM
  characters at string boundaries are trimmed.
- List counters use `bigint`, preserving large decimal values. List attributes
  accept ASCII decimal digits; Python's Unicode digits and underscore syntax
  are not accepted.
- Relative references use Node's WHATWG `URL`, which may normalize host spelling,
  default ports, and paths differently from Python's URL joining. Absolute
  references retain their supplied spelling after validation.
- JSON-LD uses `JSON.parse`, so nonstandard `NaN` and `Infinity` tokens are rejected.
  These words inside valid JSON strings are preserved.

HTML entity names come from the WHATWG table; see [NOTICE](NOTICE) for its source
and attribution. Package code uses the repository's [MIT license](LICENSE).

## Development

From the repository root, `mise run setup`, `shipwright build`, and `mise run check`
install dependencies, build all four packages, and validate the existing artifacts.
Within this directory:

```sh
bun install --frozen-lockfile
bun run build
bun run lint
bun run format:check
bun run typecheck
bun run test
```

The compiler builds JavaScript and declarations into `dist/` and checks source
types. The separate `typecheck` command checks tests against those declarations.
Tests run on Node and read the root fixtures without making package-local copies.
`bun pm pack` builds once through `prepack`; test and package-check commands never
rebuild. Distribution checks validate the packed tarball in an isolated consumer;
conformance checks compare all four installed CLIs on synthetic, edge, and
saved-page fixtures. See the root README for the separate packaging steps.
