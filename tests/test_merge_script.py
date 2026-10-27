"""Behaviour tests for the merge script shipped into generated projects."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from pyinit.render import package_data_root

MERGE_SCRIPT = package_data_root() / "artifacts" / "base-app" / "files" / "merge.sh"


def _env() -> dict[str, str]:
    """Return an environment that ignores user and system git configuration."""
    return os.environ | {
        "GIT_AUTHOR_NAME": "Pyinit Test",
        "GIT_AUTHOR_EMAIL": "test@example.com",
        "GIT_COMMITTER_NAME": "Pyinit Test",
        "GIT_COMMITTER_EMAIL": "test@example.com",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_SYSTEM": os.devnull,
    }


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run git in the repository and fail loudly on error."""
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
        env=_env(),
    )


def _repo(tmp_path: Path) -> Path:
    """Create a repository with one commit on 'main'."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    (repo / "app.txt").write_text("base\n")
    _git(repo, "add", "app.txt")
    _git(repo, "commit", "-m", "init")
    return repo


def _commit(repo: Path, name: str, content: str, message: str) -> None:
    """Write a file and commit it."""
    (repo / name).write_text(content)
    _git(repo, "add", name)
    _git(repo, "commit", "-m", message)


def _merge(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run the merge script inside a repository."""
    return subprocess.run(
        ["bash", str(MERGE_SCRIPT), *args],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
        env=_env(),
    )


def _branch_exists(repo: Path, branch: str) -> bool:
    """Return whether a local branch exists."""
    result = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}"],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
        env=_env(),
    )
    return result.returncode == 0


def _current_branch(repo: Path) -> str:
    """Return the checked out branch name."""
    return _git(repo, "branch", "--show-current").stdout.strip()


def test_merges_task_branch_and_deletes_it(tmp_path: Path) -> None:
    """The default case: fast-forward main and drop the task branch."""
    repo = _repo(tmp_path)
    _git(repo, "switch", "-c", "feat/task")
    _commit(repo, "feature.txt", "feature\n", "feat: add feature")
    _git(repo, "switch", "main")

    result = _merge(repo, "feat/task")

    assert result.returncode == 0, result.stderr
    assert _current_branch(repo) == "main"
    assert (repo / "feature.txt").is_file()
    assert not _branch_exists(repo, "feat/task")
    assert "merged into 'main'" in result.stdout


def test_auto_detects_the_only_unmerged_branch(tmp_path: Path) -> None:
    """Without an argument the single candidate is merged."""
    repo = _repo(tmp_path)
    _git(repo, "switch", "-c", "feat/only")
    _commit(repo, "only.txt", "only\n", "feat: only")
    _git(repo, "switch", "main")

    result = _merge(repo)

    assert result.returncode == 0, result.stderr
    assert (repo / "only.txt").is_file()
    assert not _branch_exists(repo, "feat/only")


def test_reports_when_there_is_nothing_to_merge(tmp_path: Path) -> None:
    """An repository without candidates fails with a clear message."""
    repo = _repo(tmp_path)

    result = _merge(repo)

    assert result.returncode == 1
    assert "nothing to merge" in result.stderr


def test_refuses_dirty_checkout_when_target_is_not_checked_out(tmp_path: Path) -> None:
    """A dirty tree blocks the implicit switch of the current checkout."""
    repo = _repo(tmp_path)
    _git(repo, "switch", "-c", "feat/dirty")
    (repo / "dirty.txt").write_text("dirty\n")

    result = _merge(repo)

    assert result.returncode == 1
    assert "and the current tree is dirty" in result.stderr
    assert _current_branch(repo) == "feat/dirty"


def test_refuses_diverged_target(tmp_path: Path) -> None:
    """A main that moved on cannot be fast-forwarded."""
    repo = _repo(tmp_path)
    _git(repo, "switch", "-c", "feat/old")
    _commit(repo, "old.txt", "old\n", "feat: old")
    _git(repo, "switch", "main")
    _commit(repo, "new.txt", "new\n", "feat: new")

    result = _merge(repo, "feat/old")

    assert result.returncode == 1
    assert "cannot be fast-forwarded" in result.stderr
    assert _branch_exists(repo, "feat/old")


def test_refuses_to_merge_a_branch_into_itself(tmp_path: Path) -> None:
    """Passing the target as the branch is rejected."""
    repo = _repo(tmp_path)

    result = _merge(repo, "main", "main")

    assert result.returncode == 1
    assert "refusing to merge 'main' into itself" in result.stderr


def test_reports_unknown_target(tmp_path: Path) -> None:
    """An unknown target branch is reported instead of silently doing nothing."""
    repo = _repo(tmp_path)

    result = _merge(repo, "feat/whatever", "release")

    assert result.returncode == 1
    assert "target branch 'release' does not exist" in result.stderr


def test_merges_from_linked_worktree_and_removes_it(tmp_path: Path) -> None:
    """A branch checked out in another worktree is merged and cleaned up."""
    repo = _repo(tmp_path)
    worktree = tmp_path / "wt"
    _git(repo, "worktree", "add", str(worktree), "-b", "feat/worktree")
    _commit(worktree, "wt.txt", "wt\n", "feat: worktree")

    result = _merge(repo)

    assert result.returncode == 0, result.stderr
    assert (repo / "wt.txt").is_file()
    assert not _branch_exists(repo, "feat/worktree")
    assert not worktree.exists()
    assert "worktree removed and branch deleted" in result.stdout


@pytest.mark.parametrize("profile_id", ["app", "app-cli", "cli-mcp", "lib", "mcp"])
def test_script_is_part_of_every_profile(profile_id: str) -> None:
    """Every generated project ships the script it calls from the Justfile."""
    assert MERGE_SCRIPT.is_file()
    content = MERGE_SCRIPT.read_text()
    assert content.startswith("#!/usr/bin/env bash\n")
    assert "{{" not in content


def test_repository_copy_matches_the_shipped_script() -> None:
    """The generator dogfoods the script, so both copies must stay identical."""
    own_copy = Path(__file__).resolve().parents[1] / "scripts" / "merge.sh"
    assert own_copy.is_file()
    assert own_copy.read_text() == MERGE_SCRIPT.read_text(), (
        "scripts/merge.sh and the base-app artifact diverged; copy the tested artifact version into scripts/merge.sh"
    )
