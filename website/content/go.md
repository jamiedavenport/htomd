---
title: Go
description: Build htomd from source and extract Markdown and metadata with Go.
---

Requires Go 1.27 or later. No external dependencies.

## Install from source

The Go port is available in the repository; it does not yet have a module release.
Clone the repository and use a local replacement in your Go project:

```sh
git clone https://github.com/jamiedavenport/htomd.git
# Run these in your application's Go module, adjusting the checkout path:
go mod edit -replace=github.com/jamiedavenport/htomd/go=./htomd/go
go get github.com/jamiedavenport/htomd/go
```

To install the CLI from the checkout:

```sh
go install -C htomd/go ./cmd/htomd
```

## Quickstart

```go
package main

import (
    "fmt"
    "log"

    "github.com/jamiedavenport/htomd/go"
)

func main() {
    html := "<article><h1>Tea</h1><p>Steep gently.</p></article>"
    source := "https://example.org/tea"
    document, err := htomd.Extract(html, htomd.Options{URL: &source})
    if err != nil {
        log.Fatal(err)
    }
    fmt.Print(document.Markdown) // "# Tea\n\nSteep gently.\n"
    fmt.Println(*document.Metadata.Title) // "Tea"
}
```

## API

```go
func Convert(html string, options Options) (string, error)
func Extract(html string, options Options) (Document, error)
```

Use `Options{}` without a source URL. `Options.URL` is a `*string`; `nil` means
absent and a pointer to `""` preserves an empty source URL. HTML and the supplied
URL must be valid UTF-8; otherwise the functions return an error. Malformed HTML
is recovered best-effort. No URL is fetched.

| Result        | Fields                                                                                               |
| ------------- | ---------------------------------------------------------------------------------------------------- |
| `Document`    | `Markdown string`, `Metadata Metadata`, `Diagnostics Diagnostics`                                    |
| `Metadata`    | `Title`, `Author`, `Description`, `Language`, `PublishedTime`, `URL`, `CanonicalURL`: each `*string` |
| `Diagnostics` | `Strategy Strategy`, `Notes []string`                                                                |

Results own their data and may be modified. Check metadata pointers for `nil`
before dereferencing them. Strategy constants are `Semantic`, `Scored`,
`Fallback`, and `None`. JSON serialization uses snake_case field names and
`null` for absent metadata.

## Native behavior

Go uses `unicode.IsSpace`, `html.UnescapeString`, `net/url`, and `encoding/json`.
List counters accept ASCII decimal digits with an optional sign. See the
[package README](https://github.com/jamiedavenport/htomd/tree/main/go#native-behavior)
for the resulting differences from Python.

See [shared behavior and limitations](/#what-to-expect) and the [CLI](/cli/).
