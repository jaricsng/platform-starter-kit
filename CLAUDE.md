# CLAUDE.md

Guidance for Claude Code when working **on this repo itself** (the kit),
not on a project that has adopted it.

## What this is

`platform-starter-kit` is a GitHub template repo: a library of DevSecOps
platform assets (CI/CD shape, observability stack, load-test scenarios, a
Terraform module, pen-test scripts, Claude Code commands) extracted from a
working three-tier reference app and organized by **capability**, not by
the app they came from. Adopters copy individual folders into their own
repos — there is no single app here to "run." `examples/minimal-service/`
exists solely to prove the extracted pieces still work together.

Read `README.md` for the capability map, `docs/ASSET-CATALOG.md` for
per-asset provenance/reusability notes, `docs/ARCHITECTURE-FIT.md` for the
architecture this kit assumes (containerized HTTP services, OTel,
serverless-container deploy targets) and what's a poor fit,
`docs/ENTERPRISE-TOOLING.md` for how each free/OSS tool maps to an
enterprise replacement, `docs/TECH-STACK-SWAP-GUIDE.md` for the file-level
mechanics of swapping any single piece for a different one, and
`docs/TODO.md` for every placeholder an adopter needs to fill in.
`tools/scaffold.py` is the self-service mechanism that resolves most of
those placeholders automatically; `tools/doctor.py` automates
`docs/ARCHITECTURE-FIT.md`'s checklist; `tools/sync_check.py` reports what's
changed upstream in the kit since a given repo was scaffolded;
`tools/check_migrations.py` is the schema-safety gate
(`docs/DATABASE-MIGRATIONS.md`). They share `tools/_platform_kit.py` for
placeholder substitution and the kit-file map (`ALWAYS_FILES`/`ALWAYS_DIRS`/
`OPTIONAL_DIRS`/...) — change that mapping in one place, not per tool. The
`dev-experience/` folder is copied to a scaffolded repo's *root* (Makefile,
devcontainer, .env.example); `operations/` holds Day-2 runbooks + SLOs. Keep
`docs/TODO.md` in sync with `scaffold.py` — if a row is added there for
something `scaffold.py` *could* substitute (an app name, a generic
resource label), prefer teaching the scaffolder over leaving it manual.

## Repo-specific rules

- **Every asset must work standing alone.** Nothing in here may depend on
  application source code (there isn't any) or on another capability
  folder. If you add something that only makes sense alongside app code,
  it belongs in `docs/ASSET-CATALOG.md`'s "Not extracted" list instead.
- **Placeholders, not real values.** Cloud account IDs, app names, and
  endpoints are deliberately `TODO-*` or example paths (e.g.
  `backend/app/`). Don't replace them with something that looks real —
  add a row to `docs/TODO.md` instead.
- **`claude-commands/*.md` are slash commands, not Skills.** They use
  `$ARGUMENTS` and are meant to be copied into an adopter's
  `.claude/commands/`. Each file carries `description`/`argument-hint`
  frontmatter and an "Adapted from a three-tier app lab" note — keep both
  when editing, and keep the note's example paths in sync with whatever
  the command body references.
- **Versioning is structural, not semantic-per-feature** (see
  `CHANGELOG.md`): major = a folder moves/is removed, minor = a new
  capability folder is added, patch = doc/template fixes only. Update
  `CHANGELOG.md` under `[Unreleased]` for anything touching layout.

## Known cross-file gotchas

- `observability/recording_rules.yml` uses the pre-1.23 OTel metric name
  `http_server_duration_milliseconds`; `observability/grafana/dashboards/starter-dashboard.json`
  queries the newer `http_server_request_duration_seconds`. This mismatch
  is intentionally documented in `docs/ASSET-CATALOG.md` rather than
  "fixed" — picking one is an adopter decision, not this kit's call.
  Don't silently reconcile these without flagging it.
- Grafana provisioning files must use Grafana's own file-provisioning
  schema (`title`/`uid`/`condition`/`data`), not Mimir/Cortex ruler syntax
  (`alert`/`expr`/`for`) — Grafana crash-loops on the latter. Prometheus
  `rule_files` must be top-level, not nested under `global:`. Both were
  real bugs found and fixed in this repo's history; if you touch either
  file, re-run the `minimal-service-smoke` job locally before assuming it
  still boots.
- The deploy jobs in `ci-cd/github-actions/publish.yml` and the
  `detect-drift` job in `drift-detection.yml` ship `if: false` on purpose
  (adopters remove it to activate). `actionlint` flags these as
  "constant expression in condition" — that's expected, not a regression;
  don't delete the `if: false`. These adopter-template workflows live under
  `ci-cd/github-actions/` and aren't scanned by `validate-kit.yml` anyway.
- `ci-cd/github-actions/ci.yml`'s Conftest gate is intentionally active but
  soft (`continue-on-error: true` = report, not block). Don't "fix" it to
  hard-fail by default — that's an adopter decision (remove the line). The
  pre-commit `terraform_*` hooks need `terraform`/`tfsec` installed locally;
  they no-op when no `*.tf` is staged.

## Validating changes

`.github/workflows/validate-kit.yml` is this repo's own CI (separate from
the CI/CD *templates* adopters copy out of `ci-cd/`). Before claiming a
change is done, run the relevant piece locally:

