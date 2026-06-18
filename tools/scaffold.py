#!/usr/bin/env python3
"""Scaffold a new repo from this kit — the self-service mechanism a
"copy folders and edit 17 placeholders by hand" starter kit is missing.

Answers the app name and a handful of capability toggles once, then emits
a new repo with every `your-app`/`YourApp`/"Your App" placeholder already
resolved, a version-stamped PLATFORM-KIT.md manifest (consumed by
sync_check.py for drift detection), a catalog-info.yaml so the new
service is discoverable in a Backstage-style catalog from day one, and a
TODO.md trimmed to only the placeholders that genuinely can't be
automated (cloud credentials, a fresh UserSecretsId, your actual GCP
project ID, ...).

Usage:
    python3 tools/scaffold.py --app-name my-service --output ../my-service \\
        [--cloud none|fly|azure|aws|gcp] \\
        [--no-observability] [--no-security] [--no-load-testing] [--no-claude-commands] \\
        [--telemetry] [--force]

Run from the root of a clone of this kit.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from _platform_kit import (
    ALWAYS_DIRS,
    ALWAYS_FILES,
    CLAUDE_COMMANDS_DST,
    CLAUDE_COMMANDS_SRC,
    EXECUTABLE_TARGETS,
    GOVERNANCE_DST,
    GOVERNANCE_SRC,
    IAC_GCP_DST,
    IAC_GCP_SRC,
    KIT_ROOT,
    OPTIONAL_DIRS,
    TEXT_SUFFIXES,
    case_variants,
    kit_commit_sha,
    slugify,
    substitute_placeholders,
)

TELEMETRY_LOCAL_PATH = Path.home() / ".platform-kit" / "telemetry.jsonl"


def copy_and_substitute(src: Path, dst: Path, variants: dict):
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.suffix in TEXT_SUFFIXES:
        text = src.read_text(errors="ignore")
        dst.write_text(substitute_placeholders(text, variants))
    else:
        shutil.copy2(src, dst)


def copy_tree(src_root: Path, dst_root: Path, variants: dict):
    for src in src_root.rglob("*"):
        if src.is_dir():
            continue
        rel = src.relative_to(src_root)
        copy_and_substitute(src, dst_root / rel, variants)


def write_manifest(output: Path, app_name: str, args, sha: str):
    content = f"""# PLATFORM-KIT.md

Provenance record for this repo's adoption of `platform-starter-kit`.
Don't delete this even after dropping capabilities you don't need —
`tools/sync_check.py` reads the commit SHA below to tell you what's
changed upstream since you scaffolded.

- Generated: {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}
- Source kit commit: `{sha}`
- App name: `{app_name}`
- Cloud target: `{args.cloud}`
- Capabilities included:
  - observability: {not args.no_observability}
  - security: {not args.no_security}
  - load-testing: {not args.no_load_testing}
  - claude-commands: {not args.no_claude_commands}
  - iac-terraform (gcp-cloud-run): {args.cloud == "gcp"}
  - governance/policy-as-code (example only, GCP-specific): {args.cloud == "gcp" and not args.no_governance}

Re-run `python3 tools/doctor.py .` periodically as you add your actual
application code — the gaps it reports now (no app code yet) are expected;
the ones it reports once you have a real service are not.

Run `python3 tools/sync_check.py . --kit-path /path/to/platform-starter-kit`
periodically to see what's changed in the kit since `{sha[:12]}`.
"""
    (output / "PLATFORM-KIT.md").write_text(content)


def write_catalog_info(output: Path, variants: dict, args):
    content = f"""# Backstage-style catalog registration for this service. Fill in the
# annotation/owner placeholders once this repo has a real remote and team.
apiVersion: backstage.io/v1alpha1
kind: Component
metadata:
  name: {variants["kebab"]}
  description: >-
    {variants["title"]} — scaffolded from platform-starter-kit.
  annotations:
    # TODO: github.com/project-slug: your-org/{variants["kebab"]}
    backstage.io/techdocs-ref: dir:.
  tags:
    - scaffolded-from-platform-starter-kit
spec:
  type: service
  lifecycle: experimental
  # TODO: replace with your actual Backstage group reference
  owner: TODO-team
