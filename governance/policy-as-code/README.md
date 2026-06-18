# Policy as code (OSS baseline)

`docs/ENTERPRISE-TOOLING.md` says, for Terraform Cloud/Spacelift/env0:
"configure policy-as-code (Sentinel for TFC, OPA for others) for
guardrails like 'no public IP' — this is the actual enterprise
value-add." This folder is that guardrail layer's free/OSS starting
point: [Conftest](https://www.conftest.dev/) running [Open Policy
Agent](https://www.openpolicyagent.org/) (Rego) rules against a
`terraform plan`'s JSON output. The enterprise tools above don't replace
this — they host/manage it centrally and add an approval workflow; the
Rego policies themselves port over largely unchanged.

`policy/terraform_guardrails.rego` checks two real config mistakes
`iac-terraform/gcp-cloud-run/variables.tf`'s defaults make easy to hit
(forgetting to override a staging-sized default in production), plus one
non-blocking `warn` flagging the module's intentional public-ingress
choice so anyone reusing the pattern consciously confirms it still
applies. It is an example tied to this module's specific resource
shapes — adapt the resource types/fields if you change the Terraform
module or swap clouds (see
[`docs/TECH-STACK-SWAP-GUIDE.md`](../../docs/TECH-STACK-SWAP-GUIDE.md)).

## Run it locally

```bash
brew install conftest   # or see https://www.conftest.dev/install/

cd iac-terraform/gcp-cloud-run
terraform plan -var-file=terraform.tfvars -out=plan.tfplan
terraform show -json plan.tfplan > plan.json

conftest test --policy ../../governance/policy-as-code/policy plan.json
```

## Try it without real cloud credentials

`governance/policy-as-code/examples/passing-plan.json` and
`failing-plan.json` are hand-written plan-JSON fixtures (no `terraform`
or GCP credentials needed) that exercise the same policy:

```bash
cd governance/policy-as-code
conftest test --policy policy examples/passing-plan.json   # exit 0, 1 warning
conftest test --policy policy examples/failing-plan.json   # exit 1, 2 failures
```

## Wiring into CI

`ci-cd/github-actions/ci.yml`'s `terraform-plan` job runs this gate
**by default, in report mode**: the `Conftest policy-as-code gate (report
mode)` step executes after `terraform plan`, prints any violations, but
carries `continue-on-error: true` so it doesn't block the PR — same
posture as the `tfsec` step above it. The step no-ops gracefully if the
`governance/policy-as-code/policy` folder isn't present.

**To hard-gate** (block a PR when a policy fails), once you've adapted the
rules to your own module: remove the `continue-on-error: true` line from
that step. That one line is the difference between "policy is visible" and
"policy is enforced" — flip it when you trust your rules.

## Writing your own rules

A Rego rule is a `deny` (blocking) or `warn` (non-blocking, still
visible) that matches against `input.resource_changes[]` — the same
array `terraform show -json` produces for every resource the plan would
create, update, or destroy. Conftest's own
[Terraform tutorial](https://www.conftest.dev/examples/) covers the
`resource_changes[].change.after` shape this policy reads from `rc` in
more detail than is worth duplicating here.
