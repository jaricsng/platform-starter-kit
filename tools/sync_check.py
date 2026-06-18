#!/usr/bin/env python3
"""Drift/re-sync check for a repo scaffolded from platform-starter-kit.

GETTING-STARTED.md has always said "this kit stays as the upstream
reference to re-sync from later" without ever providing a way to actually
do that. This is that way: reads the source commit SHA that
tools/scaffold.py stamped into PLATFORM-KIT.md, and for every file it
knows scaffold.py copied, reports whether (a) you've locally modified it
since scaffolding, and (b) the kit has changed it upstream since then —
with a diff for the latter, since that's the part you'd otherwise only
find out about by accident.

Usage:
    python3 tools/sync_check.py [target-path] --kit-path /path/to/platform-starter-kit

This does not modify anything — it's a report, not a merge tool. Decide
file by file whether to manually pull in an upstream change.
"""
import argparse
import difflib
import re
import sys
from pathlib import Path

from _platform_kit import (
    ALWAYS_DIRS,
    ALWAYS_FILES,
    CLAUDE_COMMANDS_DST,
    CLAUDE_COMMANDS_SRC,
    GOVERNANCE_DST,
    GOVERNANCE_SRC,
    IAC_GCP_DST,
    IAC_GCP_SRC,
    OPTIONAL_DIRS,
    case_variants,
    git_show,
    kit_commit_sha,
    reverse_substitute_placeholders,
    slugify,
)

UNCHANGED, LOCAL_ONLY, UPSTREAM_ONLY, BOTH_CHANGED, NEW_UPSTREAM, REMOVED_UPSTREAM, UNKNOWN = (
    "unchanged", "locally modified", "upstream changed", "both changed",
    "new upstream file", "removed upstream", "unknown",
)
ICONS = {
    UNCHANGED: "✅", LOCAL_ONLY: "✏️ ", UPSTREAM_ONLY: "🆕", BOTH_CHANGED: "⚠️ ",
    NEW_UPSTREAM: "➕", REMOVED_UPSTREAM: "🗑️ ", UNKNOWN: "❓",
}


def parse_manifest(target: Path):
    manifest = target / "PLATFORM-KIT.md"
    if not manifest.exists():
        return None, None
    text = manifest.read_text()
    sha_match = re.search(r"Source kit commit: `([^`]+)`", text)
    name_match = re.search(r"App name: `([^`]+)`", text)
    sha = sha_match.group(1) if sha_match else None
    app_name = name_match.group(1) if name_match else None
    return sha, app_name


def discover_file_pairs(target: Path):
    """Yield (target_relative_path, kit_relative_path) for every file in
    the target repo that scaffold.py is known to have produced from a kit
    source file (i.e. excludes generated-on-the-fly files like
    PLATFORM-KIT.md, README.md, TODO.md, and terraform.tfvars.example)."""
    for kit_rel, target_rel in ALWAYS_FILES:
        if (target / target_rel).exists():
            yield target_rel, kit_rel

    dir_pairs = [(kd, td) for kd, td, _cap in OPTIONAL_DIRS] + list(ALWAYS_DIRS)
    for kit_dir, target_dir in dir_pairs:
        root = target / target_dir
        if not root.is_dir():
            continue
        for f in root.rglob("*"):
            if f.is_file():
                rel = f.relative_to(root).as_posix()
                yield f"{target_dir}/{rel}", f"{kit_dir}/{rel}"

    claude_dir = target / CLAUDE_COMMANDS_DST
    if claude_dir.is_dir():
        for f in claude_dir.glob("*.md"):
            yield f"{CLAUDE_COMMANDS_DST}/{f.name}", f"{CLAUDE_COMMANDS_SRC}/{f.name}"

    iac_dir = target / IAC_GCP_DST
    if iac_dir.is_dir():
        for f in iac_dir.rglob("*"):
            if f.is_file() and f.name != "terraform.tfvars.example":
                rel = f.relative_to(iac_dir).as_posix()
                yield f"{IAC_GCP_DST}/{rel}", f"{IAC_GCP_SRC}/{rel}"

    gov_dir = target / GOVERNANCE_DST
    if gov_dir.is_dir():
        for f in gov_dir.rglob("*"):
            if f.is_file():
                rel = f.relative_to(gov_dir).as_posix()
                yield f"{GOVERNANCE_DST}/{rel}", f"{GOVERNANCE_SRC}/{rel}"


