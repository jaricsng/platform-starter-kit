**What changed and why**

**Affected capability folder(s)**

**Versioning** (see `CHANGELOG.md`'s policy — major/minor/patch)
- [ ] `CHANGELOG.md` updated under `[Unreleased]`
- [ ] If a placeholder was introduced, `docs/TODO.md` updated
- [ ] If reusability/provenance changed, `docs/ASSET-CATALOG.md` updated

**Validation**
- [ ] `validate-kit.yml` checks pass (actionlint, terraform validate,
      compose config, minimal-service smoke test, pre-commit validate —
      see `CLAUDE.md` for how to run these locally)
- [ ] No new dependency on application source code or another capability
      folder (each asset must still work standalone)
