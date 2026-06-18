# Service Level Objectives

SLOs make "is the service healthy?" a number instead of a vibe, and give
the deploy pipeline an objective stop signal (error-budget burn). These
are wired to the recording rules and alerts the kit already ships — this
doc is the human-readable contract behind them.

## The SLOs

Defaults below match `observability/recording_rules.yml`. **Set the targets
to what your users actually need** — an SLO copied from a template and never
agreed with stakeholders is just a number.

| SLI (what we measure) | SLO (target) | Recording rule | Alert |
|---|---|---|---|
| Availability — non-5xx ratio | ≥ 99% (30-day) | `app:request_availability:rate5m` | `ErrorBudgetBurnRate{Critical,High}` |
| Latency — P95 request duration | < 500 ms | `app:request_p95_seconds:rate5m` | `LatencySLOBreach` |
| Reachability — `/ready` probe | ≥ 99.9% | `job:readiness_probe_success:avg5m` | `ServiceUnreachable` |

## Error budget

A 99% availability SLO means a **1% error budget**: over 30 days, up to 1%
of requests may fail before you've breached. The budget is what makes the
"ship fast vs. stay stable" trade-off objective:

- **Budget remaining** → ship features; take reasonable risks.
- **Budget exhausted / burning fast** → freeze risky changes, spend effort
  on reliability until it recovers.

The kit alerts on **burn rate**, not raw error count, so a brief blip
doesn't page but a sustained burn does:

- `app:error_budget_burn_rate:1h > 14.4` → budget gone in < 2h → **page**
  (`ErrorBudgetBurnRateCritical`, routed to PagerDuty in `alertmanager.yml`).
- `> 6` → gone in < 6h → **warn** (`ErrorBudgetBurnRateHigh`, Slack).

(14.4 is the standard multi-window burn-rate threshold: at 14.4× the
sustainable rate, a 30-day budget lasts ~2 hours.)

## Making them real

1. **Agree the targets** with whoever owns the user experience — these are
   a product decision, not an SRE one.
2. **Tie deploys to the budget.** When `ErrorBudgetBurnRateHigh` is
   firing, that's the signal to hold non-essential releases — a policy your
   team enforces, optionally backed by a deploy check.
3. **Review monthly.** If you never burn budget, the SLO may be too loose
   (you're over-investing in reliability); if you always breach, it's too
   tight or the service genuinely needs work.

See [`runbooks/incident-response.md`](runbooks/incident-response.md) for what
happens when an SLO alert fires.
