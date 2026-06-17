# minimal-service

A throwaway FastAPI app with one job: prove the extracted pieces of this kit
actually work together before you touch your own code. Run this first.

## Run it

From the **repo root** (not this directory):

```bash
docker compose --project-directory . \
  -f examples/minimal-service/docker-compose.yml \
  -f observability/docker-compose.observability.yml \
  --profile observability up --build
```

Why `--project-directory .` and why run from the root: Docker Compose
resolves every relative path (build `context:`, volume mounts) against a
single project directory, which otherwise defaults to the directory of the
*first* `-f` file. Forcing it to the repo root makes both this file's
`context: ./examples/minimal-service` and the observability overlay's
`./observability/prometheus.yml`-style volume mounts resolve correctly at
the same time. If you copy `observability/` into your own repo root instead
of running it from here, you won't need this flag — see
`observability/docker-compose.observability.yml`'s own usage comment.

## Check it worked

```bash
curl http://localhost:8000/health   # {"status": "ok"}
curl http://localhost:8000/ready    # {"status": "ready"}
curl -L http://localhost:8000/metrics  # Prometheus text format (mounted sub-app redirects to a trailing slash)
```

- **Jaeger** (http://localhost:16686) — select service `app`, you should see
  `health-check` / `readiness-check` spans from the curls above.
- **Prometheus** (http://localhost:9090/targets) — the `app` and `readiness`
  scrape targets should both show `UP`.
- **Grafana** (http://localhost:3000, admin/admin) — open the "Service
  Overview" dashboard; request-rate and latency panels should show data once
  you've hit `/health` a few times.

## Smoke-test it with k6

```bash
k6 run load-testing/k6/smoke.js -e BASE_URL=http://localhost:8000
```

This example only has `/health` and `/ready`, so most of `smoke.js`'s
project/task/comment checks will fail — that's expected here. It's wired up
in `.github/workflows/validate-kit.yml` only to confirm k6 itself runs
against a live container, not to pass every check.

## Tear down

```bash
docker compose --project-directory . \
  -f examples/minimal-service/docker-compose.yml \
  -f observability/docker-compose.observability.yml \
  --profile observability down -v
```
