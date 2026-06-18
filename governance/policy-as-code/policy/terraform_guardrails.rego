package main

import rego.v1

# Example Conftest/OPA guardrails for iac-terraform/gcp-cloud-run's plan
# output. These check real config mistakes the module's variables make
# easy to hit (see variables.tf's defaults), not generic "best practice"
# noise. Adapt or replace the resource types/fields if you swap clouds —
# see docs/TECH-STACK-SWAP-GUIDE.md's IaC section.

# Deny: production Cloud SQL left on the staging-sized default db_tier.
# variables.tf defaults db_tier to "db-f1-micro" ("staging" in its own
# description) — easy to forget to override in terraform.tfvars.
deny contains msg if {
	rc := input.resource_changes[_]
	rc.type == "google_sql_database_instance"
	settings := rc.change.after.settings[_]
	settings.user_labels.environment == "production"
	settings.tier == "db-f1-micro"
	msg := sprintf(
		"%s: db_tier is db-f1-micro in production — override db_tier in terraform.tfvars (db-f1-micro is the staging default and undersized for production load)",
		[rc.address],
	)
}

# Deny: production Cloud Run scaled to zero. variables.tf defaults
# min_instances to 0 ("staging" in its own description) — fine for
# staging, causes cold-start latency spikes if left as-is in production.
deny contains msg if {
	rc := input.resource_changes[_]
	rc.type == "google_cloud_run_v2_service"
	rc.change.after.labels.environment == "production"
	template := rc.change.after.template[_]
	scaling := template.scaling[_]
	scaling.min_instance_count == 0
	msg := sprintf(
		"%s: min_instances is 0 (scale-to-zero) in production — set min_instances >= 1 to avoid cold-start latency on the first request after idle",
		[rc.address],
	)
}

# Warn (non-blocking): public Cloud Run invoker access. main.tf grants
# this intentionally (the app handles its own JWT auth) — flagged so
# anyone copying the pattern for a different service consciously confirms
# the same is true there, not silently inheriting public ingress.
warn contains msg if {
	rc := input.resource_changes[_]
	rc.type == "google_cloud_run_v2_service_iam_member"
	rc.change.after.member == "allUsers"
	msg := sprintf(
		"%s: grants roles/run.invoker to allUsers — main.tf's comment says this app handles its own JWT auth; confirm that's still true before reusing this pattern for a different service",
		[rc.address],
	)
}
