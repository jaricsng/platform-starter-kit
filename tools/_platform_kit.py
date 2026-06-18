"""Shared logic for tools/scaffold.py and tools/sync_check.py.

Single source of truth for: app-name placeholder substitution (and its
inverse, needed by sync_check.py to compare a scaffolded file back against
the kit's still-templated source), and the map of which kit file/directory
ends up at which path in a scaffolded repo. Keeping this in one module is
the same rule TECH-STACK-SWAP-GUIDE.md's footer states: when two tools
need the same fact, fix the shared interface, don't let them drift apart.
"""
import re
import subprocess
from pathlib import Path

# NOTE: this file gets copied into every scaffolded repo (see ALWAYS_FILES
# below), where KIT_ROOT then resolves to *that* repo, not the original
# kit. That's fine today — the only caller of kit_commit_sha() that runs
# from a copied context (sync_check.py) always passes an explicit
# --kit-path and never relies on this default. Keep it that way: don't add
# a new caller of kit_commit_sha(KIT_ROOT) without checking whether it
# might run from a scaffolded copy.
KIT_ROOT = Path(__file__).resolve().parent.parent

# (placeholder string, app-name-case-variant key in case_variants()'s output)
PLACEHOLDER_REPLACEMENTS = [
    ("TODO-your-app-staging", "kebab_staging"),
    ("TODO-your-app-production", "kebab_production"),
    ("your-app", "kebab"),
    ("YourApp", "pascal"),
    ("Your App", "title"),
]

TEXT_SUFFIXES = {
    ".yml", ".yaml", ".md", ".sh", ".py", ".js", ".tf", ".json", ".cfg",
    ".toml", ".txt",
}

# Flat files scaffold.py always copies 1:1 (kit-relative -> target-relative).
# Note the dev-experience/* files land at the repo ROOT — that's where a
# Makefile / .env.example / devcontainer have to be to do their job.
ALWAYS_FILES = [
    ("ci-cd/github-actions/ci.yml", ".github/workflows/ci.yml"),
    ("ci-cd/github-actions/publish.yml", ".github/workflows/publish.yml"),
    ("ci-cd/github-actions/drift-detection.yml", ".github/workflows/drift-detection.yml"),
    ("ci-cd/pre-commit/.pre-commit-config.yaml", ".pre-commit-config.yaml"),
    # Ship .gitignore so a scaffolded repo can't commit the .env the dev is
    # told to create from .env.example (it also ignores tfstate/tfvars/secrets).
    (".gitignore", ".gitignore"),
    # Ship .gitattributes so a mixed-OS team doesn't get CRLF/LF churn (and
    # shell scripts / the Makefile stay LF).
    (".gitattributes", ".gitattributes"),
    ("tools/doctor.py", "tools/doctor.py"),
    ("tools/sync_check.py", "tools/sync_check.py"),
    ("tools/check_migrations.py", "tools/check_migrations.py"),
    ("tools/_platform_kit.py", "tools/_platform_kit.py"),
    # Paved inner loop (dev-experience/ -> repo root)
    ("dev-experience/Makefile", "Makefile"),
    ("dev-experience/.devcontainer/devcontainer.json", ".devcontainer/devcontainer.json"),
    ("dev-experience/.tool-versions", ".tool-versions"),
    ("dev-experience/.env.example", ".env.example"),
    ("dev-experience/.editorconfig", ".editorconfig"),
    # Docs that the copied operations/ runbooks + migration gate link to,
    # so those links resolve inside a scaffolded repo too.
    ("docs/DATABASE-MIGRATIONS.md", "docs/DATABASE-MIGRATIONS.md"),
    ("docs/FEATURE-FLAGS.md", "docs/FEATURE-FLAGS.md"),
]

# Subset of ALWAYS_FILES' targets that need the executable bit set.
EXECUTABLE_TARGETS = {"tools/doctor.py", "tools/sync_check.py", "tools/check_migrations.py"}

# Directories copied 1:1 unconditionally (kit-relative -> target-relative).
ALWAYS_DIRS = [
    ("operations", "operations"),
]

# Directories copied 1:1 when their capability flag is enabled.
# capability key matches the scaffold.py argparse dest (without "no_").
OPTIONAL_DIRS = [
    ("observability", "observability", "observability"),
    ("security", "security", "security"),
    ("load-testing", "load-testing", "load_testing"),
]

# claude-commands/*.md -> .claude/commands/*.md (renamed root, flat glob)
CLAUDE_COMMANDS_SRC = "claude-commands"
CLAUDE_COMMANDS_DST = ".claude/commands"

# iac-terraform/gcp-cloud-run/ -> iac-terraform/gcp-cloud-run/, only when cloud == gcp
IAC_GCP_SRC = "iac-terraform/gcp-cloud-run"
IAC_GCP_DST = "iac-terraform/gcp-cloud-run"

# governance/policy-as-code/ -> governance/policy-as-code/, only when cloud
# == gcp (the example Rego policy is written against the gcp-cloud-run
# module's specific resource shapes) and --no-governance wasn't passed.
GOVERNANCE_SRC = "governance/policy-as-code"
GOVERNANCE_DST = "governance/policy-as-code"


def slugify(raw: str) -> str:
    slug = raw.strip().lower()
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"[^a-z0-9-]", "", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug or "app"


def case_variants(kebab: str) -> dict:
    pascal = "".join(part.capitalize() for part in kebab.split("-"))
    title = " ".join(part.capitalize() for part in kebab.split("-"))
    return {
        "kebab": kebab,
        "pascal": pascal,
        "title": title,
        "kebab_staging": f"{kebab}-staging",
        "kebab_production": f"{kebab}-production",
    }


def substitute_placeholders(text: str, variants: dict) -> str:
    for placeholder, key in PLACEHOLDER_REPLACEMENTS:
        text = text.replace(placeholder, variants[key])
    return text


def reverse_substitute_placeholders(text: str, variants: dict) -> str:
    """Inverse of substitute_placeholders — turns a scaffolded file back into
    its kit-template form, so it can be diffed against the kit's own source
    (which is still written with `your-app`/`YourApp`/"Your App").
    Longest-value-first so e.g. `{kebab}-staging` doesn't get partially
    eaten by a prior `{kebab}` -> `your-app` pass.
    """
    pairs = sorted(
        ((variants[key], placeholder) for placeholder, key in PLACEHOLDER_REPLACEMENTS),
        key=lambda pair: len(pair[0]),
        reverse=True,
    )
    for value, placeholder in pairs:
        if value:
            text = text.replace(value, placeholder)
    return text


def kit_commit_sha(kit_root: Path = KIT_ROOT) -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=kit_root,
            capture_output=True, text=True, timeout=5,
        )
        if out.returncode == 0:
            return out.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return "unknown (not a git checkout, or git unavailable)"


def git_show(kit_root: Path, sha: str, relative_path: str):
    """Return the file's content at `sha` in the kit repo, or None if it
    didn't exist at that point (new file, renamed, or invalid sha)."""
    try:
        out = subprocess.run(
            ["git", "show", f"{sha}:{relative_path}"], cwd=kit_root,
            capture_output=True, text=True, timeout=10,
        )
        if out.returncode == 0:
            return out.stdout
    except (OSError, subprocess.SubprocessError):
        pass
    return None
