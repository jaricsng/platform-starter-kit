# Runbook: Incident Response

A lightweight, copy-and-adapt incident process. The goal is a predictable
sequence under pressure, not bureaucracy — trim or expand to your org.

## Severity

| Sev | Meaning | Example | Response |
|---|---|---|---|
| **SEV1** | Service down / data at risk | All requests 5xx; `ServiceUnreachable` firing | Page on-call immediately, all hands |
| **SEV2** | Major degradation, no workaround | P95 latency 5× SLO; `ErrorBudgetBurnRateCritical` | Page on-call |
| **SEV3** | Minor / partial, workaround exists | One non-critical endpoint failing | Next business hours |

Alert → severity mapping lives in `observability/recording_rules.yml`
(`severity:` labels) and routes via `observability/alertmanager.yml`.

## The loop

1. **Acknowledge** the page so others know it's owned.
2. **Declare** — open an incident channel/doc, state the SEV and a one-line
   summary. Assign an **Incident Commander** (coordinates; doesn't
   necessarily fix).
3. **Mitigate before diagnose.** Restore service first:
   - Flag off the suspect feature ([`../../docs/FEATURE-FLAGS.md`](../../docs/FEATURE-FLAGS.md)), or
   - [Roll back](rollback.md) to the last known-good SHA.
   Root cause can wait until users are unblocked.
4. **Communicate** on a cadence (e.g. every 30 min for SEV1/2) even if the
   update is "still investigating."
5. **Resolve** — confirm via `/health`, `/ready`, the dashboards
   (`observability/grafana`), and the alerts clearing in Alertmanager.
6. **Postmortem** — within a few days, blameless, using
   [`postmortem-template.md`](postmortem-template.md).

## Where to look

- **Dashboards:** Grafana (`make obs-up`, then `:3000`) — RED panels.
- **Traces:** Jaeger (`:16686`) — find the slow/failing span.
- **What just changed:** `git log --oneline -10 origin/main`, and the most
  recent `publish` run in GitHub Actions. Most incidents correlate with a
  recent deploy — check that first.
- **Active alerts:** Alertmanager (`:9093`).
