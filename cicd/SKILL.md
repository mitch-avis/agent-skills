---
name: cicd
description: >-
  Use before writing or changing CI/CD pipeline files (.github/workflows/*.yml, .gitlab-ci.yml,
  Jenkinsfile, ArgoCD Applications) or when a pipeline fails or runs slowly, including image
  build-and-push, monorepo path filters, and multi-environment deploys. Covers pipeline
  architecture, security gates (SAST, SCA, container scanning, artifact signing), caching and
  parallelization, deployment strategies, ArgoCD GitOps sync, and common anti-patterns.
---

# CI/CD Pipelines

Design secure, efficient, and maintainable CI/CD pipelines across GitHub Actions, GitLab CI,
Jenkins, and ArgoCD.

## Core Principles

1. **Fail fast** — order stages: lint → security → test → build → deploy. Catch issues before
   expensive work runs.
2. **Security by default** — embed SAST, SCA, and container scanning. Use OIDC over static secrets.
   Sign artifacts. Apply least-privilege permissions.
3. **Reproducible** — pin dependency versions, use lockfiles, avoid external state. Identical inputs
   must produce identical outputs. Image tags and action versions in these examples were current
   in October 2026; look up the current release when you write a pipeline instead of copying them.
4. **Cache aggressively** — cache dependencies, build outputs, and Docker layers. Every saved minute
   compounds across all developers.
5. **Parallelize** — run independent jobs concurrently. Only serialize jobs with real data
   dependencies.
6. **Gate production** — require manual approval, health checks, and rollback plans before
   production deployments.

## Quick Start — GitHub Actions

Python with uv (versions come from `.python-version` and `uv.lock`):

```yaml
name: CI
on:
  push: { branches: [main] }
  pull_request: { branches: [main] }

permissions:
  contents: read

jobs:
  python:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - uses: astral-sh/setup-uv@v10
        with: { enable-cache: true }
      - run: uv sync --locked
      - run: .venv/bin/ruff format --check .
      - run: .venv/bin/ruff check .
      - run: .venv/bin/pyright
      - run: .venv/bin/ty check
      - run: .venv/bin/pytest
```

Rust on nightly (the toolchain comes from `rust-toolchain.toml`):

```yaml
  rust:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - uses: dtolnay/rust-toolchain@nightly
        with: { components: "rustfmt, clippy" }
      - uses: Swatinem/rust-cache@v2
      - uses: taiki-e/install-action@v2
        with: { tool: cargo-nextest }
      - run: cargo +nightly fmt --all --check
      - run: cargo +nightly clippy --workspace --all-features --all-targets -- -D warnings
      - run: cargo +nightly test --doc --workspace --all-features
      - run: cargo +nightly nextest run --workspace --all-features --all-targets
```

A Node.js lint/test/build pipeline is in
[references/github-actions.md](references/github-actions.md#nodejs-quick-start).

## Quick Start — GitLab CI

```yaml
image: node:24-alpine

stages:
  - lint
  - test
  - build
  - deploy

cache:
  key: ${CI_COMMIT_REF_SLUG}
  paths:
    - node_modules/
    - .npm/

lint:
  stage: lint
  script:
    - npm ci
    - npm run lint

test:
  stage: test
  script:
    - npm ci
    - npm test
  coverage: '/Lines\s*:\s*(\d+\.\d+)%/'
  artifacts:
    reports:
      coverage_report:
        coverage_format: cobertura
        path: coverage/cobertura-coverage.xml

build:
  stage: build
  script:
    - npm ci
    - npm run build
  artifacts:
    paths:
      - dist/
    expire_in: 1 hour
```

## Quick Start — ArgoCD GitOps

Declare desired state in Git. ArgoCD reconciles clusters automatically.

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: myapp
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/org/k8s-manifests.git
    targetRevision: main
    path: overlays/production
  destination:
    server: https://kubernetes.default.svc
    namespace: production
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
```

For ApplicationSets, RBAC, sync hooks, SSO, and CLI commands, read
[references/argocd-gitops.md](references/argocd-gitops.md).

## Security Essentials

Embed security at every stage. Block deployment on high/critical findings.

### Permissions

```yaml
# GitHub Actions — explicit minimal permissions
permissions:
  contents: read
  security-events: write
  id-token: write          # OIDC — no static cloud credentials

# GitLab CI — use protected variables and environments
variables:
  SECURE_ANALYZERS_PREFIX: registry.gitlab.com/security-products
```

### Pin Third-Party Actions to a Commit

A tag like `@v0.36.0` can be moved to point at different code. Pin actions from outside `actions/*`
and `github/*` to the full commit SHA, with the tag in a comment so updates stay readable
(Dependabot and Renovate keep both in sync):

```yaml
- uses: aquasecurity/trivy-action@ed142fd0673e97e23eac54620cfb913e5ce36c25  # v0.36.0
```

Resolve a tag to its commit with
`gh api repos/<owner>/<repo>/commits/<tag> --jq .sha`.

### Scanning Stages

| Scan Type | GitHub Actions | GitLab CI Template |
| --- | --- | --- |
| SAST | `semgrep/semgrep:1.179.0` container running `semgrep scan` | `Security/SAST.gitlab-ci.yml` |
| SCA        | `snyk/actions/node@v1.0.0`  | `Security/Dependency-Scanning.gitlab-ci.yml` |
| Containers | `aquasecurity/trivy-action` | `Security/Container-Scanning.gitlab-ci.yml`  |
| Secrets    | `gitleaks/gitleaks-action`  | `Security/Secret-Detection.gitlab-ci.yml`    |

### Supply Chain Integrity

```yaml
# Sign container images with Cosign (keyless via OIDC)
- name: Sign image
  run: cosign sign --yes ghcr.io/${{ github.repository }}@${{ steps.build.outputs.digest }}

# Generate SBOM
- uses: docker/build-push-action@v7
  with:
    provenance: true
    sbom: true
```

For complete security patterns, OWASP CI/CD Top 10 mapping, and SAST/DAST integration details, read
[references/security-gates.md](references/security-gates.md).

## Performance Patterns

### Dependency Caching

```yaml
# GitHub Actions
- uses: actions/cache@v6
  with:
    path: ~/.npm
    key: ${{ runner.os }}-npm-${{ hashFiles('**/package-lock.json') }}
    restore-keys: ${{ runner.os }}-npm-

# GitLab CI
cache:
  key: ${CI_COMMIT_REF_SLUG}
  paths: [node_modules/]
  policy: pull-push
```

### Docker Layer Caching

```yaml
# GitHub Actions — BuildKit GHA cache
- uses: docker/build-push-action@v7
  with:
    cache-from: type=gha
    cache-to: type=gha,mode=max

# GitLab CI — registry-based cache
build-docker:
  script:
    - >-
      docker build
      --cache-from $CI_REGISTRY_IMAGE:latest
      --tag $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA .
```

### Path-Filtered Triggers

Only run affected jobs on monorepos:

```yaml
# GitHub Actions
- uses: dorny/paths-filter@v4
  id: changes
  with:
    filters: |
      frontend: ['src/frontend/**']
      backend: ['src/backend/**']

# GitLab CI
frontend:
  rules:
    - changes: [src/frontend/**]
```

## Deployment Strategies

| Strategy | Mechanism | Rollback |
| --- | --- | --- |
| Rolling | Replace pods incrementally | `kubectl rollout undo` |
| Blue-green | Switch traffic between identical environments | Flip load balancer     |
| Canary     | Route % of traffic to new version             | Scale canary to 0      |
| GitOps     | ArgoCD syncs from Git state                   | Revert Git commit      |

### Multi-Environment Pattern

```yaml
# GitLab CI — extend a deploy template
.deploy:
  image: alpine/k8s:1.37.1
  script:
    - kubectl apply -f k8s/ -n $ENVIRONMENT
    - kubectl rollout status deployment/app -n $ENVIRONMENT --timeout=5m

deploy:staging:
  extends: .deploy
  variables: { ENVIRONMENT: staging }
  environment:
    name: staging
    url: https://staging.example.com

deploy:production:
  extends: .deploy
  variables: { ENVIRONMENT: production }
  environment:
    name: production
    url: https://app.example.com
  when: manual
  rules:
    - if: $CI_COMMIT_BRANCH == "main"
```

For advanced deployment patterns (Terraform pipelines, blue-green, canary), read
[references/deployment-strategies.md](references/deployment-strategies.md). For ArgoCD application
management, ApplicationSets, sync strategies, RBAC, and CLI commands, read
[references/argocd-gitops.md](references/argocd-gitops.md).

## Anti-Patterns

### Overly Permissive Permissions

```yaml
# BAD — inherits write permissions to everything
name: CI
on: [push]

# GOOD — explicit minimal permissions
permissions:
  contents: read
  pull-requests: write
```

### No Timeout

```yaml
# BAD — job can run indefinitely (default 360 min)
jobs:
  build:
    runs-on: ubuntu-latest

# GOOD — set reasonable timeouts
jobs:
  build:
    runs-on: ubuntu-latest
    timeout-minutes: 30
```

### Deploy Without Health Checks

```yaml
# BAD — deploy and hope
- run: kubectl apply -f deployment.yml

# GOOD — verify rollout and health
- run: kubectl apply -f deployment.yml
- run: kubectl rollout status deployment/app --timeout=5m
- run: curl -f https://app.example.com/health || exit 1
```

### Secrets in Fork PRs

```yaml
# BAD — secrets exposed to fork PRs
on: pull_request
jobs:
  deploy:
    steps:
      - run: deploy.sh
        env:
          AWS_SECRET: ${{ secrets.AWS_SECRET }}

# GOOD — restrict secrets to push events
jobs:
  deploy:
    if: github.event_name == 'push'
```

### Sequential Independent Jobs

```yaml
# BAD — lint waits for test, which waits for security
jobs:
  lint:
  test:
    needs: lint
  security:
    needs: test

# GOOD — independent jobs run in parallel
jobs:
  lint:
  test:
  security:
  build:
    needs: [lint, test, security]
```

## Pre-Implementation Checklist

- [ ] Define stages and job dependency graph
- [ ] Identify caching targets (deps, builds, Docker layers)
- [ ] Set explicit permissions (never default write-all)
- [ ] Pin action/image versions (SHA for Actions, tags for Docker)
- [ ] Add SAST, SCA, and container scanning
- [ ] Configure timeouts for every job
- [ ] Gate production with manual approval
- [ ] Add health checks after deployment
- [ ] Set up rollback mechanism
- [ ] Validate syntax (`actionlint`, `gitlab-ci-lint`)

## Reference Guides

| Topic | File | Load When |
| --- | --- | --- |
| GitHub Actions | [references/github-actions.md](references/github-actions.md) | Creating or modifying GitHub Actions workflows |
| GitLab CI             | [references/gitlab-ci.md](references/gitlab-ci.md)                         | Creating or modifying GitLab CI pipelines          |
| Jenkins               | [references/jenkins.md](references/jenkins.md)                             | Creating or modifying Jenkins pipelines            |
| Security Gates        | [references/security-gates.md](references/security-gates.md)               | Adding SAST, SCA, DAST, signing, OWASP mapping     |
| Deployment Strategies | [references/deployment-strategies.md](references/deployment-strategies.md) | Blue-green, canary, Terraform deployments          |
| ArgoCD GitOps         | [references/argocd-gitops.md](references/argocd-gitops.md)                 | ArgoCD apps, ApplicationSets, sync, RBAC, CLI      |

## Related Skills

- [docker](../docker/SKILL.md) — building and scanning container images in pipelines
- [kubernetes](../kubernetes/SKILL.md) — GitOps deploys and rollouts to clusters
- [helm](../helm/SKILL.md) — packaging and releasing chart-based applications
- [observability](../observability/SKILL.md) — pipeline telemetry, deploy markers, build metrics
- [shell-scripting](../shell-scripting/SKILL.md) — hardening shell steps inside pipeline jobs
