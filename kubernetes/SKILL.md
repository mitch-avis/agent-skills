---
name: kubernetes
description: >-
  Deploy, secure, and manage Kubernetes workloads. Use when creating manifests, configuring RBAC,
  defining NetworkPolicies, setting up storage, troubleshooting pods, or designing cluster
  architecture. Covers Deployments, StatefulSets, DaemonSets, Jobs, Services, Ingress, ConfigMaps,
  Secrets, Pod Security Standards, OPA Gatekeeper, service mesh, GitOps, and multi-cluster patterns.
---

# Kubernetes

## When to Use

- Creating or reviewing Kubernetes manifests (Deployments, StatefulSets, Services, etc.)
- Configuring RBAC, NetworkPolicies, or Pod Security Standards
- Setting up persistent storage (PV, PVC, StorageClasses)
- Troubleshooting pod crashes, networking, or resource issues
- Designing cluster architecture, multi-tenancy, or GitOps workflows

## Related Skills

- [helm](../helm/SKILL.md) — when the output is a Helm chart (Go-templated manifests); covers chart
  structure, `_helpers.tpl`, Go template techniques, values schema, hooks, and CLI operations
- [docker](../docker/SKILL.md) — building and hardening the container images workloads run
- [cicd](../cicd/SKILL.md) — GitOps deploys, ArgoCD, rolling updates
- [observability](../observability/SKILL.md) — Prometheus/Grafana/Loki/OTel collectors on the
  cluster

## Core Workflow

1. **Analyze requirements** — workload type, scaling, security, storage
2. **Implement manifests** — declarative YAML with resource limits, probes, security context
3. **Secure** — RBAC, NetworkPolicies, Pod Security Standards, least privilege
4. **Validate** — `kubectl apply --dry-run=server`, `kube-linter lint`, `kube-score score`
5. **Deploy and verify** — `kubectl rollout status`, `kubectl get pods -w`, `kubectl describe pod`

## Reference Guides

Load on demand based on the task:

| Topic              | Reference                           | Load When                                                       |
| ------------------ | ----------------------------------- | --------------------------------------------------------------- |
| Workloads          | `references/workloads.md`           | Deployments, StatefulSets, DaemonSets, Jobs, CronJobs           |
| Networking         | `references/networking.md`          | Services, Ingress, NetworkPolicies, DNS, service mesh           |
| Security           | `references/security.md`            | Pod Security Standards, RBAC, OPA Gatekeeper, Istio, compliance |
| Configuration      | `references/configuration.md`       | ConfigMaps, Secrets, env vars, External Secrets Operator        |
| Storage            | `references/storage.md`             | PV, PVC, StorageClasses, snapshots, CSI drivers                 |
| Troubleshooting    | `references/troubleshooting.md`     | kubectl debug, logs, events, common failure patterns            |
| Custom Operators   | `references/custom-operators.md`    | CRDs, Operator SDK, controller reconciliation loops             |
| Service Mesh       | `references/service-mesh.md`        | Istio, Linkerd, traffic management, mTLS, observability         |
| GitOps             | `references/gitops.md`              | ArgoCD, Flux, progressive delivery, secret management           |
| Cost Optimization  | `references/cost-optimization.md`   | VPA, HPA, right-sizing, spot nodes, FinOps, quotas              |
| Multi-Cluster      | `references/multi-cluster.md`       | Cluster API, federation, cross-cluster networking, DR           |

## Constraints

### MUST DO

- Use declarative YAML manifests (avoid imperative kubectl in production)
- Set resource requests **and** limits on every container
- Include liveness and readiness probes
- Use Secrets for sensitive data (never ConfigMaps or plain env vars)
- Apply least-privilege RBAC — dedicated ServiceAccount per workload
- Implement NetworkPolicies (default-deny, then allow specific traffic)
- Use namespaces for logical isolation
- Label resources with `app.kubernetes.io/*` standard labels
- Use specific image tags (never `:latest` in production)
- Run containers as non-root with `readOnlyRootFilesystem: true`

