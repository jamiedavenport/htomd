---
name: sw-rust
description: Create or update an idiomatic Rust port of a Python reference, preserving its I/O contract.
---

# Python → Rust

## Workflow

- Use the codebase map or run `sw-explore`; read the reference, target, tests, and uncommitted changes before editing.
- Follow repository instructions and dependency limits. Select Rust from Shipwright `targets`, accepting legacy singular `target` configurations.
- Preserve I/O behavior through idiomatic Rust, not a one-to-one implementation mapping. Document justified native-runtime differences in shared fixtures rather than masking them with Python compatibility code.
- Prefer standard-library facilities and narrowly enabled maintained crates where they avoid substantial parser or protocol maintenance. Explain direct and transitive dependency costs; do not vendor runtime internals to claim zero dependencies.
- Establish provenance before reusing code or data, preserve applicable attribution, and keep runtime packages independent. Extend existing infrastructure only within scope.

## Language mappings

- Dataclasses become structs, variants become enums, `None` becomes `Option`, and recoverable failures become `Result`. Preserve empty versus absent values and wire-format names.
- Borrow inputs with `&str` or slices when useful; return owned results. Ordinary public structs and Rust's ownership rules are appropriate even when Python results are frozen. Avoid unnecessary clones or getter-only APIs that merely emulate Python.
- Typed inputs can eliminate Python type errors. Recover malformed best-effort input without panicking; reserve `Result` for remaining meaningful failures.
- Choose `Vec`, maps, and sets according to identity and ordering requirements. Do not use hash iteration for tie-breaking. For mutable parent-linked trees, consider a `Vec` arena with stable node IDs instead of cyclic `Rc<RefCell<_>>` ownership.
- Strings are UTF-8; byte offsets must be character boundaries. Use character iteration for semantic counts. Check Unicode whitespace, regex, integer ranges, division, and URL behavior explicitly.
- Preserve numeric precision where it affects output. A bounded operation such as decimal increment may justify a small helper instead of a general arbitrary-precision dependency.
- Prefer iterative traversal for deeply nested inputs, including destruction: a recursive owned tree can overflow during drop even if its walk is iterative.
- Keep synchronous APIs synchronous. Avoid async runtimes, `unsafe`, and input-dependent `unwrap` unless the actual contract requires them or a documented invariant proves safety.

## Tooling and validation

- Use Cargo, declare edition and minimum supported Rust version, and retain the lockfile for reproducible CLI builds. Minimize crate features.
- Run rustfmt checks, Clippy, native and documentation tests, builds, and isolated `.crate`/CLI checks through existing repository entry points.
- Keep authoritative conformance fixtures at repository root. Missing implementations must fail; intentional differences must be narrow and explained.
- Test optional values, ownership, Unicode, deterministic ordering, error handling, and deep traversal/drop where they matter. Do not disable JSON recursion limits without a stack-safe alternative.
- Build native artifacts per platform and reuse them for artifact validation; distinguish test compilation from release packaging.
- Ensure package data and applicable license notices survive packaging. Account for registry setup when publishing is in scope; do not publish or create commits unless requested.
- Report checks run and limitations. Do not create synchronization-state files.
