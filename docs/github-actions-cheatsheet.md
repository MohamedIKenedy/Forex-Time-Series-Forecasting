# GitHub Actions — Fundamental Commands & Examples

This cheatsheet covers the core concepts, YAML fields, and runtime commands you will use frequently in GitHub Actions workflows.

## Workflow basics
- `on:` — triggers (e.g. `push`, `pull_request`, `workflow_dispatch`, `schedule`).
- `jobs:` — top-level blocks. Each job runs in its own runner (or container).
- `runs-on:` — runner OS, e.g. `ubuntu-latest`.
- `needs:` — makes a job wait for one or more other jobs.
- `if:` — conditional expression to run a job or step (uses `${{ }}` expressions).

Example header:
```yaml
name: CI
on: [push]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - run: echo "Hello"
```

## Steps: `uses` vs `run`
- `uses:` — reference a reusable action (e.g. `actions/checkout@v3`).
- `run:` — shell commands executed on the runner.
- `with:` — pass inputs to an action used with `uses:`.
- `env:` — set environment variables for a step.

```yaml
- name: Checkout
  uses: actions/checkout@v3

- name: Run tests
  run: pytest -q
  env:
    PYTHONPATH: .:api
```

## Common `actions/checkout@v3` options
- `fetch-depth`: `1` (default) for shallow clones. Use `0` for full history.
- `persist-credentials`: `true` (default). Set to `false` to avoid leaving the token in `.git/config`.
- `submodules`: `true` to fetch submodules.

## Contexts & Expressions
- Use `${{ }}` to evaluate expressions.
- Common contexts: `github`, `env`, `secrets`, `steps`, `needs`, `matrix`, `runner`.

Examples:
```yaml
if: github.ref == 'refs/heads/main'
run: echo "Event: ${{ github.event_name }}"
run: echo "Matrix os: ${{ matrix.os }}"
run: echo "Previous step output: ${{ steps.build.outputs.version }}"
```

## Passing data between steps and jobs
- Step outputs (preferred): write to the special file `$GITHUB_OUTPUT`.

Set a step output:
```bash
echo "version=1.2.3" >> $GITHUB_OUTPUT
```
Then reference in same job:
`${{ steps.<step_id>.outputs.version }}`

- Job outputs: set using `echo "name=value" >> $GITHUB_OUTPUT` inside a step and declare job outputs, then read from `needs.<job>.outputs.<name>` in downstream jobs.

> Note: the old `::set-output` command is deprecated; use `$GITHUB_OUTPUT`.

## Workflow commands (logging / masking / grouping)
- Mask a value in logs:
```bash
echo "::add-mask::${SECRET_VALUE}"
```
- Log warning / error:
```bash
echo "::warning::This is a warning"
echo "::error::This is an error"
```
- Group logs (folded blocks in UI):
```bash
echo "::group::Build"
do_build_steps
echo "::endgroup::"
```

## Artifacts and cache
- Upload artifact:
```yaml
- uses: actions/upload-artifact@v3
  with:
    name: my-artifact
    path: path/to/files
```
- Download artifact in another job:
```yaml
- uses: actions/download-artifact@v3
  with:
    name: my-artifact
```
- Cache dependencies (actions/cache):
```yaml
- uses: actions/cache@v4
  with:
    path: ~/.cache/pip
    key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}
    restore-keys: |
      ${{ runner.os }}-pip-
```

## Matrix builds
```yaml
strategy:
  matrix:
    python-version: [3.10, 3.11]
    os: [ubuntu-latest, windows-latest]
```

## Services (databases, message brokers)
```yaml
services:
  postgres:
    image: postgres:15
    env:
      POSTGRES_PASSWORD: example
    ports:
      - 5432:5432
```

## Useful action examples
- Login to Docker Hub:
```yaml
- uses: docker/login-action@v2
  with:
    username: ${{ secrets.DOCKER_HUB_USERNAME }}
    password: ${{ secrets.DOCKER_HUB_PASSWORD }}
```
- Build and push image:
```yaml
- uses: docker/build-push-action@v4
  with:
    context: ./api
    push: true
    tags: ${{ secrets.DOCKER_HUB_USERNAME }}/forex-api:latest
```
- Setup Terraform:
```yaml
- uses: hashicorp/setup-terraform@v2
  with:
    terraform_version: 1.6.0
```

## Secrets and security
- Store secrets under _Repository → Settings → Secrets and variables → Actions_.
- Do not echo secrets to logs. Use `${{ secrets.NAME }}` only where needed.
- Use `persist-credentials: false` for `checkout` when you don't need the GitHub token persisted.

## Environment & Protection
- Workflows can target `environments` (dev/staging/prod) and require approvals.
- Use `permissions:` block to restrict token scopes for jobs.

## Common troubleshooting tips
- Use `workflow_dispatch` to run a workflow manually for debugging.
- Set `fetch-depth: 0` on checkout if you need tags or full history.
- Inspect logs in Actions UI — expand grouped logs for details.

## Quick reference snippets
- Capture TF output to use in later steps:
```yaml
- name: Apply Terraform
  id: tf
  run: |
    terraform apply -auto-approve
    echo "public_ip=$(terraform output -raw public_ip)" >> $GITHUB_OUTPUT

- name: Use TF output
  run: ssh ubuntu@${{ steps.tf.outputs.public_ip }} "hostname"
```

---
File created in `docs/github-actions-cheatsheet.md` — expand or ask for examples tailored to your workflow.
