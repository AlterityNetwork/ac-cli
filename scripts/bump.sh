#!/usr/bin/env bash
# Bump the version by creating a new git tag.
#
# Usage:
#   ./scripts/bump.sh patch    # 0.1.0 → 0.1.1
#   ./scripts/bump.sh minor    # 0.1.0 → 0.2.0
#   ./scripts/bump.sh major    # 0.1.0 → 1.0.0
#   ./scripts/bump.sh          # defaults to patch
#
# Add --push to also push the tag to the remote:
#   ./scripts/bump.sh minor --push

set -euo pipefail

PART="${1:-patch}"
PUSH=false

for arg in "$@"; do
    if [[ "$arg" == "--push" ]]; then
        PUSH=true
    fi
done

# Validate argument
if [[ "$PART" != "patch" && "$PART" != "minor" && "$PART" != "major" ]]; then
    echo "Usage: $0 [patch|minor|major] [--push]"
    exit 1
fi

# Get latest version tag
LATEST=$(git tag -l 'v*' --sort=-v:refname | head -1)
if [[ -z "$LATEST" ]]; then
    echo "No existing version tags found. Creating v0.1.0"
    NEXT="0.1.0"
else
    # Strip leading 'v'
    VERSION="${LATEST#v}"

    IFS='.' read -r MAJOR MINOR PATCH <<< "$VERSION"

    case "$PART" in
        major) MAJOR=$((MAJOR + 1)); MINOR=0; PATCH=0 ;;
        minor) MINOR=$((MINOR + 1)); PATCH=0 ;;
        patch) PATCH=$((PATCH + 1)) ;;
    esac

    NEXT="${MAJOR}.${MINOR}.${PATCH}"
fi

TAG="v${NEXT}"

echo "Current: ${LATEST:-none}"
echo "Next:    ${TAG}"
echo ""

# Check for uncommitted changes
if ! git diff --quiet HEAD 2>/dev/null; then
    echo "Error: You have uncommitted changes. Commit or stash them first."
    exit 1
fi

read -rp "Create tag ${TAG}? [y/N] " CONFIRM
if [[ "$CONFIRM" != "y" && "$CONFIRM" != "Y" ]]; then
    echo "Aborted."
    exit 0
fi

git tag -a "$TAG" -m "Release ${TAG}"
echo "Created tag: ${TAG}"

if [[ "$PUSH" == true ]]; then
    git push origin "$TAG"
    echo "Pushed tag to remote."
else
    echo "Run 'git push origin ${TAG}' to push the tag."
fi
