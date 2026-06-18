# Operations

The Operate/Monitor end of the lifecycle: how the service is run once it's
live, and what to do when it isn't healthy. The `observability/` folder
gives you the *signals* (metrics, traces, dashboards, alerts); this folder
gives you the *human procedures* that turn a signal into an action.

| File | What it's for |
|---|---|
| [`SLOs.md`](SLOs.md) | The reliability targets behind `observability/recording_rules.yml`, and how error-budget burn gates risky deploys |
| [`runbooks/rollback.md`](runbooks/rollback.md) | Get back to the last known-good version, per deploy target |
| [`runbooks/incident-response.md`](runbooks/incident-response.md) | The sequence to follow when an alert fires |
| [`runbooks/postmortem-template.md`](runbooks/postmortem-template.md) | Blameless write-up, copied per incident |

These are deliberately short and copy-to-adapt. The platform-engineering
point: a developer shipping a service shouldn't have to invent an incident
process or a rollback procedure under pressure — the paved road comes with
one. Pair this with `docs/FEATURE-FLAGS.md` (flag off is often faster than
roll back) and `docs/DATABASE-MIGRATIONS.md` (the migration-safety gate
keeps you out of the worst rollback scenario).
