# Runbook: Rollback

**When to use:** a deploy is live and causing errors (5xx spike, SLO burn,
broken feature) and the fastest safe action is to get back to the last
known-good version.

> **Decide first: roll back, or flag off?** If the bad behaviour is behind
> a feature flag (see [`docs/FEATURE-FLAGS.md`](../../docs/FEATURE-FLAGS.md)),
> turning the flag off is faster and lower-risk than a redeploy — no new
> rollout, no image change. Roll back when the problem is in the deploy
> itself (a bad build, a config/infra change, a migration), not a flagged
> code path.

## Prerequisites

This kit's `ci-cd/github-actions/publish.yml` tags every image with the
commit SHA (`sha-<short>`) and promotes the *same* image staging → prod.
Rollback is therefore "re-deploy the previous SHA" — no rebuild needed.

1. Find the last known-good SHA: GitHub → Actions → the last green
   `publish` run before the bad one, or `git log --oneline` on `main`.
2. Confirm a database migration did **not** ship with the bad deploy
   (`git show <bad-sha> --stat` for files under your migrations dir). If
   one did, **stop** — see "If a migration shipped" below before rolling
   back.

## Roll back (per deploy target)

These mirror the deploy jobs in `publish.yml`. Replace placeholders with
your real names.

**Azure Container Apps** (the .NET Aspire deploy path, `azd`)
```bash
az containerapp revision list -n <app> -g <rg> -o table
az containerapp ingress traffic set -n <app> -g <rg> --revision-weight <good-revision>=100
```

**GCP Cloud Run** (matches `iac-terraform/gcp-cloud-run`)
```bash
gcloud run services update-traffic <service> --to-revisions=<good-revision>=100 --region=<region>
# or re-apply Terraform pinned to the good image:
#   terraform apply -var="image_tag=sha-<good>"
```

**AWS ECS Fargate**
```bash
aws ecs update-service --cluster <cluster> --service <svc> \
  --task-definition <family>:<good-revision> --force-new-deployment
```

## After rolling back

1. Confirm recovery: `/health` + `/ready` green, 5xx rate back to baseline,
   the `ErrorBudgetBurnRate*` alerts (see `observability/recording_rules.yml`)
   resolve in Alertmanager.
2. Open an incident if you haven't — see
   [`incident-response.md`](incident-response.md).
3. The bad SHA is still on `main`. Revert it (`git revert <bad-sha>`) or
   roll forward with a fix, so the next deploy doesn't re-ship it.

## If a migration shipped with the bad deploy

Rolling the *app* back while the *schema* moved forward can break the
old version. This is exactly what the expand/contract pattern in
[`docs/DATABASE-MIGRATIONS.md`](../../docs/DATABASE-MIGRATIONS.md) prevents —
if it was followed, the previous app version tolerates the new schema and a
plain rollback is safe. If it was **not** followed, do not blind-rollback:
assess whether the migration is reversible, and prefer rolling *forward*
with a fix. This is the scenario the `migration-safety` CI gate exists to
keep you out of.
