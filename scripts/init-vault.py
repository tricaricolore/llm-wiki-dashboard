#!/usr/bin/env python3
"""
Create a clean local LLM wiki vault from this repository.

The generated vault is intentionally data-empty: no demo sources, no generated
pages, and no example reports are copied into the target project.
"""

import argparse
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def parse_args():
    parser = argparse.ArgumentParser(
        description="Create a clean local LLM wiki vault."
    )
    parser.add_argument("target", help="Destination directory for the new vault.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Allow using an existing directory if it only contains generated vault files.",
    )
    parser.add_argument(
        "--git",
        action="store_true",
        help="Initialize a Git repository and create an initial commit.",
    )
    return parser.parse_args()


def ensure_target(target: Path, force: bool):
    if target.exists() and any(target.iterdir()) and not force:
        raise SystemExit(f"Target is not empty: {target}")
    target.mkdir(parents=True, exist_ok=True)


def copy_path(source: Path, destination: Path):
    if source.is_dir():
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(
            source,
            destination,
            ignore=shutil.ignore_patterns(
                "__pycache__",
                "*.pyc",
                "data.json",
            ),
        )
    else:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def write_file(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def create_clean_wiki(target: Path):
    today = date.today().isoformat()

    write_file(target / "raw/.gitkeep", "\n")
    write_file(target / "raw/assets/.gitkeep", "\n")
    write_file(target / "ingest-reports/.gitkeep", "\n")
    write_file(target / "reflect-reports/.gitkeep", "\n")
    write_file(target / "plans/.gitkeep", "\n")

    write_file(
        target / "wiki/index.md",
        f"""---
title: "Index"
type: overview
tags:
  - index
created: {today}
last_updated: {today}
source_count: 0
confidence: high
status: active
---

# Index

## Sources

## Entities

## Concepts

## Techniques

## Analyses
""",
    )

    write_file(
        target / "wiki/log.md",
        f"""---
title: "Log"
type: overview
tags:
  - log
created: {today}
last_updated: {today}
source_count: 0
confidence: high
status: active
---

# Log

## [{today}] maintenance | Vault initialized
Clean local wiki template initialized.
""",
    )

    write_file(
        target / "wiki/overview.md",
        f"""---
title: "Overview"
type: overview
tags:
  - overview
created: {today}
last_updated: {today}
source_count: 0
confidence: high
status: active
---

# Wiki Overview

## Current state

- Sources: 0
- Entity pages: 0
- Concept pages: 0
- Technique pages: 0
- Total wiki pages: 3

## Getting started

- Add source documents to `raw/` or paste a source from the dashboard Ingest view.
- Run an ingest to create cited wiki pages.
- Review the generated diff, then commit and push the wiki with Git.
""",
    )


def init_git(target: Path):
    if (target / ".git").exists():
        return
    subprocess.run(["git", "init", "-b", "main"], cwd=target, check=True)
    subprocess.run(["git", "add", "-A"], cwd=target, check=True)
    subprocess.run(
        ["git", "commit", "-m", "init: llm wiki vault"],
        cwd=target,
        check=True,
    )


def main():
    args = parse_args()
    target = Path(args.target).expanduser().resolve()

    ensure_target(target, args.force)

    for name in ["dashboard", ".obsidian"]:
        copy_path(ROOT / name, target / name)

    for name in ["CLAUDE.md", ".gitignore"]:
        copy_path(ROOT / name, target / name)

    create_clean_wiki(target)

    if args.git:
        init_git(target)

    print(f"Created clean LLM wiki vault: {target}")
    print("Start it with: python3 dashboard/server.py")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as exc:
        print(f"Command failed: {' '.join(exc.cmd)}", file=sys.stderr)
        raise SystemExit(exc.returncode)
