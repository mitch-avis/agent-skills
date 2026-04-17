# Helm Operations

## Command Reference

| Command | Purpose |
| ---- | ---- |
| `helm create <name>` | Scaffold a new chart |
| `helm install <release> <chart>` | Install a chart |
| `helm upgrade <release> <chart>` | Upgrade a release |
| `helm upgrade --install <release> <chart>` | Install or upgrade (idempotent) |
| `helm rollback <release> <rev>` | Rollback to a previous revision |
| `helm uninstall <release>` | Remove a release |
| `helm list` | List releases |
| `helm history <release>` | Show release history |
| `helm status <release>` | Show release status |
| `helm get values <release>` | Show user-supplied values |
| `helm get manifest <release>` | Show rendered manifests |
| `helm get all <release>` | Show all release info |
| `helm show values <chart>` | Show chart's default values |
| `helm show chart <chart>` | Show Chart.yaml metadata |
| `helm template <release> <chart>` | Render templates locally |
| `helm lint <chart>` | Validate chart syntax |
| `helm dependency update <chart>` | Download/update dependencies |
| `helm dependency build <chart>` | Rebuild charts/ from lock |
| `helm package <chart>` | Package chart into .tgz |
| `helm repo add <name> <url>` | Add a chart repository |
| `helm repo update` | Refresh repository index |
| `helm search repo <keyword>` | Search repos |
| `helm search hub <keyword>` | Search Artifact Hub |
| `helm env` | Show Helm environment info |

## OCI Registry Support

```bash
# Log in to registry
helm registry login ghcr.io -u $USER -p $TOKEN

# Push a packaged chart
helm push myapp-1.0.0.tgz oci://ghcr.io/myorg/charts

# Install directly from OCI
helm install myapp oci://ghcr.io/myorg/charts/myapp --version 1.0.0

# Pull chart from OCI
helm pull oci://ghcr.io/myorg/charts/myapp --version 1.0.0

# Show values from OCI chart
helm show values oci://ghcr.io/myorg/charts/myapp --version 1.0.0
```

## --set Syntax

```bash
# Scalar
--set image.tag=v2.0.0

# String (force quoting)
--set-string port="8080"

# Array element
--set ingress.hosts[0].host=example.com

# Comma in value (escape with \)
--set annotation="value\,with\,commas"

# Multiple values
--set replicas=3,image.tag=v2.0.0

# From file
--set-file config=./app.conf

# From JSON
--set-json 'resources={"requests":{"cpu":"100m"}}'
```

Prefer `-f values.yaml` over `--set` for anything non-trivial — files are versionable, reviewable,
and do not require shell escaping.

## Namespace Behavior

```bash
# Install into specific namespace (must exist)
helm install myapp ./myapp -n production

# Create namespace if missing
helm install myapp ./myapp -n production --create-namespace

# List releases in all namespaces
helm list -A
```

Always pass `-n <namespace>` explicitly — Helm defaults to the current kubeconfig context namespace,
which can vary between environments and CI runners.

## helm diff Plugin

Shows what an `upgrade` would change before applying:

```bash
# Install the plugin
helm plugin install https://github.com/databus23/helm-diff

# Preview changes (colored diff of rendered manifests)
helm diff upgrade myapp ./myapp -f values-prod.yaml

# Suppress unchanged resources
helm diff upgrade myapp ./myapp --suppress-secrets

# Compare against a specific revision
helm diff revision myapp 5 7
```

## helm-docs

Auto-generates documentation from chart metadata and values comments:

```bash
# Install
go install github.com/norwoodj/helm-docs/cmd/helm-docs@latest

# Generate README from values.yaml comments
helm-docs --chart-search-root ./charts

# Custom template
helm-docs --template-files README.md.gotmpl
```

Document values using `--` comments in `values.yaml`:

```yaml
# -- Number of replicas
# @default -- 3
replicaCount: 3

# -- Image configuration
image:
  # -- Container image repository
  repository: myregistry.io/myapp
  # -- Image pull policy
  pullPolicy: IfNotPresent
```

## helm secrets Plugin

Manage encrypted values files with SOPS, GPG, AWS KMS, or Azure Key Vault:

