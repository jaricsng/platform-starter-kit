# Postmortem: <short incident title>

> Blameless. The goal is to fix the **system and process** that let this
> happen, never to assign individual fault. Copy this file per incident.

- **Date:** YYYY-MM-DD
- **Severity:** SEV_
- **Duration:** HH:MM (detection → resolution)
- **Authors:** @...
- **Status:** Draft | Reviewed

## Summary

Two or three sentences: what broke, who was affected, how it was resolved.

## Impact

- User-facing effect (error rate, latency, downtime, data).
- Scope: % of requests / users / which regions.
- Error budget consumed (see `observability/recording_rules.yml`'s
  `app:error_budget_burn_rate:1h`).

## Timeline (UTC)

| Time | Event |
|---|---|
| HH:MM | First bad deploy / triggering change |
| HH:MM | Alert fired (`<alertname>`) |
| HH:MM | Acknowledged |
| HH:MM | Mitigated (flag off / rolled back) |
| HH:MM | Resolved |

## Root cause

What actually caused it (the technical chain), and **why it wasn't caught
earlier** — which gate/test/review should have stopped it and didn't.

## What went well / what didn't

- Went well: ...
- Didn't: ...
- Got lucky: ... (things that could have been worse)

## Action items

Each item: concrete, owned, dated, and tracked as an issue. Prefer changes
that make the whole *class* of failure impossible over one-off fixes.

| Action | Owner | Due | Issue |
|---|---|---|---|
| e.g. add a CI gate / alert / test that would have caught this | @... | YYYY-MM-DD | #... |
