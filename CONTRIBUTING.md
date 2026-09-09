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
mise exec -- env RELEASE_TAG=v0.1.0 uv run --locked python tools/check_release.py
```

See [RELEASING.md](RELEASING.md) for the manual version, changelog, tag, and
GitHub Release steps.

The [release workflow](.github/workflows/release.yml) publishes to PyPI when a
GitHub Release is published. It runs CI, verifies the tag matches the package
version, validates both distributions, and uploads them to PyPI and the GitHub
Release. Pushing a branch or tag alone does not publish a package.
