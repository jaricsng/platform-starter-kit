#!/usr/bin/env python3
"""Automated pre-adoption readiness check — the checklist in
docs/ARCHITECTURE-FIT.md, run as a script instead of read-and-self-assess.

Inspects a target repo (default: current directory) for the signals listed
in that doc's "Pre-adoption checklist" table and prints a pass/fail report,
so an adopter — or this kit's own scaffold.py right after generating a new
repo — can confirm fit before wiring in CI, observability, or security
gates rather than discovering a gap mid-adoption.

Usage:
    python3 tools/doctor.py [path]   # defaults to the current directory

Exit code: 0 if no FAIL findings, 1 otherwise (CI-usable).
"""
import re
import subprocess
import sys
from pathlib import Path

SOURCE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".java", ".kt", ".cs",
}
MAX_FILES_TO_SCAN = 2000  # guard against scanning a huge unrelated tree

SECRET_PATTERNS = re.compile(
    r"AKIA[0-9A-Z]{16}|ghp_[a-zA-Z0-9]{36,}|sk-[a-zA-Z0-9]{32,}"
)

PASS, WARN, FAIL, INFO, SKIP = "PASS", "WARN", "FAIL", "INFO", "SKIP"
ICONS = {PASS: "✅", WARN: "⚠️ ", FAIL: "❌", INFO: "ℹ️ ", SKIP: "⏭️ "}

# Exclude this script's own location (and its scaffold.py sibling, if a
# copy was scaffolded alongside it) from source scans — otherwise this
# file's own docstrings/regexes ("/health", "opentelemetry", ...) produce
# false-positive PASSes when doctor.py is run against a repo that contains
# nothing but itself.
_SELF_PATH = Path(__file__).resolve()
_SELF_EXCLUDED = {_SELF_PATH, _SELF_PATH.parent / "scaffold.py"}


def iter_source_files(root: Path):
    count = 0
    for path in root.rglob("*"):
        if count >= MAX_FILES_TO_SCAN:
            return
        parts = set(path.parts)
        # Skip VCS/build noise, and skip this kit's own non-application
        # infrastructure directories — their scripts/docs *reference*
        # /health, OTel, etc. (because they test or instrument an app),
        # which would otherwise read as application code that has them.
        if parts & {
            ".git", "node_modules", ".venv", "__pycache__", "vendor",
            "target", "obj", "bin", ".terraform",
            "load-testing", "security", "observability", "iac-terraform",
            "tools", ".claude", ".github",
        }:
            continue
        if path.is_file() and path.suffix in SOURCE_EXTENSIONS and path.resolve() not in _SELF_EXCLUDED:
            count += 1
            yield path


def grep_files(root: Path, pattern: re.Pattern, paths=None):
    """Return the first matching (path, line) or None."""
    files = paths if paths is not None else iter_source_files(root)
    for path in files:
        try:
            text = path.read_text(errors="ignore")
        except OSError:
            continue
        if pattern.search(text):
            return path
    return None


def git_tracked_files(root: Path):
    try:
        out = subprocess.run(
            ["git", "ls-files"], cwd=root, capture_output=True, text=True, timeout=10
        )
        if out.returncode == 0:
            return [root / line for line in out.stdout.splitlines() if line]
    except (OSError, subprocess.SubprocessError):
        pass
    return None


def check_containerized(root: Path):
    dockerfiles = list(root.rglob("Dockerfile")) + list(root.rglob("dockerfile"))
    dockerfiles = [d for d in dockerfiles if ".git" not in d.parts][:1]
    compose = any((root / f"docker-compose.{ext}").exists() for ext in ("yml", "yaml"))
    if dockerfiles or compose:
        return PASS, "Dockerfile or docker-compose.yml found"
    return FAIL, "No Dockerfile/docker-compose.yml found — containerize before adopting ci-cd/, observability/, or any deploy job (see ARCHITECTURE-FIT.md)"