### MUST NOT DO

- Deploy without resource limits
- Store credentials in ConfigMaps, env literals, or container images
- Use the `default` ServiceAccount for application pods
- Allow unrestricted network access (skip NetworkPolicies)
- Run containers as root without documented justification
- Skip health checks
- Expose unnecessary ports or services

## Deployment Pattern

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
  namespace: my-namespace
  labels:
    app.kubernetes.io/name: my-app
    app.kubernetes.io/version: "1.2.3"
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  selector:
    matchLabels:
      app.kubernetes.io/name: my-app
  template:
    metadata:
      labels:
        app.kubernetes.io/name: my-app
        app.kubernetes.io/version: "1.2.3"
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8080"
    spec:
      serviceAccountName: my-app-sa
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        fsGroup: 2000
        seccompProfile:
          type: RuntimeDefault
      containers:
        - name: my-app
          image: my-registry/my-app:1.2.3
          ports:
            - name: http
              containerPort: 8080
          resources:
            requests:
              cpu: "100m"
              memory: "128Mi"
            limits:
              cpu: "500m"
              memory: "512Mi"
          livenessProbe:
            httpGet:
              path: /healthz
              port: http
            initialDelaySeconds: 30
            periodSeconds: 10
            timeoutSeconds: 5
            failureThreshold: 3
          readinessProbe:
            httpGet:
              path: /ready
              port: http
            initialDelaySeconds: 5
            periodSeconds: 10
            timeoutSeconds: 3
            failureThreshold: 2
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities:
              drop: ["ALL"]
          envFrom:
            - configMapRef:
                name: my-app-config
            - secretRef:
                name: my-app-secret
```

## RBAC Pattern

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: my-app-sa
  namespace: my-namespace
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: my-app-role
  namespace: my-namespace
rules:
  - apiGroups: [""]
    resources: ["configmaps"]
    verbs: ["get", "list"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: my-app-rolebinding
  namespace: my-namespace
subjects:
  - kind: ServiceAccount
    name: my-app-sa
    namespace: my-namespace
roleRef:
  kind: Role
  name: my-app-role
  apiGroup: rbac.authorization.k8s.io
```

## NetworkPolicy Pattern

```yaml
# Default deny all traffic
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: my-namespace
spec:
  podSelector: {}
  policyTypes: ["Ingress", "Egress"]
---
# Allow DNS egress (required for service discovery)
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-dns
  namespace: my-namespace
spec:
  podSelector: {}
  policyTypes: ["Egress"]
  egress:
    - to:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: kube-system
      ports:
        - protocol: UDP
          port: 53
---
# Allow specific ingress
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-frontend-to-backend
  namespace: my-namespace
spec:
  podSelector:
    matchLabels:
      app.kubernetes.io/name: backend
  policyTypes: ["Ingress"]
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app.kubernetes.io/name: frontend
      ports:
        - protocol: TCP
          port: 8080
```

## Pod Security Standards

Apply at namespace level for enforcement:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: production
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted
```

## Validation Commands

```bash
# Validate manifests
kubectl apply -f manifest.yaml --dry-run=server
kube-linter lint manifest.yaml
kube-score score manifest.yaml

# Watch rollout
kubectl rollout status deployment/my-app -n my-namespace

# Inspect failures
kubectl describe pod <pod-name> -n my-namespace
kubectl logs <pod-name> -n my-namespace --previous

# Verify resource usage
kubectl top pods -n my-namespace

# Audit RBAC
kubectl auth can-i --list --as=system:serviceaccount:my-namespace:my-app-sa

# Rollback
kubectl rollout undo deployment/my-app -n my-namespace
```

## Output Checklist

When implementing Kubernetes resources, provide:

1. Complete YAML manifests with proper structure
2. RBAC configuration (ServiceAccount + Role + RoleBinding)
3. NetworkPolicy for network isolation
4. Security context on both pod and container level
5. Brief explanation of design decisions
