---
name: helm
description: >-
  Helm 3 chart development, templating, packaging, and production operations. Use when creating Helm
  charts, writing Go templates for Kubernetes manifests, managing chart dependencies, packaging for
  distribution, performing installs/upgrades/rollbacks, or configuring multi-environment
  deployments.
---

# Helm

## When to Use

- Creating or scaffolding Helm charts
- Writing or debugging Go templates for Kubernetes manifests
- Managing chart dependencies
- Installing, upgrading, or rolling back releases
- Packaging charts for distribution
- Multi-environment configuration (dev/staging/prod)

## Related Skills

- **kubernetes** — load alongside this skill when creating or reviewing charts. The kubernetes skill
  defines security constraints, RBAC patterns, NetworkPolicies, and resource best practices that
  every chart must follow. Load its reference guides on demand for advanced K8s patterns (service
  mesh, GitOps, cost optimization, etc.).

## Reference Guides

Load on demand — do not read all files upfront.

| Topic | File | Load When |
| ---- | ---- | ---- |
| Template Patterns | references/templates.md | Writing or reviewing chart template files |
| Go Templates | references/go-templates.md | Writing or debugging Go template syntax |
| Operations | references/operations.md | CLI commands, packaging, distribution, plugins |

## Constraints

Charts MUST produce manifests that satisfy the kubernetes skill constraints:

- Set resource `requests` **and** `limits` on every container
- Include liveness and readiness probes
- Use Secrets for sensitive data (never ConfigMaps or plain env vars)
- Dedicated ServiceAccount per workload — never rely on `default`
- Include a NetworkPolicy template (default-deny + explicit allows)
- Run containers as non-root with `readOnlyRootFilesystem: true`
- Use `app.kubernetes.io/*` standard labels (via `_helpers.tpl`)
- Never use `:latest` — default to `.Chart.AppVersion`
- Include PodDisruptionBudget for production workloads

## Chart Structure

```text
mychart/
├── Chart.yaml          # Chart metadata (required)
├── values.yaml         # Default values (required)
├── values.schema.json  # Values validation schema
├── charts/             # Dependency charts
├── templates/          # Template files
│   ├── NOTES.txt       # Post-install notes
│   ├── _helpers.tpl    # Template helpers
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── ingress.yaml
│   ├── configmap.yaml
│   ├── serviceaccount.yaml
│   ├── hpa.yaml
│   └── tests/
│       └── test-connection.yaml
├── crds/               # Custom Resource Definitions
└── .helmignore         # Files to ignore when packaging
```

## Chart.yaml

```yaml
apiVersion: v2
name: myapp
description: A production-grade web application
type: application
version: 1.2.3
appVersion: "2.0.1"

keywords:
  - web
  - api

maintainers:
  - name: DevOps Team
    email: devops@example.com

dependencies:
  - name: postgresql
    version: "12.x.x"
    repository: "https://charts.bitnami.com/bitnami"
    condition: postgresql.enabled
  - name: redis
    version: "17.x.x"
    repository: "https://charts.bitnami.com/bitnami"
    condition: redis.enabled
    tags:
      - cache

kubeVersion: ">=1.28.0"
```

## values.yaml

```yaml
replicaCount: 3

image:
  repository: myregistry.io/myapp
  pullPolicy: IfNotPresent
  tag: ""  # Overrides appVersion

imagePullSecrets:
  - name: registry-secret

nameOverride: ""
fullnameOverride: ""

serviceAccount:
  create: true
  annotations: {}
  name: ""

podAnnotations:
  prometheus.io/scrape: "true"
  prometheus.io/port: "9090"

podSecurityContext:
  runAsNonRoot: true
  runAsUser: 1000
  fsGroup: 2000
  seccompProfile:
    type: RuntimeDefault

securityContext:
  allowPrivilegeEscalation: false
  readOnlyRootFilesystem: true
  capabilities:
    drop: ["ALL"]

service:
  type: ClusterIP
  port: 80
  targetPort: 8080

ingress:
  enabled: true
  className: nginx
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
  hosts:
    - host: myapp.example.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: myapp-tls
      hosts:
        - myapp.example.com

resources:
  requests:
    cpu: 250m
    memory: 256Mi
  limits:
    cpu: 500m
    memory: 512Mi

autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70
  targetMemoryUtilizationPercentage: 80

affinity:
  podAntiAffinity:
    preferredDuringSchedulingIgnoredDuringExecution:
      - weight: 100
        podAffinityTerm:
          labelSelector:
            matchExpressions:
              - key: app.kubernetes.io/name
                operator: In
                values: ["myapp"]
          topologyKey: kubernetes.io/hostname

nodeSelector: {}
tolerations: []
```