"""
    (output / "catalog-info.yaml").write_text(content)


# Fallback detect-secrets v1.5.0 baseline (default plugins/filters, no
# results) used only when `detect-secrets` isn't installed at scaffold time.
# An empty `plugins_used` would make the hook scan with no detectors, so the
# real default plugin set is embedded to keep the fallback protective.
_SECRETS_BASELINE_TEMPLATE = {
    "version": "1.5.0",
    "plugins_used": [
        {"name": "ArtifactoryDetector"},
        {"name": "AWSKeyDetector"},
        {"name": "AzureStorageKeyDetector"},
        {"name": "Base64HighEntropyString", "limit": 4.5},
        {"name": "BasicAuthDetector"},
        {"name": "CloudantDetector"},
        {"name": "DiscordBotTokenDetector"},
        {"name": "GitHubTokenDetector"},
        {"name": "GitLabTokenDetector"},
        {"name": "HexHighEntropyString", "limit": 3.0},
        {"name": "IbmCloudIamDetector"},
        {"name": "IbmCosHmacDetector"},
        {"name": "IPPublicDetector"},
        {"name": "JwtTokenDetector"},
        {"name": "KeywordDetector", "keyword_exclude": ""},
        {"name": "MailchimpDetector"},
        {"name": "NpmDetector"},
        {"name": "OpenAIDetector"},
        {"name": "PrivateKeyDetector"},
        {"name": "PypiTokenDetector"},
        {"name": "SendGridDetector"},
        {"name": "SlackDetector"},
        {"name": "SoftlayerDetector"},
        {"name": "SquareOAuthDetector"},
        {"name": "StripeDetector"},
        {"name": "TelegramBotTokenDetector"},
        {"name": "TwilioKeyDetector"},
    ],
    "filters_used": [
        {"path": "detect_secrets.filters.allowlist.is_line_allowlisted"},
        {"path": "detect_secrets.filters.common.is_ignored_due_to_verification_policies", "min_level": 2},
        {"path": "detect_secrets.filters.heuristic.is_indirect_reference"},
        {"path": "detect_secrets.filters.heuristic.is_likely_id_string"},
        {"path": "detect_secrets.filters.heuristic.is_lock_file"},
        {"path": "detect_secrets.filters.heuristic.is_not_alphanumeric_string"},
        {"path": "detect_secrets.filters.heuristic.is_potential_uuid"},
        {"path": "detect_secrets.filters.heuristic.is_prefixed_with_dollar_sign"},
        {"path": "detect_secrets.filters.heuristic.is_sequential_string"},
        {"path": "detect_secrets.filters.heuristic.is_swagger_file"},
        {"path": "detect_secrets.filters.heuristic.is_templated_secret"},
    ],
    "results": {},
}


def write_secrets_baseline(output: Path):
    """Generate a detect-secrets baseline so the detect-secrets pre-commit
    hook (configured with --baseline .secrets.baseline) works on the very
    first commit instead of erroring on a missing file. Prefers a live
    `detect-secrets scan` (correct schema for the installed version); falls
    back to the embedded default baseline if the tool isn't available."""
    baseline = output / ".secrets.baseline"
    try:
        # --all-files scans the filesystem rather than `git ls-files` — the
        # output dir isn't a git repo yet, and without this the baseline
        # would be empty and fail to allowlist the kit's worked-example
        # placeholders (appuser:apppass, ci-test-secret-key, ...), blocking
        # the adopter's very first commit.
        result = subprocess.run(
            ["detect-secrets", "scan", "--all-files"],
            cwd=output, capture_output=True, text=True, timeout=60,
        )
        if result.returncode == 0 and result.stdout.strip():
            baseline.write_text(result.stdout)
            return
    except (OSError, subprocess.SubprocessError):
        pass
    event = dict(_SECRETS_BASELINE_TEMPLATE)
    event["generated_at"] = datetime.now(timezone.utc).isoformat()
    baseline.write_text(json.dumps(event, indent=2) + "\n")