def check_file(target: Path, target_rel: str, kit_rel: str, kit_path: Path, sha: str, variants: dict):
    target_text = (target / target_rel).read_text(errors="ignore")
    normalized_target = reverse_substitute_placeholders(target_text, variants)

    as_scaffolded = git_show(kit_path, sha, kit_rel)
    current_kit_file = kit_path / kit_rel
    current_kit = current_kit_file.read_text(errors="ignore") if current_kit_file.exists() else None

    if as_scaffolded is None and current_kit is None:
        return UNKNOWN, None
    if as_scaffolded is None:
        return NEW_UPSTREAM, None
    if current_kit is None:
        return REMOVED_UPSTREAM, None

    locally_modified = normalized_target != as_scaffolded
    upstream_changed = as_scaffolded != current_kit

    if locally_modified and upstream_changed:
        status = BOTH_CHANGED
    elif upstream_changed:
        status = UPSTREAM_ONLY
    elif locally_modified:
        status = LOCAL_ONLY
    else:
        status = UNCHANGED

    diff = None
    if upstream_changed:
        diff = "\n".join(
            difflib.unified_diff(
                as_scaffolded.splitlines(), current_kit.splitlines(),
                fromfile=f"{kit_rel} (as scaffolded)", tofile=f"{kit_rel} (current kit)",
                lineterm="", n=1,
            )
        )
    return status, diff


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("target", nargs="?", default=".", type=Path)
    parser.add_argument("--kit-path", required=True, type=Path, help="path to a clone of platform-starter-kit to diff against")
    parser.add_argument("--show-diffs", action="store_true", help="print the unified diff for every upstream-changed file")
    args = parser.parse_args()

    target = args.target.resolve()
    kit_path = args.kit_path.resolve()

    if not (kit_path / "tools" / "_platform_kit.py").exists():
        print(f"--kit-path {kit_path} doesn't look like a platform-starter-kit checkout", file=sys.stderr)
        return 2

    sha, app_name = parse_manifest(target)
    if sha is None:
        print(f"No PLATFORM-KIT.md (or no recorded commit) found in {target} — was this repo scaffolded with tools/scaffold.py?", file=sys.stderr)
        return 2

    variants = case_variants(slugify(app_name or "app"))
    current_kit_sha = kit_commit_sha(kit_path)

    print()
    print(f"Sync check: {target}")
    print(f"  Scaffolded from kit commit: {sha[:12]}")
    print(f"  Kit at {kit_path} is currently at: {current_kit_sha[:12] if len(current_kit_sha) > 12 else current_kit_sha}")
    print("=" * 65)

    counts = {}
    upstream_diffs = []
    for target_rel, kit_rel in sorted(discover_file_pairs(target)):
        status, diff = check_file(target, target_rel, kit_rel, kit_path, sha, variants)
        counts[status] = counts.get(status, 0) + 1
        if status != UNCHANGED:
            print(f"{ICONS[status]} {status:<18} {target_rel}")
        if diff:
            upstream_diffs.append((target_rel, diff))

    print("=" * 65)
    print(f"{ICONS[UNCHANGED]} {counts.get(UNCHANGED, 0)} unchanged, "
          f"{ICONS[LOCAL_ONLY]} {counts.get(LOCAL_ONLY, 0)} locally modified, "
          f"{ICONS[UPSTREAM_ONLY]} {counts.get(UPSTREAM_ONLY, 0)} upstream changed, "
          f"{ICONS[BOTH_CHANGED]} {counts.get(BOTH_CHANGED, 0)} both changed")

    if upstream_diffs and args.show_diffs:
        for target_rel, diff in upstream_diffs:
            print()
            print(f"--- {target_rel} ---")
            print(diff)
    elif upstream_diffs:
        print(f"Re-run with --show-diffs to see what changed in the {len(upstream_diffs)} upstream-changed file(s).")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
