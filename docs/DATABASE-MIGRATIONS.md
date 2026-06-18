# Database migrations — expand/contract for zero-downtime deploys

A schema change is the most common reason a deploy that passed every CI
gate still takes production down. The cause is almost always the same: a
**rolling deploy runs the old and new app versions at the same time**
against **one shared database**. Any migration the *old* version can't
tolerate breaks it the moment the migration applies — before the new
version has fully rolled out.

`tools/check_migrations.py` is the gate that catches these before merge
(`ci-cd/github-actions/ci.yml` runs it; see below). This doc is the
pattern it points you at when it fails.

## The rule

> Every migration must be safe for the **currently-running** app version,
> not just the new one.

That means schema changes and the code that depends on them ship in
**separate deploys**, in a specific order.

## Expand / contract

Split any breaking change into phases, each its own PR/deploy:

| Phase | Schema | Code | Safe because |
|---|---|---|---|
| **1. Expand** | Add the new column/table (nullable, or with a default) | Old code ignores it; new code may start writing it | Additive — old version doesn't know it exists |
| **2. Migrate** | Backfill existing rows | App dual-writes old + new during transition | Both columns valid the whole time |
| **3. Contract** | Drop the old column/table | Only after no running version reads it | Nothing references it anymore |

A column **rename** is not one operation — it's a drop + an add, which is
two breaking changes. Do it as: add new → dual-write → backfill → switch
reads → drop old. Four deploys, zero downtime.

## What the gate flags

`tools/check_migrations.py` greps migration files (`.sql`, Alembic `.py`,
Rails `.rb`) for the operations that are unsafe during a rolling deploy:

- `DROP TABLE` / `DROP COLUMN` / `ALTER TABLE ... DROP`
- `RENAME TABLE` / `RENAME COLUMN` / `RENAME TO`
- `SET NOT NULL`, or `ADD COLUMN ... NOT NULL` without a `DEFAULT`
- the Alembic equivalents (`op.drop_table`, `op.drop_column`,
  `op.alter_column(..., nullable=False)`)

These aren't *forbidden* — the contract phase legitimately drops columns.
They just have to be **deliberate**. When a flagged statement is the
intentional contract-phase step and the expand phase already shipped,
acknowledge it inline so the gate passes and the decision is visible in
review:

```sql
ALTER TABLE users DROP COLUMN legacy_name;  -- migration-safety: ack contract phase, dual-write removed in v2.3
```

## Running it

```bash
# scans migrations/, alembic/versions/, db/migrate/, prisma/migrations/ by default
python3 tools/check_migrations.py

# or point it at your migrations explicitly
python3 tools/check_migrations.py path/to/migrations
```

Exit code is non-zero if any unacknowledged breaking statement is found,
so it gates a PR the same way the test and lint jobs do.

## Beyond the gate

This is a static check — it catches the common destructive DDL, not every
possible incompatibility (a `CREATE INDEX` without `CONCURRENTLY` locks
writes on Postgres; a type change can rewrite a whole table). For
higher-stakes schemas, layer a tool that understands your engine's
locking behaviour — `squawk` (Postgres) or `gh-ost`/`pt-online-schema-change`
(MySQL) — on top. See `docs/ENTERPRISE-TOOLING.md`.
