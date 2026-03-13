#!/usr/bin/env bash
# post-commit hook: auto-create a version tag based on commit message prefix.
#
# Conventional commit prefixes determine the bump level:
#   feat:     → minor bump (0.1.0 → 0.2.0)
#   fix:      → patch bump (0.1.0 → 0.1.1)
#   perf:     → patch bump
#   BREAKING CHANGE / feat!: / fix!: → major bump (0.1.0 → 1.0.0)
#
# Prefixes that do NOT trigger a version bump:
#   chore:, docs:, style:, refactor:, test:, ci:, build:
#
# To skip auto-tagging on any commit, include [skip-version] in the message.

set -euo pipefail

# Only run inside the ac-cli submodule
REPO_NAME=$(basename "$(git rev-parse --show-toplevel)")
if [[ "$REPO_NAME" != "ac-cli" ]]; then
  exit 0
fi

# Read the commit message
COMMIT_MSG=$(git log -1 --pretty=%B)

# Skip if explicitly opted out
if echo "$COMMIT_MSG" | grep -qi '\[skip-version\]'; then
  exit 0
fi

# Determine bump level from commit message
BUMP=""
if echo "$COMMIT_MSG" | grep -qE '^.+!:|BREAKING CHANGE'; then
  BUMP="major"
elif echo "$COMMIT_MSG" | grep -qE '^feat(\(.+\))?:'; then
  BUMP="minor"
elif echo "$COMMIT_MSG" | grep -qE '^(fix|perf)(\(.+\))?:'; then
  BUMP="patch"
fi

# No bump-worthy prefix found
if [[ -z "$BUMP" ]]; then
  exit 0
fi

# Get latest version tag
LATEST=$(git tag -l 'v*' --sort=-v:refname | head -1)
if [[ -z "$LATEST" ]]; then
  MAJOR=0; MINOR=0; PATCH=0
else
  VERSION="${LATEST#v}"
  IFS='.' read -r MAJOR MINOR PATCH <<< "$VERSION"
fi

# Calculate next version
case "$BUMP" in
  major) MAJOR=$((MAJOR + 1)); MINOR=0; PATCH=0 ;;
  minor) MINOR=$((MINOR + 1)); PATCH=0 ;;
  patch) PATCH=$((PATCH + 1)) ;;
esac

TAG="v${MAJOR}.${MINOR}.${PATCH}"

# Don't re-tag if this tag already exists
if git rev-parse "$TAG" >/dev/null 2>&1; then
  exit 0
fi

git tag -a "$TAG" -m "Release ${TAG}"
echo "auto-version: ${LATEST:-v0.0.0} → ${TAG} (${BUMP} bump from commit prefix)"