```bash
# Install the plugin
helm plugin install https://github.com/jkroepke/helm-secrets

# Encrypt a values file
helm secrets encrypt values-secret.yaml > values-secret.enc.yaml

# Decrypt (edit in-place with $EDITOR)
helm secrets edit values-secret.enc.yaml

# Install using encrypted values
helm secrets install myapp ./myapp \
  -f values.yaml \
  -f secrets://values-secret.enc.yaml

# Upgrade using encrypted values
helm secrets upgrade myapp ./myapp \
  -f values.yaml \
  -f secrets://values-secret.enc.yaml
```

`.sops.yaml` configures which keys encrypt which paths:

```yaml
creation_rules:
  - path_regex: .*secret.*\.yaml$
    kms: arn:aws:kms:us-east-1:123456789:key/abc-123
```

## Chart Signing

Sign charts for provenance verification:

```bash
# Generate a GnuPG key (one-time)
gpg --quick-generate-key "Helm Charts <charts@example.com>"

# Package and sign
helm package myapp --sign --key "Helm Charts" --keyring ~/.gnupg/pubring.gpg

# Verify a signed chart
helm verify myapp-1.0.0.tgz --keyring ~/.gnupg/pubring.gpg

# Install with verification
helm install myapp myapp-1.0.0.tgz --verify --keyring ~/.gnupg/pubring.gpg
```

The `--sign` flag generates a `.prov` provenance file alongside the `.tgz` archive. Push both to the
chart repository.

## helm unittest Plugin

Write YAML-based tests for chart templates:

```bash
# Install the plugin
helm plugin install https://github.com/helm-unittest/helm-unittest

# Run tests
helm unittest ./myapp

# With JUnit output (for CI)
helm unittest ./myapp --output-type junit --output-file results.xml
```

Test file at `tests/deployment_test.yaml`:

```yaml
suite: deployment tests
templates:
  - templates/deployment.yaml
tests:
  - it: should set replicas from values
    set:
      replicaCount: 5
    asserts:
      - equal:
          path: spec.replicas
          value: 5

  - it: should use the correct image
    set:
      image:
        repository: myapp
        tag: v2.0.0
    asserts:
      - equal:
          path: spec.template.spec.containers[0].image
          value: "myapp:v2.0.0"

  - it: should not set replicas when HPA is enabled
    set:
      autoscaling:
        enabled: true
    asserts:
      - isNull:
          path: spec.replicas

  - it: should fail without image repository
    set:
      image.repository: null
    asserts:
      - failedTemplate: {}
```

## CI/CD Integration Patterns

### GitHub Actions

```yaml
name: Helm CI
on: [push, pull_request]
jobs:
  lint-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: azure/setup-helm@v4
      - run: helm lint ./myapp
      - run: helm template myapp ./myapp --values values-prod.yaml
      - uses: helm/chart-testing-action@v2
      - run: ct lint --charts ./myapp
```

### Helmfile (multi-chart orchestration)

```yaml
# helmfile.yaml
repositories:
  - name: bitnami
    url: https://charts.bitnami.com/bitnami

releases:
  - name: postgresql
    namespace: database
    chart: bitnami/postgresql
    version: 13.4.3
    values:
      - values/postgresql.yaml

  - name: myapp
    namespace: production
    chart: ./charts/myapp
    values:
      - values/myapp-prod.yaml
    needs:
      - database/postgresql
```

```bash
# Apply all releases
helmfile apply

# Diff before applying
helmfile diff

# Target specific release
helmfile -l name=myapp apply
```

### ArgoCD Application

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: myapp
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/myorg/myapp
    targetRevision: main
    path: charts/myapp
    helm:
      valueFiles:
        - values-prod.yaml
      parameters:
        - name: image.tag
          value: v2.0.0
  destination:
    server: https://kubernetes.default.svc
    namespace: production
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
```

### FluxCD HelmRelease

```yaml
apiVersion: helm.toolkit.fluxcd.io/v2
kind: HelmRelease
metadata:
  name: myapp
  namespace: production
spec:
  interval: 10m
  chart:
    spec:
      chart: myapp
      version: "1.x"
      sourceRef:
        kind: HelmRepository
        name: myorg
  valuesFrom:
    - kind: ConfigMap
      name: myapp-values
  values:
    image:
      tag: v2.0.0
```
