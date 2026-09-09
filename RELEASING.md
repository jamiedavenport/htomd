# Releasing htomd

Releases are prepared manually. Publishing a GitHub Release starts the
[release workflow](.github/workflows/release.yml), which runs CI, validates the
version and distributions, publishes to PyPI, and attaches the wheel and source
archive to the GitHub Release.

## Publishing identity

PyPI Trusted Publishing uses these settings:

| Field | Value |
| --- | --- |
| Project | `htomd` |
| Repository owner | `jamiedavenport` |
| Repository | `htomd` |
| Workflow filename | `release.yml` |
| GitHub environment | `pypi` |

Configure the publisher in the project's PyPI settings, or use an account-level
pending publisher for the first upload. No stored PyPI API token is needed.
See [PyPI's setup instructions](https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/).

## 1. Prepare the version and release notes

Set the version in `pyproject.toml` and refresh `uv.lock` if the version changed.
Update `CHANGELOG.md` with the release date and user-facing changes. Version
`0.1.0` is used in the examples below; substitute the new version for later
releases.

## 2. Validate, commit, and push

```sh
mise run check
mise run build
mise exec -- uv run --locked twine check dist/*
mise exec -- env RELEASE_TAG=v0.1.0 uv run --locked python tools/check_release.py
```

The build inspects package contents and installs both artifacts in separate
virtual environments to exercise the API and CLI. Keep exactly one wheel and
one source archive in `dist/`; move aside old-version artifacts before building.

Commit and push the release changes to `main`. Wait for all CI jobs to pass,
including the Windows package build. The release workflow must be included in
the commit you tag.

## 3. Create the tag and GitHub Release

From the clean, validated `main` checkout:

```sh
git tag -a v0.1.0 -m "htomd 0.1.0"
git push origin v0.1.0
gh release create v0.1.0 --verify-tag --title "htomd 0.1.0" --notes-file CHANGELOG.md
```

For later releases, pass a file containing only that version's changelog entry
as `--notes-file`. Pushing the tag alone does not publish. Publishing the GitHub
Release triggers the PyPI upload; saving a draft does not.

## 4. Monitor publishing and verify installation

Find the new Release run, then watch it using its numeric ID:

```sh
gh run list --workflow release.yml --limit 5
gh run watch RUN_ID --exit-status
```

Verify PyPI installation in an isolated environment:

```sh
mise exec -- uv run --isolated --no-project --refresh-package htomd \
  --default-index https://pypi.org/simple/ --with htomd==0.1.0 \
  python -I -c "import htomd; assert htomd.convert('<h1>Hello</h1>') == '# Hello\n'"
mise exec -- uv run --isolated --no-project --refresh-package htomd \
  --default-index https://pypi.org/simple/ --with htomd==0.1.0 \
  htomd --version
```

Check the package page on [PyPI](https://pypi.org/project/htomd/) and both
attachments on [GitHub Releases](https://github.com/jamiedavenport/htomd/releases).

If publisher configuration fails, correct it and rerun the failed jobs on the
same release. If only the release-asset job fails, PyPI publication has already
succeeded; rerun that job to attach the existing artifacts. Published artifacts
cannot be replaced with changed files; corrections need a new version.

## Documentation references

Commands were checked against uv `0.12.11` using Context7 library ID
`/astral-sh/uv` (requested version `0.12.11`; current unversioned documentation)
and the [uv publishing guide](https://docs.astral.sh/uv/guides/package/).
The GitHub CLI release command was checked against installed `gh` `2.100.0` and
Context7 library ID `/websites/cli_github_manual` (unversioned), alongside the
[GitHub CLI manual](https://cli.github.com/manual/gh_release_create).