def check_health_endpoints(root: Path):
    pattern = re.compile(r"/health")
    ready_pattern = re.compile(r"/ready")
    health = grep_files(root, pattern)
    ready = grep_files(root, ready_pattern)
    if health and ready:
        return PASS, f"/health and /ready both referenced (e.g. {health.relative_to(root)})"
    if health or ready:
        return WARN, "Only one of /health or /ready found — both are expected by ci.yml's smoke jobs and every deploy job's post-deploy check"
    return FAIL, "No /health or /ready endpoint found — add both before wiring CI smoke tests or observability (see dotnet/ServiceDefaults/Extensions.cs or examples/minimal-service/telemetry.py for reference shapes)"


def check_otel(root: Path):
    pattern = re.compile(r"opentelemetry|OpenTelemetry|go\.opentelemetry\.io", re.IGNORECASE)
    manifest_names = (
        "requirements.txt", "pyproject.toml", "package.json", "go.mod",
        "go.sum", "pom.xml", "build.gradle", "*.csproj",
    )
    manifests = []
    for name in manifest_names:
        manifests.extend(root.rglob(name))
    manifests = [m for m in manifests if ".git" not in m.parts][:50]
    hit = grep_files(root, pattern, paths=manifests) or grep_files(root, pattern)
    if hit:
        return PASS, f"OpenTelemetry reference found (e.g. {hit.relative_to(root)})"
    return WARN, "No OpenTelemetry SDK reference found — observability/ will show empty dashboards (silence, not an error) until instrumented"


def check_secrets_hygiene(root: Path):
    tracked = git_tracked_files(root)
    if tracked is None:
        return SKIP, "Not a git repo (or git unavailable) — could not check tracked files"
    env_tracked = [f for f in tracked if f.name in (".env", ".env.local", ".env.production")]
    if env_tracked:
        return FAIL, f"{env_tracked[0].relative_to(root)} is tracked in git — rotate any real secrets and remove it from version control before enabling the pre-commit secret-detection hook"
    hit = grep_files(root, SECRET_PATTERNS, paths=[f for f in tracked if f.suffix in SOURCE_EXTENSIONS | {".env", ".yml", ".yaml", ".json"}][:500])
    if hit:
        return FAIL, f"Possible committed credential pattern in {hit.relative_to(root)} — rotate it and scrub git history before adopting the security/ scripts or pre-commit baseline"
    return PASS, "No tracked .env file or obvious committed-secret pattern found"


def check_kubernetes(root: Path):
    if (root / "Chart.yaml").exists() or list(root.rglob("Chart.yaml")):
        return WARN, "Helm Chart.yaml found — this kit's deploy jobs/Terraform target serverless-container platforms (Azure Container Apps/ECS/Cloud Run), not Kubernetes. See ARCHITECTURE-FIT.md's Kubernetes row before adopting ci-cd/github-actions/publish.yml or iac-terraform/"
    k8s_dirs = [d for d in (root / "k8s", root / "kubernetes") if d.is_dir()]
    if k8s_dirs:
        return WARN, f"{k8s_dirs[0].relative_to(root)}/ found — same Kubernetes caveat as above"
    return PASS, "No Helm/Kubernetes manifests detected"


def check_tests(root: Path):
    test_signals = (
        list(root.rglob("test_*.py")) + list(root.rglob("*_test.py"))
        + list(root.rglob("*.test.js")) + list(root.rglob("*.test.ts"))
        + list(root.rglob("*_test.go")) + [d for d in (root / "tests", root / "test") if d.is_dir()]
    )
    test_signals = [s for s in test_signals if ".git" not in s.parts]
    if test_signals:
        return PASS, f"Test files found (e.g. {test_signals[0].relative_to(root)})"
    return FAIL, "No test files found — ci.yml's backend/frontend jobs assume pytest/npm test exist and will fail the build; add at least one test before copying ci.yml (see TECH-STACK-SWAP-GUIDE.md)"


