# Contributing

Follow the [README setup](README.md#development), then install the hooks:

```sh
mise exec -- uv run --locked pre-commit install
mise run hooks
mise run check
```

Hooks apply Ruff safe fixes and formatting to staged Python files, excluding
fixtures. Review hook changes before staging. Checks include lint, formatting,
strict mypy, offline tests, and workflow validation.

Keep runtime dependencies empty and add focused regressions for behavior changes.
See the [fixture guide](tests/fixtures/real/README.md) when updating snapshots.

## Releases

```sh
mise run check
mise run build
mise exec -- uv run --locked twine check dist/*
```

Release checks require 120 human-reviewed pages and 40 exact expectations;
that review is incomplete.

PyPI publishing is disabled. The release workflow is parked at
[.github/release.yml.disabled](.github/release.yml.disabled), outside the Actions
workflow directory. Pushes, tags and GitHub releases cannot publish packages.
Keep it disabled until a PyPI release is explicitly planned. CI remains enabled.
