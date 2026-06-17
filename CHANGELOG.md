# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Versioning policy: **major** = breaking layout change, **minor** = new
capability folder added, **patch** = doc/template fixes with no structural
change.

## [Unreleased]

## [1.0.0]

### Added

- Initial extraction of reusable DevSecOps platform assets from the
  `task-manager` lab repo, organized by capability:
  - `claude-skills/` — 19 Claude Code skill prompts
  - `dotnet/` — Aspire `ServiceDefaults` + an `AppHost` template
  - `ci-cd/` — GitHub Actions CI/CD pipeline shape + pre-commit security baseline
  - `observability/` — Jaeger + Prometheus + Grafana Docker Compose overlay
  - `load-testing/` — k6 and Locust scenarios
  - `iac-terraform/gcp-cloud-run/` — parameterized Terraform module
  - `security/` — OWASP manual pen-test script and ZAP scan wrapper
  - `examples/minimal-service/` — a worked example proving the pieces work together
  - `.github/workflows/validate-kit.yml` — the kit's own validation CI
