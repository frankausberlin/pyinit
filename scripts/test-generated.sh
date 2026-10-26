#!/usr/bin/env bash
# Generate every bundled profile and run its quality gate with the real toolchain.
# This suite is opt-in: it needs network access and a working uv/just toolchain.
set -euo pipefail

cd "$(dirname "$0")/.."

unset VIRTUAL_ENV UV_PROJECT_ENVIRONMENT UV_PROJECT UV_WORKING_DIR PYTHONHOME PYTHONPATH || true
export UV_PYTHON_PREFERENCE=only-managed

artifacts="$(mktemp -d "$PWD/generated-artifacts.XXXXXX")"
profiles=(app app-cli lib)
failed=""

for profile in "${profiles[@]}"; do
    destination="$artifacts/$profile"
    log="$artifacts/$profile.log"
    echo "Generating profile '$profile' in $destination..."
    if ! uv run pyinit new "$profile" "$destination" --no-check >"$log" 2>&1; then
        failed="$profile (generation)"
        break
    fi
    echo "Running 'just check' for profile '$profile' (log: $log)..."
    if ! (cd "$destination" && just check) >>"$log" 2>&1; then
        failed="$profile (just check)"
        break
    fi
    echo "Profile '$profile' passed."
done

if [[ -n "$failed" ]]; then
    echo "Error: generated project check failed for $failed." >&2
    echo "Artifacts: $artifacts" >&2
    tail -n 60 "$artifacts"/*.log >&2 || true
    exit 1
fi

echo "All generated profiles passed. Artifacts: $artifacts"