def write_codeowners(output: Path):
    content = """# Default owner for everything in this repo. GitHub uses this to
# auto-request review on every PR opened against the branches it
# protects — replace the placeholder below with your actual team or
# handle. A CODEOWNERS file naming nobody real is the same as having
# none, just quieter about it.
* @TODO-set-your-team-or-handle
"""
    gh_dir = output / ".github"
    gh_dir.mkdir(parents=True, exist_ok=True)
    (gh_dir / "CODEOWNERS").write_text(content)


def write_dependabot(output: Path, args):
    content = """# Keep this updated as you add ecosystems — this only covers what
# tools/scaffold.py copied in. Add "pip"/"npm"/"docker"/etc. entries
# once you add your actual application code.
version: 2
updates:
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
"""
    if args.cloud == "gcp":
        content += """  - package-ecosystem: "terraform"
    directory: "/iac-terraform/gcp-cloud-run"
    schedule:
      interval: "weekly"
"""
    gh_dir = output / ".github"
    gh_dir.mkdir(parents=True, exist_ok=True)
    (gh_dir / "dependabot.yml").write_text(content)


def write_readme(output: Path, variants: dict, args):
    included = []
    if not args.no_security:
        included.append("- `security/` — OWASP manual checks + ZAP scan wrapper")
    if not args.no_observability:
        included.append("- `observability/` — Jaeger + Prometheus + Grafana overlay")
    if not args.no_load_testing:
        included.append("- `load-testing/` — k6 + Locust scenarios")
    if args.cloud == "gcp":
        included.append(f"- `iac-terraform/gcp-cloud-run/` — parameterized Cloud Run module, `app_name` pre-set to `{variants['kebab']}`")
        if not args.no_governance:
            included.append("- `governance/policy-as-code/` — example Conftest/OPA policy-as-code guardrails for the Terraform module")
    if not args.no_claude_commands:
        included.append("- `.claude/commands/` — Claude Code review/fix commands")
    included.append("- `.github/workflows/`, `.pre-commit-config.yaml` — CI/CD pipeline shape + pre-commit security baseline (incl. IaC + migration checks)")
    included.append("- `.github/workflows/drift-detection.yml` — scheduled `terraform plan` drift check (ships gated; configure cloud auth to enable)")
    included.append("- `.gitignore`, `.secrets.baseline` — `.env` can't be committed; detect-secrets hook works on first commit")
    included.append("- `Makefile`, `.devcontainer/`, `.tool-versions`, `.env.example` — paved inner loop (`make help` for the task list)")
    included.append("- `operations/` — rollback / incident / postmortem runbooks + SLO definitions")
    included.append("- `tools/check_migrations.py`, `docs/DATABASE-MIGRATIONS.md`, `docs/FEATURE-FLAGS.md` — schema-safety gate + safe-release patterns")
    included.append("- `catalog-info.yaml` — Backstage catalog registration (fill in the owner/project-slug TODOs)")
    included.append("- `.github/CODEOWNERS`, `.github/dependabot.yml` — review ownership + dependency-update policy (fill in the CODEOWNERS TODO)")

    content = f"""# {variants["title"]}

Generated by `platform-starter-kit`'s `tools/scaffold.py`. See
`PLATFORM-KIT.md` for what was included and which kit commit this came
from, and `TODO.md` for the placeholders that couldn't be automated
(cloud credentials, project IDs, secrets — anything that needs a value
only you have).

## What's here

{chr(10).join(included)}

## Next steps

1. Add your actual application code (this scaffold doesn't include one).
2. `cp .env.example .env` and fill in local values, then `make setup`.
3. Fill in the `TODO` commands in the `Makefile` (`setup`/`test`/`lint`/`fmt`).
4. Work through `TODO.md`.
5. `make doctor` (readiness) and `make migrations` (schema safety) as you go.
6. `make sync` later, to see what's changed upstream in the kit.
"""
    (output / "README.md").write_text(content)


