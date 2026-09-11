# Releasing htomd

Publishing a GitHub Release runs Build → Test → Deploy. The
[CI workflow](.github/workflows/ci.yml) builds once on Linux and tests the same
artifacts on Linux, Windows, and macOS. Static checks run once in the build job.
The [release workflow](.github/workflows/release.yml) deploys those tested
artifacts through separate Python/PyPI and TypeScript/npm jobs. Deployment
does not rebuild packages. Pushing a tag or saving a draft does not publish.

## Publisher setup

Both registries use trusted publishing from `jamiedavenport/htomd` with workflow
filename `release.yml`. Configure these identities in the registry settings:

| Registry | Package | GitHub environment |
| --- | --- | --- |
| PyPI | `htomd` | `pypi` |
| npm | `htomd` | `npm` |

The package owner must configure each publisher before automated deployment.
For npm, allow direct publishing from this workflow and ensure the package's
repository metadata matches. No registry tokens are stored in the workflow. See the
[PyPI setup guide](https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/)
and [npm trusted publishing guide](https://docs.npmjs.com/trusted-publishers/).

## Prepare and validate

Update `python/pyproject.toml` and `typescript/package.json` to the same version,
refresh `python/uv.lock` and `typescript/bun.lock` with their package managers,
and update `CHANGELOG.md`. The release tag must be `v` followed by that version;
`tools/check_release.py` checks both package versions. Use the new version in
place of `0.1.1` below.

```sh
mise run setup
mise run build
mise run check
mise exec -- env RELEASE_TAG=v0.1.1 uv run --project python --locked python tools/check_release.py
```

Builds produce a wheel and source archive in `dist/python/` and a tarball in
`dist/typescript/`. Move aside artifacts from older versions before building;
checks require exactly one artifact of each kind.

## Publish

Commit and push the validated release changes, then create the tag and Release:

```sh
git tag -a v0.1.1 -m "htomd 0.1.1"
git push origin v0.1.1
gh release create v0.1.1 --verify-tag --title "htomd 0.1.1" --notes-file release-notes.md
```

Use a notes file containing only this version's changelog entry. Watch the
Release workflow; each deployment job publishes and attaches its own artifacts.
If one package fails, rerun its failed job after correcting the problem. The
other package may already be published. If only attachment fails, upload the
existing artifact with `gh release upload` without republishing. Changed package
contents require a new version.

## Documentation references

Checked with Context7 `/astral-sh/uv` (requested uv 0.12.11) and `/npm/cli`
(requested npm 11.19.0); both entries are unversioned. The pinned Node installation
includes npm with OIDC support. Bun remains the TypeScript development tool;
only deployment uses npm's trusted-publishing client.
