#!/usr/bin/env bash
set -euo pipefail

PROFILE_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)

while IFS= read -r -d '' link; do
    resolved=$(realpath "$link")
    case "$resolved" in
        "$PROFILE_ROOT"/*) ;;
        *)
            echo "ERROR: symlink escapes profile repository: $link -> $resolved" >&2
            exit 1
            ;;
    esac
done < <(find "$PROFILE_ROOT" -type l -print0)

if grep -RIE --exclude-dir=.git --exclude='verify-profile-boundaries.sh' \
    '(/Users/|/home/[^/]+/(Desktop|Downloads)/O-RAN-Testbed-Automation)' \
    "$PROFILE_ROOT" >/dev/null; then
    echo "ERROR: profile contains a host-local testbed path" >&2
    exit 1
fi

if grep -RIE --exclude-dir=.git --exclude='verify-profile-boundaries.sh' \
    "(^|[[:space:]\"'])(\.\./)+" "$PROFILE_ROOT" >/dev/null; then
    echo "ERROR: profile contains a parent-directory path reference" >&2
    exit 1
fi

echo "Profile boundary check passed: $PROFILE_ROOT"
