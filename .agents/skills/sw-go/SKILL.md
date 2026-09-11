---
name: sw-go
description: Create or update an idiomatic Go port of a Python reference, preserving its I/O contract.
---

# Python → Go

## Workflow

- Use the codebase map or run `sw-explore`; read the reference, target, tests, and uncommitted changes before editing.
- Follow repository instructions and dependency limits. Select Go from Shipwright `targets`, accepting legacy singular `target` configurations.
- Preserve the product's I/O contract, not a one-to-one implementation mapping. Use native APIs and document justified platform differences in shared conformance fixtures. Do not recreate Python internals to mask those differences.
- Prefer the standard library. Justify external dependencies by the maintenance burden or correctness they avoid; zero dependencies is not a reason to vendor a runtime.
- Establish provenance before reusing third-party code or data; retain applicable attribution. Keep runtime packages independent and infrastructure changes within scope.

## Language mappings

- Dataclasses become structs; keyword arguments become typed options. Export Go-style names while preserving wire-format keys.
- Use pointers or explicit optional types when absence differs from an empty value. Distinguish nil slices from empty arrays in JSON.
- Return errors for actual failure paths; malformed best-effort input need not become an error. Typed APIs can eliminate Python type errors. Do not use panic as routine error handling.
- Use ordinary owned results and document their mutation behavior. Frozen Python objects do not require getter-only Go APIs. Avoid unintended aliasing of maps, pointers, and slice backing arrays.
- Use maps for lookup and slices for order. Never let randomized map iteration decide output ordering or tie-breaking. Preserve node identity with pointers or stable IDs where required.
- Strings contain bytes, not guaranteed UTF-8. Validate decoded-text boundaries and use runes for character counts. Check native Unicode whitespace, regex, and URL behavior explicitly.
- Use `math/big` when the contract requires unbounded integers. Translate Python truthiness, floor division, and negative remainder deliberately.
- Keep synchronous work synchronous. Add goroutines or contexts only when cancellation or concurrency serves the actual API.

## Tooling and validation

- Use Go modules, declare the supported Go version, and retain `go.sum` when dependencies require it. Do not introduce a lockfile for a dependency-free module.
- Run gofmt checks, `go vet`, native tests, builds, and isolated package/CLI checks. Reuse repository entry points.
- Preserve one authoritative set of conformance fixtures at repository root. Missing required implementations must fail, and exceptions must be narrow and explained.
- Test ownership, optional values, errors, Unicode, deterministic ordering, and deep traversal where these affect behavior; avoid tests mirroring implementation details.
- Native binaries are platform-specific. Build them per supported platform and reuse them for artifact checks. Keep release packaging separate from test compilation.
- For modules in repository subdirectories, account for the subdirectory prefix in release tags. Do not publish or create commits unless requested.
- Report checks run and any limitations. Do not create synchronization-state files.
