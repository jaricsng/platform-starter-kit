---
name: Asset / capability request
about: Propose a new capability folder or an addition to an existing one
title: "[asset] "
labels: enhancement
---

**Capability**
Which lifecycle stage does this serve (Plan, Code, Build/Release, Test,
Security Gate, Deploy, Operate/Monitor — see the capability map in
`README.md`), and is this a new folder or an addition to an existing one?

**What it would contain**

**Reusability**
Per `docs/ASSET-CATALOG.md`'s convention: does this work standalone with
no dependency on application source code or another capability folder?

**Versioning impact**
New capability folder = minor version bump; addition to an existing one
without a layout change = patch (see `CHANGELOG.md`'s versioning policy).
