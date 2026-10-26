set shell := ["bash", "-uc"]

# Run tests with coverage report
test:
    uv run pytest --cov=src --cov-report=term-missing

# Run the Docker E2E suite locally (CI runs it automatically once tests exist)
test-e2e:
    bash scripts/test-e2e.sh

# Run the provider suite manually (never part of CI; prints a hint until tests exist)
test-agent:
    bash scripts/test-agent.sh

# Run linters and type checker (find errors)
lint:
    uv run ruff check .
    uv run ruff format --check .
    uv run basedpyright

# Type check only
typecheck:
    uv run basedpyright

# Fix linting issues
fix:
    uv run ruff check --fix .
    uv run ruff format .

# Remove local caches and generated artifacts (keeps baselines, .venv, sources and the journal)
clean:
    #!/usr/bin/env bash
    set -euo pipefail
    rm -rf .pytest_cache .ruff_cache .mypy_cache .coverage htmlcov site
    rm -rf build dist ./*.egg-info
    rm -rf e2e-artifacts.* agent-artifacts.*
    if [ -d .refactor ]; then
        find .refactor -mindepth 1 -maxdepth 1 ! -name baselines -exec rm -rf {} +
    fi
    find . -path ./.venv -prune -o -path ./.git -prune -o -type d -name __pycache__ -print -exec rm -rf {} +
    find . -path ./.venv -prune -o -path ./.git -prune -o -type f \( -name '*.pyc' -o -name '*.pyo' \) -print -exec rm -f {} +
    echo "Cleaned caches and generated artifacts, including e2e-artifacts.* and agent-artifacts.* (kept .refactor/baselines, .venv and journal/)."

# Audit dependencies for known security vulnerabilities
audit:
    uv run pip-audit

# Bump version — requires a clean working tree (patch | minor | major)
bump part="patch":
    #!/usr/bin/env bash
    if [ -n "$(git status --porcelain)" ]; then
        echo "Error: Working tree is dirty." >&2
        exit 1
    fi
    uv run bump-my-version bump {{part}}

# Write or compare design metrics (run | save <name> | compare <name>)
rate-design *args:
    uv run python scripts/design_report.py {{args}}

# Prepare a refactoring session: clean tree, quality gate, baseline, branch. Changes no code.
refactor name="":
    #!/usr/bin/env bash
    set -euo pipefail
    if [ -n "$(git status --porcelain)" ]; then
        echo "Error: working tree is dirty; commit or stash first." >&2
        exit 1
    fi
    just check
    slug="{{name}}"
    slug="${slug:-$(date -u +%Y%m%d-%H%M%S)}"
    slug="$(printf '%s' "$slug" | tr '[:upper:]' '[:lower:]' | tr -cs 'a-z0-9._-' '-')"
    slug="${slug#-}"
    slug="${slug%-}"
    if [ -z "$slug" ]; then
        slug="session"
    fi
    branch="refactor/${slug}"
    if git show-ref --verify --quiet "refs/heads/${branch}"; then
        echo "Error: branch '$branch' already exists." >&2
        exit 1
    fi
    just rate-design save "$slug"
    git switch -c "$branch"
    echo "Branch '$branch' created. Baseline in .refactor/baselines/$slug/."
    echo "Proceed with the lupysta refactoring recipe; this recipe does not refactor."

# Fast-forward target to <branch> (auto-detected when omitted) and clean up safely.
merge branch="" target="main":
    #!/usr/bin/env bash
    set -euo pipefail
    branch="{{branch}}"
    target="{{target}}"
    if ! git rev-parse --verify --quiet "refs/heads/$target" >/dev/null; then
        echo "merge: target branch '$target' does not exist" >&2
        exit 1
    fi

    target_path="$(
        git worktree list --porcelain | awk -v ref="refs/heads/$target" '
            /^worktree / { path = substr($0, 10) }
            /^branch / && $2 == ref { print path; exit }
        '
    )"
    current_path="$(git rev-parse --show-toplevel)"
    current_branch="$(git branch --show-current)"
    switched_current=0

    if [ -z "$target_path" ]; then
        if [ -n "$(git status --porcelain)" ]; then
            echo "merge: no worktree has '$target' checked out and the current tree is dirty" >&2
            exit 1
        fi
        if [ -z "$branch" ] && [ "$current_branch" != "$target" ]; then
            branch="$current_branch"
        fi
        git switch "$target"
        target_path="$current_path"
        switched_current=1
    fi

    if [ -z "$branch" ]; then
        candidates="$(
            git worktree list --porcelain | awk -v ref="refs/heads/$target" '
                /^branch / { b = substr($0, 8); if (b != ref) print b }
            '
        )"
        if [ -z "$candidates" ]; then
            candidates="$(git branch --no-merged "$target" --format='%(refname:short)')"
        fi
        count="$(printf '%s\n' "$candidates" | awk 'NF { n++ } END { print n + 0 }')"
        if [ "$count" -eq 0 ]; then
            echo "merge: nothing to merge" >&2
            exit 1
        fi
        if [ "$count" -gt 1 ]; then
            echo "merge: several branches to choose from:" >&2
            printf '%s\n' "$candidates" | while IFS= read -r candidate; do
                printf '  %s\n' "$candidate" >&2
            done
            echo "merge: run 'just merge <branch>'" >&2
            exit 1
        fi
        branch="$(printf '%s\n' "$candidates" | awk 'NF { print; exit }')"
    fi
    if [ "$branch" = "$target" ]; then
        echo "merge: refusing to merge '$target' into itself" >&2
        exit 1
    fi

    if [ -n "$(git -C "$target_path" status --porcelain)" ]; then
        echo "merge: target worktree '$target_path' is dirty" >&2
        exit 1
    fi
    if git -C "$target_path" remote get-url origin >/dev/null 2>&1; then
        git -C "$target_path" fetch origin
        if git -C "$target_path" rev-parse --verify --quiet "refs/remotes/origin/$target" >/dev/null; then
            if ! git -C "$target_path" merge-base --is-ancestor "refs/remotes/origin/$target" HEAD; then
                echo "merge: origin/$target is not an ancestor of $target; reconcile before merging" >&2
                exit 1
            fi
        fi
    fi
    if ! git -C "$target_path" merge --ff-only "$branch"; then
        echo "merge: '$branch' cannot be fast-forwarded; '$target' has diverged" >&2
        exit 1
    fi

    source_path="$(
        git worktree list --porcelain | awk -v ref="refs/heads/$branch" '
            /^worktree / { path = substr($0, 10) }
            /^branch / && $2 == ref { print path; exit }
        '
    )"
    if [ -n "$source_path" ] && [ "$source_path" != "$target_path" ]; then
        if [ "$source_path" = "$current_path" ]; then
            echo "merge: '$branch' merged into '$target'."
            echo "merge: source worktree is the current checkout; switch to '$target'"
            echo "       and remove the worktree and branch manually if you no longer need them."
        elif [ -n "$(git -C "$source_path" status --porcelain)" ]; then
            echo "merge: '$branch' merged into '$target'."
            echo "merge: worktree '$source_path' left in place because it is dirty."
        elif git worktree remove "$source_path"; then
            git branch -d "$branch"
            echo "merge: '$branch' merged into '$target'; worktree removed and branch deleted."
        else
            echo "merge: '$branch' merged into '$target'."
            echo "merge: worktree '$source_path' could not be removed; clean it up manually."
        fi
    else
        if [ "$source_path" = "$target_path" ] && [ "$switched_current" -eq 0 ]; then
            echo "merge: '$branch' merged into '$target'; source worktree is the target, leaving it in place."
        else
            git branch -d "$branch"
            echo "merge: '$branch' merged into '$target'; branch deleted."
        fi
    fi
    echo "merge: publish with 'git push origin $target'"

# Full local quality gate (lint + typecheck + docs + tests)
check:
    uv run ruff check .
    uv run ruff format --check .
    uv run basedpyright
    just docs-check
    uv run pytest --cov=src --cov-report=term-missing

# Run the installed command
run:
    uv run pyinit

# Regenerate docs/reference/cli.md from the Typer app
docs:
    uv run python scripts/gen_cli_docs.py

# Verify docs/reference/cli.md matches the Typer app (no write; part of `just check`)
docs-check:
    uv run python scripts/gen_cli_docs.py --check
