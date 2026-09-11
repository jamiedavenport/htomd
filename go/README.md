# htomd for Go

Extract Markdown and metadata from decoded HTML, with no external dependencies
or network access. Requires Go 1.27.0 or newer.

```sh
go get github.com/jamiedavenport/htomd/go
go install github.com/jamiedavenport/htomd/go/cmd/htomd@latest
```

```go
import "github.com/jamiedavenport/htomd/go"

source := "https://example.org/article"
document, err := htomd.Extract(html, htomd.Options{URL: &source})
if err != nil {
    return err
}
fmt.Println(document.Markdown)
```

`Convert` returns `(string, error)`; `Extract` returns `(Document, error)`.
Use `Options{}` without a source URL. Inputs must be valid UTF-8; malformed HTML
is recovered best-effort. No URL is fetched. Result structs own their data and
may be modified. Missing metadata uses nil pointers; an explicitly empty source
URL is retained. JSON uses the Python wire names and null for missing metadata.

The CLI reads UTF-8 stdin: `htomd convert`, `htomd extract`, and optional
`--url URL`. Help and version do not read stdin. Invalid arguments exit 2;
input/output errors exit 1, with broken pipes handled quietly.

## Native behavior

Shared conformance fixtures record intentional differences from Python:

- Unicode whitespace follows `unicode.IsSpace`; Python-only control separators
  remain literal, and BOM characters inside the library input remain literal.
- List counters use `math/big`, accept ASCII decimal digits with an optional
  sign, and preserve arbitrary precision. Unicode digits and underscores are
  not accepted.
- Entity decoding uses `html.UnescapeString`, including its behavior for legacy
  references in attributes and numeric control characters.
- Relative URLs use `net/url.ResolveReference`, preserving repeated path slashes
  and dropping empty fragments. Absolute references retain supplied spelling
  after validation. Go does not apply Python's Unicode netloc normalization check.
- JSON-LD uses `encoding/json` with `UseNumber`; nonstandard NaN and Infinity
  tokens are rejected. Invalid JSON-LD does not fail extraction.

The extraction pipeline follows Python: ordered parsing, metadata, filtering,
selection, refinement, and iterative Markdown rendering. Unsupported content and
best-effort extraction limitations are shared with the Python package.

## Development

From the repository root, run `mise run setup`, `mise run build`, and
`mise run check`. Native API tests use the authoritative root fixtures. Package
archives omit repository-only tests; isolated consumers are checked separately.
Go module releases use `go/vX.Y.Z` tags matching the root `vX.Y.Z` release commit.
