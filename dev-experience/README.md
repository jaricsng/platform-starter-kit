# Developer experience — the paved inner loop

The platform-engineering goal of this folder: a developer spends their day
on application code, not on remembering tool commands or fighting a broken
local setup. Everything here is copied to your repo **root** by
`tools/scaffold.py` (or copy it by hand).

| File | What it gives you |
|---|---|
| `Makefile` | One verb per task — `make test`, `make run`, `make lint`, `make doctor`, `make obs-up`. CI calls the **same** targets, so local and CI can't drift. Run `make help` for the list. |
| `.devcontainer/devcontainer.json` | A one-click reproducible dev environment (VS Code "Reopen in Container" / GitHub Codespaces). Pins Python/Node/Terraform, runs `make setup` on create. |
| `.tool-versions` | Pins exact toolchain versions for asdf/mise — the single source of truth that should match `ci.yml`'s `setup-*` steps. |
| `.env.example` | Documents every env var the service reads, with **no real secrets**. Copy to `.env` (git-ignored) and fill in locally. |
| `.editorconfig` | Editor-agnostic whitespace/encoding baseline. |

## The contract

The Makefile is deliberately the only interface anyone needs to learn. The
targets that wrap **this kit's own tooling** work immediately:

- `make doctor` → `tools/doctor.py` (readiness check)
- `make migrations` → `tools/check_migrations.py` (schema-safety gate)
- `make obs-up` / `make obs-down` → the observability stack
- `make sync` → `tools/sync_check.py` (upstream drift report)

The app-specific targets (`setup`, `test`, `lint`, `fmt`) carry a `TODO` —
fill in your stack's actual command **once**, in the Makefile, and every
developer and every CI job inherits it. That single edit is the difference
between onboarding docs that rot and a paved road that doesn't.

## Keeping it honest

`.tool-versions` and `ci-cd/github-actions/ci.yml` should name the same
versions. If they drift, "works locally" and "works in CI" drift with
them — which is exactly what this folder exists to prevent.
