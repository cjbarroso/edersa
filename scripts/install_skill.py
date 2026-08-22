#!/usr/bin/env python3
"""Install the EDERSA Codex skill from a GitHub checkout."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


DEFAULT_REPO = "https://github.com/cjbarroso/edersa.git"
DEFAULT_REF = "master"
SKILL_NAME = "run-edersa-portal"
SKILL_RELATIVE_PATH = Path(".agents") / "skills" / SKILL_NAME


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Install run-edersa-portal into an agent's skills directory."
    )
    parser.add_argument(
        "--repo",
        default=DEFAULT_REPO,
        help=f"GitHub repository URL or local checkout (default: {DEFAULT_REPO})",
    )
    parser.add_argument(
        "--ref",
        default=DEFAULT_REF,
        help=f"Git branch or tag to clone (default: {DEFAULT_REF})",
    )
    parser.add_argument(
        "--skills-dir",
        type=Path,
        help=(
            "Parent directory for installed skills. Defaults to CODEX_SKILLS_DIR, "
            "then CODEX_HOME/skills, then ~/.codex/skills."
        ),
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace an existing run-edersa-portal installation.",
    )
    return parser.parse_args()


def resolve_skills_dir(explicit: Path | None) -> Path:
    if explicit:
        return explicit.expanduser()
    if configured := os.environ.get("CODEX_SKILLS_DIR"):
        return Path(configured).expanduser()
    if codex_home := os.environ.get("CODEX_HOME"):
        return Path(codex_home).expanduser() / "skills"
    return Path.home() / ".codex" / "skills"


def clone_repository(repo: str, ref: str, checkout: Path) -> None:
    try:
        subprocess.run(
            ["git", "clone", "--depth", "1", "--branch", ref, repo, str(checkout)],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except FileNotFoundError as exc:
        raise SystemExit("git is required to install this skill.") from exc
    except subprocess.CalledProcessError as exc:
        raise SystemExit(
            "Could not clone the repository. Verify GitHub credentials and access "
            f"to the requested ref '{ref}'."
        ) from exc


def install_skill(source_repo: Path, skills_dir: Path, force: bool) -> Path:
    source_skill = source_repo / SKILL_RELATIVE_PATH
    if not (source_skill / "SKILL.md").is_file():
        raise SystemExit(
            f"The repository does not contain {SKILL_RELATIVE_PATH / 'SKILL.md'}."
        )

    skills_dir.mkdir(parents=True, exist_ok=True)
    target = skills_dir / SKILL_NAME
    if target.exists() or target.is_symlink():
        if not force:
            raise SystemExit(
                f"{target} already exists. Re-run with --force to replace it."
            )

    if target.is_symlink() or target.is_file():
        target.unlink()
    elif target.exists():
        shutil.rmtree(target)
    shutil.copytree(source_skill, target)
    return target


def main() -> None:
    args = parse_args()
    skills_dir = resolve_skills_dir(args.skills_dir)
    local_repo = Path(args.repo).expanduser()

    if local_repo.exists():
        target = install_skill(local_repo.resolve(), skills_dir, args.force)
    else:
        with tempfile.TemporaryDirectory(prefix="edersa-skill-") as temp_dir:
            checkout = Path(temp_dir) / "repo"
            clone_repository(args.repo, args.ref, checkout)
            target = install_skill(checkout, skills_dir, args.force)

    print(f"Installed {SKILL_NAME} at {target}")


if __name__ == "__main__":
    main()
