# Contributing

Thanks for helping improve this kit. It's a **library of standalone
DevSecOps platform assets** organized by capability, not an application —
so the contribution rules are a little different from a normal app repo.

## Ground rules (what makes a good contribution here)

1. **Every asset must work standing alone.** Nothing may depend on
   application source code (there isn't any) or on another capability
   folder. If a change only makes sense alongside app code, it belongs in
   `docs/ASSET-CATALOG.md`'s "Not extracted" list, not in the kit.
2. **Placeholders, not real values.** Cloud account IDs, app names, and
   endpoints stay as `TODO-*` or example paths (e.g. `backend/app/`). Don't
   substitute anything that looks real — add a row to `docs/TODO.md`
   instead, and prefer teaching `tools/scaffold.py` to resolve it.
3. **`claude-commands/*.md` are slash commands, not Skills** — keep the
   `description`/`argument-hint` frontmatter and the "Adapted from a
   three-tier app lab" note.
4. **Keep the three pillars intact.** Changes should strengthen, not
   weaken, the kit's *shift-left* (pre-commit + CI gates before merge),
   *start-right* (`tools/scaffold.py` golden path), and *stay-right*
   (policy-as-code, SLOs/alerting, drift detection, runbooks) story.

See [`CLAUDE.md`](CLAUDE.md) for the full repo-specific conventions and
known cross-file gotchas.

## Versioning (structural, not semantic-per-feature)

Update `CHANGELOG.md` under `[Unreleased]` for anything touching layout:

- **major** — a capability folder moves or is removed
- **minor** — a new capability folder is added
- **patch** — documentation or template fixes with no structural change

## Validating your change

Before opening a PR, run the relevant local checks from
[`CLAUDE.md`](CLAUDE.md#validating-changes) — at minimum:

```bash
# Workflows you touched
actionlint .github/workflows/*.yml ci-cd/github-actions/*.yml

# Pre-commit config
pre-commit validate-config ci-cd/pre-commit/.pre-commit-config.yaml

# tools/ (if changed) — scaffold → doctor → sync_check round trip
python3 tools/scaffold.py --app-name smoke --output /tmp/smoke --cloud gcp
python3 /tmp/smoke/tools/doctor.py /tmp/smoke && rm -rf /tmp/smoke

# Observability + example boot end-to-end (if you touched either)
docker compose --project-directory . \
  -f examples/minimal-service/docker-compose.yml \
  -f observability/docker-compose.observability.yml \
  --profile observability up --build -d
```

`.github/workflows/validate-kit.yml` runs the canonical set in CI.

## Pull requests

- Branch from `main`; one logical change per PR.
- Fill in the PR template; it ties back to the versioning/validation rules.
- `@jaricsng` (see `.github/CODEOWNERS`) is requested automatically.
- CI (`validate-kit.yml`) must pass.

## Reporting bugs / requesting assets

Use the issue templates (bug report / asset request). For **security**
issues, follow [`SECURITY.md`](SECURITY.md) — report privately, don't open
a public issue.
