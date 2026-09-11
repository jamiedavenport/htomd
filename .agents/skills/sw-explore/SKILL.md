---
name: sw-explore
description: Map a reference codebase and its behavioral contract before creating or updating a language port.
---

# Explore a codebase

- Read repository instructions and `shipwright.toml`.
- Select the requested entry in `targets`; accept legacy singular `target` configurations.
- Identify source and target packages, versions, runtimes, and dependency limits.
- Trace public APIs and CLI commands through their modules and data types.
- Read tests and fixtures; separate the product contract from incidental source-runtime behavior and assumptions.
- Identify shared inputs and boundaries for comparing implementations.
- Flag language, standard-library, and environment semantics that affect output. Identify native target alternatives before proposing compatibility code or vendored runtime internals.
- Identify actual reused third-party material and its provenance; do not infer licensing files from the source language alone.
- For updates, inspect the current reference and target, including uncommitted work.
- Trace setup, format, lint, typecheck, test, build, and packaging commands through their callers. Flag missing checks, repeated builds, duplicated fixtures, and tests running on a different runtime from the published package.
- Distinguish changes needed for the port from optional CI, release, and repository restructuring.
- Return a short, linked map of behavior, architecture, checks, and compatibility questions.
- Leave implementations unchanged. Save the map only when asked.
