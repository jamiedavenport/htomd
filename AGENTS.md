## Shipwright

Shipwright is the skill-driven workflow for maintaining language ports in this repository.
Python (`python/src/htomd`) is the source of truth. Make behavior changes there first;
update TypeScript and future ports in a later pass when requested.

`shipwright.toml` identifies the source and current target. Use `sw-explore` to map
the behavioral contract and `sw-ts` to create or update the TypeScript port.
Preserve observable behavior while using target-language idioms; validate ports
against the shared conformance fixtures.