# Each row: (predicate based on args, text)
TODO_ROWS = [
    (lambda a: True,
     "| `.github/workflows/ci.yml` | `working-directory: backend` / `frontend` | Your repo's actual source directories |"),
    (lambda a: True,
     "| `.github/workflows/ci.yml` | `services: postgres:` block | Your actual database engine, if not Postgres — see `docs/TECH-STACK-SWAP-GUIDE.md` |"),
    (lambda a: a.cloud in ("fly", "none"),
     "| `.github/workflows/publish.yml` | Fly.io deploy jobs' `if: false` | Remove once `FLY_API_TOKEN` + GitHub Environments are configured |"),
    (lambda a: a.cloud in ("azure", "none"),
     "| `.github/workflows/publish.yml` | Azure deploy job's `if: false` | Remove once `azd pipeline config` has been run |"),
    (lambda a: a.cloud in ("aws", "none"),
     "| `.github/workflows/publish.yml` | AWS deploy job's `if: false`, `deploy/aws-deploy.sh` | Remove once AWS OIDC role + secrets are configured; provide your own deploy script |"),
    (lambda a: a.cloud in ("gcp", "none"),
     "| `.github/workflows/publish.yml` | GCP deploy job's `if: false`, `deploy/gcp-deploy.sh` | Remove once Workload Identity Federation is configured; provide your own deploy script, or `terraform apply` directly |"),
    (lambda a: a.cloud == "gcp",
     "| `iac-terraform/gcp-cloud-run/` | `terraform.tfvars`, GCS backend block | Your GCP project ID and a remote-state bucket (`app_name` is already set) |"),
    (lambda a: a.cloud == "gcp",
     "| `.github/workflows/drift-detection.yml` | `if: false`, cloud auth + backend | Remove `if: false` once WIF + remote state are configured, to enable scheduled drift detection |"),
    (lambda a: a.cloud == "gcp" and not a.no_governance,
     "| `governance/policy-as-code/policy/terraform_guardrails.rego` | Example only | Adapt the resource checks to your own requirements, or delete the folder if you don't want a policy-as-code gate — see `governance/policy-as-code/README.md` |"),
    (lambda a: not a.no_security,
     "| `security/manual-checks.sh` | `ENDPOINTS` configuration block | Your own auth/resource routes |"),
    (lambda a: not a.no_observability,
     "| `observability/prometheus.yml` | `job_name: app` | Only if your Compose service isn't named `app` |"),
    (lambda a: not a.no_load_testing,
     "| `load-testing/k6/*.js`, `load-testing/locust/locustfile.py` | Worked-example endpoint paths/payloads | Your own API's routes and request bodies |"),
    (lambda a: True,
     "| `catalog-info.yaml` | `project-slug` annotation, `owner: TODO-team` | Your repo's slug and your actual Backstage team reference |"),
    (lambda a: True,
     "| `.github/CODEOWNERS` | `@TODO-set-your-team-or-handle` | Your actual GitHub team or handle |"),
]


def write_todo(output: Path, args):
    rows = [text for predicate, text in TODO_ROWS if predicate(args)]
    content = f"""# TODO — placeholders `tools/scaffold.py` couldn't resolve for you

Everything app-name-shaped was already substituted. These rows need a
value only you have (credentials, routes, project IDs) or a decision
`scaffold.py` can't make for you.

| File | Placeholder | What to set it to |
|---|---|---|
{chr(10).join(rows)}
"""
    (output / "TODO.md").write_text(content)


