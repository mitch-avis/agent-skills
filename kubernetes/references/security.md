# Kubernetes Security

## Pod Security Standards

Enforce at namespace level — prefer `restricted` for production:

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

Three levels:

- **Restricted** — most secure, required for production (non-root, drop all capabilities, read-only
  root filesystem, seccomp)
- **Baseline** — minimally restrictive, prevents known privilege escalations
- **Privileged** — unrestricted, only for system-level workloads

## Security Context

### Pod and Container Level

```yaml
spec:
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    fsGroup: 1000
    seccompProfile:
      type: RuntimeDefault
  containers:
    - name: app
      securityContext:
        allowPrivilegeEscalation: false
        readOnlyRootFilesystem: true
        capabilities:
          drop: ["ALL"]
```

## RBAC Patterns

### Namespace-Scoped Role

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: pod-reader
  namespace: production
rules:
  - apiGroups: [""]
    resources: ["pods"]
    verbs: ["get", "watch", "list"]
```

### Cluster-Wide ClusterRole

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: secret-reader
rules:
  - apiGroups: [""]
    resources: ["secrets"]
    verbs: ["get", "watch", "list"]
```

### RoleBinding

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: read-pods
  namespace: production
subjects:
  - kind: ServiceAccount
    name: my-app-sa
    namespace: production
roleRef:
  kind: Role
  name: pod-reader
  apiGroup: rbac.authorization.k8s.io
```

## OPA Gatekeeper

### ConstraintTemplate (Require Labels)

```yaml
apiVersion: templates.gatekeeper.sh/v1
kind: ConstraintTemplate
metadata:
  name: k8srequiredlabels
spec:
  crd:
    spec:
      names:
        kind: K8sRequiredLabels
      validation:
        openAPIV3Schema:
          type: object
          properties:
            labels:
              type: array
              items:
                type: string
  targets:
    - target: admission.k8s.gatekeeper.sh
      rego: |
        package k8srequiredlabels
        violation[{"msg": msg, "details": {"missing_labels": missing}}] {
          provided := {label | input.review.object.metadata.labels[label]}
          required := {label | label := input.parameters.labels[_]}
          missing := required - provided
          count(missing) > 0
          msg := sprintf("missing required labels: %v", [missing])
        }
```

### Constraint

```yaml
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: K8sRequiredLabels
metadata:
  name: require-app-label
spec:
  match:
    kinds:
      - apiGroups: ["apps"]
        kinds: ["Deployment"]
  parameters:
    labels: ["app.kubernetes.io/name", "app.kubernetes.io/version"]
```

## Istio Security

### Strict mTLS

```yaml
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: default
  namespace: production
spec:
  mtls:
    mode: STRICT
```

### AuthorizationPolicy

```yaml
apiVersion: security.istio.io/v1beta1
kind: AuthorizationPolicy
metadata:
  name: allow-frontend
  namespace: production
spec:
  selector:
    matchLabels:
      app.kubernetes.io/name: backend
  action: ALLOW
  rules:
    - from:
        - source:
            principals:
              - "cluster.local/ns/production/sa/frontend-sa"
```

## Compliance Checklists

### CIS Kubernetes Benchmark

- RBAC authorization enabled
- Audit logging enabled
- Pod Security Standards enforced
- NetworkPolicies configured
- Secrets encrypted at rest
- Node authentication enabled
- API server access restricted

### Security Checklist

- [ ] Run as non-root user
- [ ] Drop all capabilities
- [ ] Read-only root filesystem
- [ ] Disable privilege escalation
- [ ] Set seccomp profile
- [ ] Dedicated ServiceAccount per workload
- [ ] Least-privilege RBAC
- [ ] NetworkPolicies in place
- [ ] Secrets managed externally (Vault, ESO, Sealed Secrets)
- [ ] Container images scanned for vulnerabilities
- [ ] Image pull from trusted registries only

## Troubleshooting

```bash
# Check effective permissions for a service account
kubectl auth can-i list pods \
  --as=system:serviceaccount:production:my-app-sa

# List all permissions
kubectl auth can-i --list \
  --as=system:serviceaccount:production:my-app-sa

# Check NetworkPolicy effect
kubectl describe networkpolicy -n production
```

## Additional RBAC Patterns

### Read-Only Cluster Access

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: read-only
rules:
  - apiGroups: ["", "apps", "batch", "networking.k8s.io"]
    resources: ["*"]
    verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: read-only-binding
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: read-only
subjects:
  - kind: Group
    name: auditors
    apiGroup: rbac.authorization.k8s.io
```

### Namespace Admin

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: namespace-admin
  namespace: development
rules:
  - apiGroups: ["", "apps", "batch", "networking.k8s.io"]
    resources: ["*"]
    verbs: ["*"]
```

### Deployment Manager

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: deployment-manager
  namespace: production
rules:
  - apiGroups: ["apps"]
    resources: ["deployments", "replicasets"]
    verbs: ["get", "list", "watch", "create", "update", "patch"]
  - apiGroups: [""]
    resources: ["pods"]
    verbs: ["get", "list", "watch"]
```

### CI/CD Pipeline

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: cicd-deployer
rules:
  - apiGroups: ["apps"]
    resources: ["deployments", "replicasets"]
    verbs: ["get", "list", "watch", "create", "update", "patch"]
  - apiGroups: [""]
    resources: ["services", "configmaps"]
    verbs: ["get", "list", "watch", "create", "update", "patch"]
  - apiGroups: [""]
    resources: ["pods"]
    verbs: ["get", "list", "watch"]
```

### ServiceAccount Best Practice

Disable automatic token mounting for workloads that don't need the API:

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: my-app-sa
  namespace: production
automountServiceAccountToken: false
```

## RBAC Reference

### Common Verbs

| Verb               | Description                    |
| ------------------ | ------------------------------ |
| get                | Read a single resource         |
| list               | List resources in a namespace  |
| watch              | Stream resource changes        |
| create             | Create a resource              |
| update             | Replace a resource             |
| patch              | Partially modify a resource    |
| delete             | Delete a resource              |
| deletecollection   | Delete multiple resources      |
| `*`                | All verbs (avoid in production)|

### Resource Scope

| Cluster-Scoped (ClusterRole only) | Namespace-Scoped (Role or ClusterRole) |
| --------------------------------- | -------------------------------------- |
| Nodes                             | Pods                                   |
| PersistentVolumes                 | Services                               |
| ClusterRoles / ClusterRoleBindings| Deployments, StatefulSets, DaemonSets  |
| Namespaces                        | ConfigMaps, Secrets                    |
| StorageClasses                    | Roles / RoleBindings                   |
| CustomResourceDefinitions         | Jobs, CronJobs                         |

## NIST Cybersecurity Framework

Mapping to Kubernetes controls:

- **Identify** — inventory of workloads, RBAC audit, CRD catalog
- **Protect** — Pod Security Standards, NetworkPolicies, Secrets encryption
- **Detect** — audit logging, Falco runtime detection, image scanning
- **Respond** — incident runbooks, pod quarantine (cordon + label)
- **Recover** — Velero backups, DR playbooks, rollback procedures
