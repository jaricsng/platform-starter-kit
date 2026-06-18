# Feature flags — decoupling deploy from release

The confidence lever this unlocks: **deploying code and releasing a feature
become two separate decisions.** You ship code dark (flag off), turn it on
for 1% / internal users / one region, watch the SLOs, then ramp — and if
anything's wrong you flip the flag back, instantly, with no redeploy and no
rollback. It's the single biggest reason a team can deploy to production
many times a day without fear.

This is a **pattern doc**, not a copied asset — flag evaluation lives in
your application code, which this kit deliberately doesn't contain. The
recommendation below keeps you vendor-neutral.

## Use OpenFeature (the OTel of feature flags)

[OpenFeature](https://openfeature.dev) is a CNCF vendor-neutral SDK: you
write against one API, and swap the *provider* behind it (a hosted service
like LaunchDarkly/Flagsmith/Statsig, the OSS [flagd](https://flagd.dev), or
a trivial env-var provider) without touching call sites — exactly the same
decoupling `OTEL_EXPORTER_OTLP_ENDPOINT` gives you for traces. Start with a
local/static provider; graduate to a managed one when you need targeting
rules and audit logs, with no code churn.

```python
# Illustrative — Python, OpenFeature SDK. The call site never changes when
# you swap providers; only the set_provider() line does.
from openfeature import api

client = api.get_client()

if client.get_boolean_value("new-checkout-flow", default=False):
    return new_checkout()
return legacy_checkout()
```

## How it fits the lifecycle

- **Deploy** (`ci-cd/github-actions/publish.yml`): keep promoting one image
  staging → prod. New code ships behind a default-off flag, so a deploy is
  inert until you choose to release.
- **Operate** ([`operations/runbooks/`](../operations/runbooks/)): the
  rollback runbook's first question is "can we flag this off?" — because
  that's faster and safer than a redeploy. A flag is a kill switch.
- **Release**: ramp 1% → 10% → 100%, watching the error-budget burn rate
  (`operations/SLOs.md`). A canary in software, without needing
  canary *infrastructure*.

## Keep it disciplined

- **Default off**, and make the default safe — an unreachable flag service
  must fall back to current behaviour, never to the new untested path.
- **Flags are temporary.** A flag that's been 100% for a month is tech debt
  — remove it and the dead branch. Track removal like any other task.
- **Don't put secrets or kill-critical logic in flags** without testing the
  provider-down path. The flag system becomes a production dependency;
  treat it like one.

## Enterprise step-up

See [`docs/ENTERPRISE-TOOLING.md`](ENTERPRISE-TOOLING.md). The OpenFeature
call sites stay identical; you're swapping the provider for one with
percentage targeting, user segments, audit trails, and approval workflows
(LaunchDarkly, Flagsmith, Unleash, Statsig).
