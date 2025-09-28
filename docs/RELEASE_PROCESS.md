# Wikipedia MCP Release Process

This document describes how to create new releases for the Wikipedia MCP project using GitHub Actions.

## Automated Release Using GitHub Actions

The project ships from a single workflow defined in `.github/workflows/release.yml`. The workflow supports two entry points:

- **Tag push (`v*`)** – When you push an annotated tag such as `v1.7.0`, the workflow validates that `pyproject.toml` already contains that version, builds the artifacts, attaches them to a GitHub Release, and publishes the package to PyPI via trusted publishing (OIDC) once tests pass.
- **Manual dispatch** – From the GitHub UI you can trigger the workflow to bump the version for you on `main`, create a tag, and then run the same verification/publish steps. This is useful when you do not want to create the tag locally.

### Triggering a Release Manually (workflow_dispatch)

1. Open the **Actions** tab in GitHub and select **Release Wikipedia MCP**.
2. Click **Run workflow** and supply:
   - **Version** – e.g. `1.7.0`
   - **Prerelease** – `true` if this should be marked as a pre-release
   - **Draft** – `true` to create a draft GitHub Release without publishing to PyPI
3. Submit the run and monitor the "Release Wikipedia MCP" workflow for progress.
4. After completion confirm:
   - `pyproject.toml` on `main` reflects the new version
   - A `vX.Y.Z` tag was created
   - The GitHub Release lists the built wheel and sdist
   - The package is available on PyPI (skipped when Draft or Prerelease is selected)

### When Releasing from a Local Tag

If you prefer to manage version bumps locally:

1. Update `pyproject.toml` with the new semantic version.
2. Commit the change and create an annotated tag `vX.Y.Z` that matches the version field.
3. Push the commit and tag. The release workflow will detect the tag, run tests/builds, publish to GitHub Releases, and publish to PyPI if the tag is a full release.

> Note: Because PyPI uses trusted publishing, no PyPI token is stored in GitHub secrets and only OIDC-enabled workflows can publish. Ensure the tag is pushed from the canonical repo so the trusted publisher configuration matches.

### Release Workflow Overview

For both entry points the pipeline:

1. Determines the version and prerelease/draft flags.
2. Optionally (manual runs only) edits `pyproject.toml` and `CHANGELOG.md`, commits, and pushes a matching tag.
3. Builds and tests the project on Python 3.10, 3.11, and 3.12.
4. Uploads build artifacts for reuse by downstream jobs.
5. Creates (or updates) the GitHub Release and attaches the built wheel and source distribution.
6. Publishes to PyPI using `pypa/gh-action-pypi-publish@release/v1` with OIDC if the release is not marked as a prerelease or draft.

## Manually Creating a Release (Alternative Method)

If you need to create a release manually without using GitHub Actions, follow these steps:

### 1. Update Version Number

Update the version number in `setup.py`:

```python
setup(
    name="wikipedia-mcp",
    version="1.0.2",  # Update this to the new version
    # ...
)
```

### 2. Create and Update CHANGELOG.md

```markdown
# Changelog

## [1.0.2] - YYYY-MM-DD

### Added
- New features

### Fixed
- Bug fixes

### Changed
- Other changes
```

### 3. Build the Package

```bash
# Install build tools if needed
pip install --upgrade build twine

# Build the package
python -m build
```

### 4. Create a Git Tag

```bash
git add .
git commit -m "Bump version to 1.0.2"
git tag -a v1.0.2 -m "Version 1.0.2"
git push origin v1.0.2
git push origin main
```

### 5. Create a GitHub Release

1. Go to https://github.com/rudra-ravi/wikipedia-mcp/releases/new
2. Select the tag you just created (v1.0.2)
3. Set the title to "Wikipedia MCP v1.0.2"
4. Add release notes (e.g., from your CHANGELOG.md)
5. Attach the distribution files (.tar.gz and .whl) from the dist/ directory
6. Click "Publish release"

### 6. Publish to PyPI

```bash
twine upload dist/*
```

## Release Guidelines

When creating releases, keep these guidelines in mind:

1. **Follow Semantic Versioning**:
   - **MAJOR**: Breaking changes (1.0.0)
   - **MINOR**: New features, backward compatible (0.x.0)
   - **PATCH**: Bug fixes, backward compatible (0.0.x)

2. **Release Notes**: Provide clear, concise release notes that highlight:
   - New features
   - Bug fixes
   - Breaking changes (if any)
   - Upgrade instructions (if needed)

3. **Testing**: Before creating a release:
   - Run all tests
   - Verify installation from the built packages
   - Test key functionality

4. **Security**: Prioritize fixes for security vulnerabilities

## PyPI Trusted Publishing Configuration

This repository uses **PyPI Trusted Publishing**. Instead of storing a username/password in GitHub secrets, PyPI is configured to trust the `Release Wikipedia MCP` workflow. During the `publish-pypi` job GitHub issues an OpenID Connect (OIDC) token that PyPI validates. To keep releases working:

1. Ensure the workflow file path (`.github/workflows/release.yml`), repository owner, and environment `pypi` remain registered on PyPI under *Manage project → Publishing → Trusted Publishers*.
2. Keep `id-token: write` permissions enabled for the `publish-pypi` job in the workflow.
3. If you rename the workflow, repository, or environment, update the trusted publisher configuration on PyPI accordingly.

## Troubleshooting

If you encounter issues with the release process, check:

1. **GitHub Actions logs** for detailed error messages
2. **Git tags and commits** to verify they were created correctly
3. **PyPI credentials** if the package publishing fails
4. **Build artifacts** to ensure they were created correctly

## Contact

If you encounter persistent issues with the release process, please open an issue on the GitHub repository. 