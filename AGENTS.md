## Shipwright

Shipwright is the skill-driven workflow for maintaining language ports in this repository.
Python (`python/src/htomd`) is the source of truth. Make behavior changes there first;
update TypeScript and future ports in a later pass when requested.

`shipwright.toml` identifies the source and maintained targets. Use `sw-explore`
to map the behavioral contract, then `sw-ts`, `sw-go`, or `sw-rust` for the
requested port. Preserve I/O behavior through idiomatic target-language APIs and
implementations. Record justified native-runtime differences in shared
conformance fixtures instead of masking them with compatibility layers.
