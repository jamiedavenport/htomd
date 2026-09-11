---
name: sw-ts
description: Create or update an idiomatic TypeScript port of a Python reference, preserving observable behavior.
---

# Python → TypeScript

## Workflow

- Use the codebase map or run `sw-explore`; read relevant source and tests before editing.
- Follow repository instructions and Shipwright configuration, versions, and dependency limits.
- For updates, inspect current source and uncommitted changes; preserve independent target edits.
- Implement the product's behavioral contract in maintained TypeScript. Use native APIs for incidental runtime behavior; document intentional differences in conformance cases.
- Do not copy source-runtime implementations to chase incidental compatibility. A zero-dependency requirement is not a reason to vendor a standard library. Identify the smallest implementation the product needs.
- A language port does not inherently need a new license or NOTICE. Add attribution only for material actually reused under terms that require it; preserve existing applicable notices. Establish provenance before copying third-party code or data.
- Keep CI, release workflows, and repository layout within the requested scope. Reuse existing tooling rather than scaffolding a second release system.

## Python → TypeScript idioms

- Keyword arguments → typed options objects; snake_case → camelCase. Preserve wire-format names.
- Dataclasses → interfaces or small classes; variants → unions, discriminated where useful.
- `None` → `null`; omitted options → `undefined`. Preserve empty values and defaults explicitly.
- Lists/tuples → arrays/readonly tuples; dictionaries → objects or Maps; sets → Sets.
- Preserve key identity, iteration order, and equality; avoid JavaScript truthiness shortcuts.
- Use `bigint` when integer precision matters; check Unicode, regex, whitespace, and URL semantics.
- Preserve errors, mutation, and sync/async behavior. Types and `readonly` do not enforce runtime checks or freezing.
- Prefer descriptive helper names, separate variable declarations, and braces around control flow. Write long user-facing text as readable multiline literals.
- Use non-null assertions only where an established invariant guarantees the value. Explain shared traversal/cache invariants at their construction point; do not add generic assertion wrappers around every lookup.

## Default tooling

- Use Bun for dependency management and scripts; commit its lockfile. Run tests on the declared production runtime, including Node for a Node package.
- Use Oxfmt for formatting and Oxlint for linting.
- Use TypeScript with `strict`, `noUncheckedIndexedAccess`, and `exactOptionalPropertyTypes` enabled.
- Emit JavaScript and declarations into `dist/`. Let a compiler build check source types; check tests against the emitted declarations without compiling the source repeatedly.
- If publishing source maps, embed their source content or include the referenced sources.
- Configure package exports, types, CLI bins when needed, and published files for an npm-ready package.
- Check the packed package outside the checkout; choose and declare its supported runtime explicitly.
- Honor explicit project requirements over these defaults; do not migrate existing tooling incidentally.

## Validation

- Keep native API tests and one authoritative set of shared conformance fixtures. Do not maintain identical fixture copies in each package; use shared test assets or an explicit generation step when standalone tests require copies.
- Give build, static checks, and tests distinct responsibilities. A convenience command may compose them, but each build should run once and tests of release artifacts must not rebuild them.
- When cross-platform CI is in scope, build platform-independent artifacts once and test the same artifacts on supported platforms. Run platform-independent static checks once.
- Extend existing validation entry points to include the port. Preserve established expectations; explain deliberate runtime differences rather than silently relaxing comparisons.
- Fail on missing required packages or failing suites; do not silently skip them.
- Run formatting, linting, typechecking, tests, build, and package checks; report checks not run.
- Report validation results. Do not create synchronization-state files.
- Keep runtime packages independent; shared test assets and conformance tooling belong at the repository root. Reuse small installation helpers when checks need the same setup.