def check_database(root: Path):
    manifest_names = ("requirements.txt", "pyproject.toml", "package.json", "go.mod", "pom.xml")
    manifests = []
    for name in manifest_names:
        manifests.extend(root.rglob(name))
    manifests = [m for m in manifests if ".git" not in m.parts][:50]
    pg_pattern = re.compile(r"asyncpg|psycopg|pg8000|postgres", re.IGNORECASE)
    nonrel_pattern = re.compile(r"pymongo|mongoose|dynamodb|redis(?!.*cache)", re.IGNORECASE)
    if grep_files(root, pg_pattern, paths=manifests):
        return INFO, "Postgres client library detected — matches this kit's default CI service container and check-db.md"
    if grep_files(root, nonrel_pattern, paths=manifests):
        return WARN, "Non-relational datastore client detected — ci.yml's Postgres CI service container and claude-commands/check-db.md assume a relational/SQLAlchemy stack and need adapting (see TECH-STACK-SWAP-GUIDE.md's database-swap row)"
    return SKIP, "No recognized database client library detected — check manually if this service has a database"


def check_gitignore_secrets(root: Path):
    gitignore = root / ".gitignore"
    if not gitignore.exists():
        return FAIL, "No .gitignore — a committed .env would leak secrets; copy this kit's root .gitignore (it ignores .env/tfstate/tfvars)"
    text = gitignore.read_text(errors="ignore")
    env_ignored = any(
        line.strip() in (".env", "*.env", ".env*") or line.strip().startswith(".env")
        for line in text.splitlines()
    )
    if not env_ignored:
        return FAIL, ".gitignore exists but doesn't ignore .env — add a `.env` line before creating one from .env.example"
    if not (root / ".secrets.baseline").exists():
        return WARN, ".env is gitignored (good), but no .secrets.baseline — run `detect-secrets scan > .secrets.baseline` (or `make setup`) so the pre-commit detect-secrets hook works"
    return PASS, ".env is gitignored and a .secrets.baseline is present"


def check_catalog_governance(root: Path):
    catalog = root / "catalog-info.yaml"
    if not catalog.exists():
        return SKIP, "No catalog-info.yaml found — run tools/scaffold.py, or copy this kit's own root catalog-info.yaml, if you use a Backstage-style catalog"
    text = catalog.read_text(errors="ignore")
    match = re.search(r"^\s*owner:\s*(\S+)", text, re.MULTILINE)
    if not match:
        return WARN, "catalog-info.yaml has no owner: field — the catalog can't attribute this service to a team without one"
    owner = match.group(1).strip("\"'")
    if owner.startswith("TODO"):
        return WARN, f"catalog-info.yaml's owner is still the placeholder '{owner}' — resolve it to your actual Backstage group/team reference before this service ships to production"
    return PASS, f"catalog-info.yaml owner resolved to '{owner}'"


CHECKS = [
    ("Containerized", check_containerized),
    ("Health/readiness endpoints", check_health_endpoints),
    ("OpenTelemetry instrumentation", check_otel),
    ("Secrets hygiene", check_secrets_hygiene),
    ("Kubernetes mismatch", check_kubernetes),
    ("Automated tests present", check_tests),
    ("Database engine", check_database),
    ("Gitignore / secrets baseline", check_gitignore_secrets),
    ("Catalog ownership", check_catalog_governance),
]


def main():
    target = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()
    if not target.is_dir():
        print(f"Not a directory: {target}", file=sys.stderr)
        return 2

    print()
    print(f"Platform Starter Kit — readiness check: {target}")
    print("=" * 65)

    fail_count = 0
    for name, fn in CHECKS:
        status, message = fn(target)
        if status == FAIL:
            fail_count += 1
        print(f"{ICONS[status]} {name:<32} {message}")

    print("=" * 65)
    if fail_count:
        print(f"{ICONS[FAIL]} {fail_count} check(s) failed — see docs/ARCHITECTURE-FIT.md for what to fix first.")
    else:
        print(f"{ICONS[PASS]} No blocking gaps found. Review WARN/INFO lines, then continue with docs/GETTING-STARTED.md.")
    print()
    return 1 if fail_count else 0


if __name__ == "__main__":
    sys.exit(main())
