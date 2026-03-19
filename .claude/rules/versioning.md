# Versioning & Publishing

## How It Works

Version is managed by **hatch-vcs** — derived from git tags, not hardcoded.

- `pyproject.toml` uses `dynamic = ["version"]` — never add a `version` field
- `src/ac_cli/_version.py` is auto-generated at build time — do not edit or commit it (gitignored)
- Between tags, dev builds show versions like `0.2.1.dev3+gabcdef1`

## Auto-bump (post-commit hook)

A post-commit hook (`scripts/auto-version-tag.sh`) creates a version tag based on conventional commit prefixes:

| Prefix | Bump | Example |
|--------|------|---------|
| `feat:` | minor | 0.2.1 → 0.3.0 |
| `fix:`, `perf:` | patch | 0.2.1 → 0.2.2 |
| `feat!:`, `fix!:`, `BREAKING CHANGE` | major | 0.2.1 → 1.0.0 |
| `chore:`, `docs:`, `refactor:`, `test:`, `ci:`, `style:`, `build:` | none | no tag |

Add `[skip-version]` to a commit message to skip auto-tagging.

## PyPI Publishing

Automatic. Pushing a version tag triggers the "Publish to PyPI" workflow (tests on Python 3.10–3.13, then publishes as `agencycore-cli`).

Full flow: **commit** (conventional prefix) → **hook creates tag** → **push** (tags included via `push.followTags`) → **GitHub Actions tests + publishes**

Non-bumping prefixes (`chore:`, `docs:`, etc.) don't create a tag, so no publish happens.

## Manual bump

```bash
./scripts/bump.sh patch    # 0.2.1 → 0.2.2
./scripts/bump.sh minor    # 0.2.1 → 0.3.0
./scripts/bump.sh major    # 0.2.1 → 1.0.0
./scripts/bump.sh minor --push  # bump + push tag to remote
```

## Setup

Install hooks from the parent repo: `bash .claude/hooks/install-submodule-hooks.sh`

This installs the post-commit hook (auto-version tag) and sets `push.followTags = true` so tags are always pushed automatically.