def record_telemetry(args, sha: str):
    """Opt-in only — never called unless --telemetry is passed. Never blocks
    or fails scaffolding regardless of outcome. No app name, output path, or
    other identifying info is recorded — just what was chosen, not who/where."""
    event = {
        "event": "scaffold",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "kit_commit": sha,
        "cloud": args.cloud,
        "observability": not args.no_observability,
        "security": not args.no_security,
        "load_testing": not args.no_load_testing,
        "claude_commands": not args.no_claude_commands,
    }
    url = os.environ.get("PLATFORM_KIT_TELEMETRY_URL")
    if url:
        try:
            req = urllib.request.Request(
                url, data=json.dumps(event).encode(),
                headers={"Content-Type": "application/json"}, method="POST",
            )
            urllib.request.urlopen(req, timeout=3)
            print(f"Telemetry: posted to {url}")
        except Exception as exc:  # noqa: BLE001 — telemetry must never break scaffolding
            print(f"Telemetry: POST to {url} failed ({exc}) — not retrying")
        return
    try:
        TELEMETRY_LOCAL_PATH.parent.mkdir(parents=True, exist_ok=True)
        with TELEMETRY_LOCAL_PATH.open("a") as fh:
            fh.write(json.dumps(event) + "\n")
        print(f"Telemetry: recorded locally at {TELEMETRY_LOCAL_PATH}")
        print("  (set PLATFORM_KIT_TELEMETRY_URL to send to your org's own collector instead)")
    except OSError as exc:
        print(f"Telemetry: could not write {TELEMETRY_LOCAL_PATH} ({exc})")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--app-name", required=True, help="e.g. my-service (case/spacing normalized automatically)")
    parser.add_argument("--output", required=True, type=Path, help="path to the new repo directory (created if missing)")
    parser.add_argument("--cloud", choices=["none", "fly", "azure", "aws", "gcp"], default="none")
    parser.add_argument("--no-observability", action="store_true")
    parser.add_argument("--no-security", action="store_true")
    parser.add_argument("--no-load-testing", action="store_true")
    parser.add_argument("--no-claude-commands", action="store_true")
    parser.add_argument("--no-governance", action="store_true", help="skip governance/policy-as-code/ (only copied when --cloud gcp, since the example policy targets that module)")
    parser.add_argument("--telemetry", action="store_true", help="opt-in: record an anonymized capability-choice event (local file, or PLATFORM_KIT_TELEMETRY_URL if set)")
    parser.add_argument("--force", action="store_true", help="allow scaffolding into a non-empty directory")
    args = parser.parse_args()

    kebab = slugify(args.app_name)
    if kebab != args.app_name:
        print(f"Normalized app name '{args.app_name}' -> '{kebab}'")
    variants = case_variants(kebab)

    output = args.output.resolve()
    if output.exists() and any(output.iterdir()) and not args.force:
        print(f"Refusing to scaffold into non-empty directory: {output} (use --force)", file=sys.stderr)
        return 1
    output.mkdir(parents=True, exist_ok=True)

    for kit_rel, target_rel in ALWAYS_FILES:
        copy_and_substitute(KIT_ROOT / kit_rel, output / target_rel, variants)
        if target_rel in EXECUTABLE_TARGETS:
            (output / target_rel).chmod(0o755)

    for kit_dir, target_dir in ALWAYS_DIRS:
        copy_tree(KIT_ROOT / kit_dir, output / target_dir, variants)

    if not args.no_claude_commands:
        for src in (KIT_ROOT / CLAUDE_COMMANDS_SRC).glob("*.md"):
            copy_and_substitute(src, output / CLAUDE_COMMANDS_DST / src.name, variants)

    flag_map = {
        "observability": args.no_observability,
        "security": args.no_security,
        "load_testing": args.no_load_testing,
    }
    for kit_dir, target_dir, capability in OPTIONAL_DIRS:
        if not flag_map[capability]:
            copy_tree(KIT_ROOT / kit_dir, output / target_dir, variants)

    if args.cloud == "gcp":
        copy_tree(KIT_ROOT / IAC_GCP_SRC, output / IAC_GCP_DST, variants)
        tfvars = output / IAC_GCP_DST / "terraform.tfvars.example"
        tfvars.write_text(
            f'app_name   = "{variants["kebab"]}"\n'
            f'project_id = "REPLACE-WITH-YOUR-GCP-PROJECT-ID"\n'
            f'image_tag  = "sha-REPLACE"\n'
            f'github_repository = "your-org/{variants["kebab"]}"\n'
        )
        if not args.no_governance:
            copy_tree(KIT_ROOT / GOVERNANCE_SRC, output / GOVERNANCE_DST, variants)

    sha = kit_commit_sha()
    write_manifest(output, kebab, args, sha)
    write_catalog_info(output, variants, args)
    write_secrets_baseline(output)
    write_codeowners(output)
    write_dependabot(output, args)
    write_readme(output, variants, args)
    write_todo(output, args)

    if args.telemetry:
        record_telemetry(args, sha)

    print()
    print(f"Scaffolded '{variants['title']}' into {output}")
    print(f"Source kit commit: {sha}")
    print()
    print("Next:")
    print(f"  cd {output}")
    print("  python3 tools/doctor.py .   # confirm readiness as you add app code")
    print("  cat TODO.md                  # only the placeholders that needed a real decision")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