## Values Schema Validation

```json
{
  "$schema": "https://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["replicaCount", "image"],
  "properties": {
    "replicaCount": {
      "type": "integer",
      "minimum": 1
    },
    "image": {
      "type": "object",
      "required": ["repository"],
      "properties": {
        "repository": { "type": "string" },
        "tag": { "type": "string" }
      }
    }
  }
}
```

## Multi-Environment Configuration

```text
myapp/
├── values.yaml          # Defaults
├── values-dev.yaml      # Development overrides
├── values-staging.yaml  # Staging overrides
└── values-prod.yaml     # Production overrides
```

```bash
helm install myapp ./myapp -f values-prod.yaml -n production
```

## Best Practices

1. **Semantic versioning** — `version` for chart, `appVersion` for the application
2. **Always lint** — `helm lint` before every commit
3. **Config checksums** — force pod restart on ConfigMap/Secret change
4. **Quote strings** — `{{ .Values.config.value | quote }}` 5. **Default values** — `{{
.Values.replicaCount | default 3 }}`
5. **Schema validation** — provide `values.schema.json` for required values
6. **Atomic upgrades** — `helm upgrade --atomic` rolls back on failure
7. **Document values** — comment every value in `values.yaml`

## Anti-Patterns

- **Hardcoded values in templates** — use `{{ .Values.* }}` for everything configurable
- **No resource limits** — always define `resources.requests` and `resources.limits`
- **Missing probes** — include liveness and readiness probes in Deployment templates
- **`:latest` image tag** — use `{{ .Values.image.tag | default .Chart.AppVersion }}`
- **Skipping `--dry-run`** — always validate before real installs/upgrades

## Chart Types

| Type        | Description                                            |
| ----------- | ------------------------------------------------------ |
| application | Default. Installs Kubernetes resources into a cluster. |
| library     | Provides helpers only. Cannot be installed directly.   |

Set in `Chart.yaml`:

```yaml
type: library
```

## NOTES.txt Template

Post-install instructions shown to the user after `helm install`:

```text
{{- if .Values.ingress.enabled }}
Visit https://{{ (index .Values.ingress.hosts 0).host }} to access {{ include "myapp.fullname" . }}.
{{- else }}
Get the application URL by running:
  export POD_NAME=$(kubectl get pods -n {{ .Release.Namespace }} \
    -l "{{ include "myapp.selectorLabels" . }}" -o jsonpath="{.items[0].metadata.name}")
  kubectl port-forward $POD_NAME 8080:{{ .Values.service.targetPort }}
  echo "Visit http://127.0.0.1:8080"
{{- end }}
```

## .helmignore Patterns

Common entries to keep chart packages lean:

```text
.git
.gitignore
.vscode/
*.swp
*.bak
*.tmp
*.orig
*~
.DS_Store
ci/
tests/
README.md
CHANGELOG.md
LICENSE
```

## CRDs Directory Convention

Files in `crds/` are installed **before** templates and are:

- **Not templated** — plain YAML only (no `{{ }}`)
- **Not upgraded** — Helm never modifies CRDs after first install
- **Not deleted** — `helm uninstall` leaves CRDs in place

Place CRDs here when your chart owns the CRD lifecycle. For third-party CRDs, install them
separately.

## Hook Types

| Hook                | Fires                                    |
| ------------------- | ---------------------------------------- |
| pre-install         | Before resources are created             |
| post-install        | After all resources are created          |
| pre-upgrade         | Before resources are upgraded            |
| post-upgrade        | After all resources are upgraded         |
| pre-delete          | Before any resources are deleted         |
| post-delete         | After all resources are deleted          |
| pre-rollback        | Before resources are rolled back         |
| post-rollback       | After all resources are rolled back      |
| test                | When `helm test` is invoked              |

Use `helm.sh/hook-weight` (string integer) to order hooks within the same phase — lower weights
execute first.

## Dependency Features

### alias

Run multiple instances of the same subchart under different names:

```yaml
dependencies:
  - name: postgresql
    version: "12.x.x"
    repository: "https://charts.bitnami.com/bitnami"
    alias: primary-db
  - name: postgresql
    version: "12.x.x"
    repository: "https://charts.bitnami.com/bitnami"
    alias: analytics-db
```

### import-values

Import specific values from a subchart into the parent:

```yaml
dependencies:
  - name: postgresql
    version: "12.x.x"
    repository: "https://charts.bitnami.com/bitnami"
    import-values:
      - child: primary
        parent: database
```
