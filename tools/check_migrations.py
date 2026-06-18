#!/usr/bin/env python3
"""Flag backward-incompatible database migrations before they reach a deploy.

The single most common cause of a failed-but-"green-CI" production deploy
is a schema change that the *old* app version (still running during a
rolling deploy) can't tolerate: a dropped column it still SELECTs, a
NOT NULL added to a column it still INSERTs without, a renamed table.

docs/DATABASE-MIGRATIONS.md describes the expand/contract pattern that
avoids this. This script is the gate that enforces it: it greps migration
files for the dangerous DDL statements and fails (exit 1) unless each is
explicitly acknowledged with an inline `migration-safety: ack <reason>`
comment — so "I know this is destructive and the expand phase already
shipped" is a deliberate, reviewable decision, not an accident.

Usage:
    python3 tools/check_migrations.py [migrations_dir ...]

Defaults to scanning common migration locations if none are given:
    migrations/  alembic/versions/  db/migrate/  prisma/migrations/

Exit code: 0 if no unacknowledged dangerous statements, 1 otherwise.
"""
import re
import sys
from pathlib import Path

DEFAULT_DIRS = [
    "migrations",
    "alembic/versions",
    "db/migrate",
    "prisma/migrations",
]

MIGRATION_SUFFIXES = {".sql", ".py", ".rb"}

ACK_MARKER = "migration-safety: ack"

# (regex, human label) — each matches a backward-incompatible operation.
# Case-insensitive, applied per logical line.
DANGEROUS = [
    (re.compile(r"\bDROP\s+TABLE\b", re.IGNORECASE),
     "DROP TABLE — old app versions still querying it will error mid-deploy"),
    (re.compile(r"\bDROP\s+COLUMN\b", re.IGNORECASE),
     "DROP COLUMN — drop only after no running version references it (contract phase)"),
    (re.compile(r"\bALTER\s+TABLE\b.*\bDROP\b", re.IGNORECASE),
     "ALTER TABLE ... DROP — destructive column/constraint removal"),
    (re.compile(r"\bRENAME\s+(TABLE|COLUMN)\b", re.IGNORECASE),
     "RENAME — a rename is a drop+add to the old version; use expand/contract (add new, dual-write, backfill, drop old)"),
    (re.compile(r"\bRENAME\s+TO\b", re.IGNORECASE),
     "RENAME TO — see RENAME guidance above"),
    (re.compile(r"\bSET\s+NOT\s+NULL\b", re.IGNORECASE),
     "SET NOT NULL — old version may INSERT without this column; backfill + default first"),
    (re.compile(r"\bADD\s+COLUMN\b.*\bNOT\s+NULL\b(?!.*\bDEFAULT\b)", re.IGNORECASE),
     "ADD COLUMN ... NOT NULL without DEFAULT — fails on existing rows / old INSERTs"),
    # Alembic helpers mirror the SQL above.
    (re.compile(r"\bop\.drop_table\(", re.IGNORECASE),
     "op.drop_table() — see DROP TABLE guidance"),
    (re.compile(r"\bop\.drop_column\(", re.IGNORECASE),
     "op.drop_column() — see DROP COLUMN guidance"),
    (re.compile(r"\bop\.alter_column\(.*nullable\s*=\s*False", re.IGNORECASE),
     "op.alter_column(nullable=False) — see SET NOT NULL guidance"),
]


def iter_migration_files(targets):
    for t in targets:
        if t.is_file() and t.suffix in MIGRATION_SUFFIXES:
            yield t
        elif t.is_dir():
            for f in sorted(t.rglob("*")):
                if f.is_file() and f.suffix in MIGRATION_SUFFIXES:
                    yield f


def scan_file(path: Path):
    """Return a list of (lineno, label, line) findings without an ack."""
    findings = []
    try:
        lines = path.read_text(errors="ignore").splitlines()
    except OSError:
        return findings
    for i, line in enumerate(lines, start=1):
        if ACK_MARKER in line.lower():
            continue
        for pattern, label in DANGEROUS:
            if pattern.search(line):
                findings.append((i, label, line.strip()))
                break
    return findings


def main():
    args = sys.argv[1:]
    root = Path.cwd()
    if args:
        targets = [Path(a) for a in args]
    else:
        targets = [root / d for d in DEFAULT_DIRS if (root / d).is_dir()]

    if not targets:
        print("No migration directories found "
              f"(looked for: {', '.join(DEFAULT_DIRS)}). "
              "Pass a path explicitly, or ignore if this service has no DB migrations.")
        return 0

    files = list(iter_migration_files(targets))
    if not files:
        print("No migration files (.sql/.py/.rb) found in the given path(s) — nothing to check.")
        return 0

    total = 0
    for path in files:
        findings = scan_file(path)
        if not findings:
            continue
        total += len(findings)
        try:
            display = path.relative_to(root)
        except ValueError:
            display = path
        print(f"\n❌ {display}")
        for lineno, label, line in findings:
            print(f"   L{lineno}: {label}")
            print(f"        {line}")

    print()
    print("=" * 65)
    if total:
        print(f"❌ {total} backward-incompatible statement(s) in {len(files)} migration file(s) scanned.")
        print("   See docs/DATABASE-MIGRATIONS.md for the expand/contract pattern.")
        print(f"   If a statement is intentional and the expand phase already shipped,")
        print(f"   add a trailing comment containing '{ACK_MARKER} <reason>' on that line.")
        return 1
    print(f"✅ No unacknowledged backward-incompatible statements in {len(files)} migration file(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