```bash
# Terraform module
cd iac-terraform/gcp-cloud-run && terraform init -backend=false && terraform validate && terraform fmt -check -recursive

# Observability + example service boot end-to-end
docker compose --project-directory . \
  -f examples/minimal-service/docker-compose.yml \
  -f observability/docker-compose.observability.yml \
  --profile observability up --build -d
curl -sf http://localhost:8000/health && curl -sf http://localhost:8000/ready
docker compose --project-directory . \
  -f examples/minimal-service/docker-compose.yml \
  -f observability/docker-compose.observability.yml \
  --profile observability down -v

# Pre-commit config (now includes terraform_* + a local check-migrations hook)
pre-commit validate-config ci-cd/pre-commit/.pre-commit-config.yaml

# tools/ — if you touched scaffold.py, doctor.py, sync_check.py, or _platform_kit.py
python3 tools/doctor.py examples/minimal-service   # should report only the known test gap
rm -rf /tmp/scaffold-smoke
python3 tools/scaffold.py --app-name smoke-test --output /tmp/scaffold-smoke --cloud gcp
python3 /tmp/scaffold-smoke/tools/doctor.py /tmp/scaffold-smoke   # 3 expected FAILs (no Dockerfile/tests/OTel yet) + WARN (catalog owner); the Gitignore/secrets-baseline check should PASS (scaffold emits both)
python3 tools/sync_check.py /tmp/scaffold-smoke --kit-path . --show-diffs   # sanity-check the diff output is readable
test -f /tmp/scaffold-smoke/.gitignore && test -f /tmp/scaffold-smoke/.secrets.baseline && echo "scaffold security defaults present"
rm -rf /tmp/scaffold-smoke

# governance/policy-as-code — if you touched the Rego policy
cd governance/policy-as-code
conftest test --policy policy examples/passing-plan.json   # expect: exit 0, 1 warning
conftest test --policy policy examples/failing-plan.json   # expect: exit 1, 2 failures
cd ../..

# dev-experience/ — if you touched the Makefile (tabs, not spaces!)
make -f dev-experience/Makefile help   # must list targets, no "missing separator" error

# tools/check_migrations.py — if you touched it, test both paths
printf 'ALTER TABLE t DROP COLUMN c;\n' > /tmp/m.sql
python3 tools/check_migrations.py /tmp/m.sql   # expect: exit 1, flags DROP COLUMN
printf 'ALTER TABLE t ADD COLUMN c TEXT;\n' > /tmp/m.sql
python3 tools/check_migrations.py /tmp/m.sql   # expect: exit 0
rm -f /tmp/m.sql
```

Note: the observability boot above now includes Alertmanager — if you touch
`alertmanager.yml`/`prometheus.yml`'s `alerting:` block, keep the smoke
boot in the validation list (Alertmanager crash-loops on a malformed
receiver URL, so placeholder URLs must stay structurally valid).
