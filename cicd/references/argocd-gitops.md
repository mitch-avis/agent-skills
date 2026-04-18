# ArgoCD GitOps

## Architecture

```text
ArgoCD:
├── API Server          (UI / CLI / API)
├── Repository Server   (Git interaction)
├── Application Controller (K8s reconciliation)
├── Redis               (caching)
├── Dex                 (SSO / RBAC)
└── ApplicationSet Controller (multi-cluster)
```

## Installation

```bash
# Standard install
kubectl create namespace argocd
kubectl apply -n argocd \
  -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# HA install
kubectl apply -n argocd \
  -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/ha/install.yaml

# Get initial admin password
kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath="{.data.password}" | base64 -d

# Access UI
kubectl port-forward svc/argocd-server -n argocd 8080:443

# Login and change password
argocd login localhost:8080 --username admin --password <password>
argocd account update-password
```

## Application CRD

### Basic Application (Kustomize)

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: myapp
  namespace: argocd
  finalizers:
    - resources-finalizer.argocd.argoproj.io
spec:
  project: production
  source:
    repoURL: https://github.com/myorg/myapp
    targetRevision: main
    path: k8s/overlays/production
  destination:
    server: https://kubernetes.default.svc
    namespace: production
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
      allowEmpty: false
    syncOptions:
      - CreateNamespace=true
    retry:
      limit: 5
      backoff:
        duration: 5s
        factor: 2
        maxDuration: 3m
```

### Helm Application

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: myapp-helm
  namespace: argocd
spec:
  project: production
  source:
    repoURL: https://github.com/myorg/helm-charts
    targetRevision: main
    path: charts/myapp
    helm:
      releaseName: myapp
      valueFiles:
        - values.yaml
        - values-production.yaml
      parameters:
        - name: image.tag
          value: "v2.0.0"
        - name: replicaCount
          value: "5"
      values: |
        ingress:
          enabled: true
          hosts:
            - myapp.example.com
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

### Kustomize Application

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: myapp-kustomize
  namespace: argocd
spec:
  project: production
  source:
    repoURL: https://github.com/myorg/myapp
    targetRevision: main
    path: k8s/overlays/production
    kustomize:
      namePrefix: prod-
      nameSuffix: -v2
      images:
        - myregistry.io/myapp:v2.0.0
      commonLabels:
        environment: production
      commonAnnotations:
        managed-by: argocd
  destination:
    server: https://kubernetes.default.svc
    namespace: production
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
```

## AppProject with RBAC

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: production
  namespace: argocd
spec:
  description: Production applications
  sourceRepos:
    - https://github.com/myorg/*
    - https://charts.bitnami.com/bitnami
  destinations:
    - namespace: production
      server: https://kubernetes.default.svc
    - namespace: monitoring
      server: https://kubernetes.default.svc
  clusterResourceWhitelist:
    - group: "*"
      kind: "*"
  namespaceResourceBlacklist:
    - group: ""
      kind: ResourceQuota
    - group: ""
      kind: LimitRange
  roles:
    - name: developer
      description: Developers can sync apps
      policies:
        - p, proj:production:developer, applications, sync, production/*, allow
        - p, proj:production:developer, applications, get, production/*, allow
      groups:
        - developers
    - name: admin
      description: Admins have full access
      policies:
        - p, proj:production:admin, applications, *, production/*, allow
      groups:
        - platform-team
  syncWindows:
    - kind: allow
      schedule: "0 9 * * 1-5"
      duration: 8h
      applications: ["*"]
    - kind: deny
      schedule: "0 0 * * 0,6"
      duration: 24h
      applications: ["*"]
  orphanedResources:
    warn: true
```

## ApplicationSet Generators

### Git Generator (Multi-Environment)

```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: myapp-environments
  namespace: argocd
spec:
  generators:
    - git:
        repoURL: https://github.com/myorg/myapp
        revision: main
        directories:
          - path: k8s/overlays/*
  template:
    metadata:
      name: "myapp-{{path.basename}}"
    spec:
      project: production
      source:
        repoURL: https://github.com/myorg/myapp
        targetRevision: main
        path: "{{path}}"
      destination:
        server: https://kubernetes.default.svc
        namespace: "{{path.basename}}"
      syncPolicy:
        automated:
          prune: true
          selfHeal: true
```

### List Generator (Multi-Cluster)

```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: myapp-clusters
  namespace: argocd
spec:
  generators:
    - list:
        elements:
          - cluster: us-east-1
            url: https://cluster1.example.com
            namespace: production
          - cluster: us-west-2
            url: https://cluster2.example.com
            namespace: production
          - cluster: eu-central-1
            url: https://cluster3.example.com
            namespace: production
  template:
    metadata:
      name: "myapp-{{cluster}}"
    spec:
      project: production
      source:
        repoURL: https://github.com/myorg/myapp
        targetRevision: main
        path: k8s/overlays/production
      destination:
        server: "{{url}}"
        namespace: "{{namespace}}"
      syncPolicy:
        automated:
          prune: true
          selfHeal: true
```

### Matrix Generator (Environments x Clusters)

```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: myapp-matrix
  namespace: argocd
spec:
  generators:
    - matrix:
        generators:
          - git:
              repoURL: https://github.com/myorg/myapp
              revision: main
              directories:
                - path: k8s/overlays/*
          - list:
              elements:
                - cluster: prod-us
                  url: https://prod-us.example.com
                - cluster: prod-eu
                  url: https://prod-eu.example.com
  template:
    metadata:
      name: "myapp-{{path.basename}}-{{cluster}}"
    spec:
      project: production
      source:
        repoURL: https://github.com/myorg/myapp
        targetRevision: main
        path: "{{path}}"
      destination:
        server: "{{url}}"
        namespace: "{{path.basename}}"
      syncPolicy:
        automated:
          prune: true
          selfHeal: true
```

## Sync Strategies

### Automated Sync with All Options

```yaml
syncPolicy:
  automated:
    prune: true
    selfHeal: true
    allowEmpty: false
  syncOptions:
    - CreateNamespace=true
    - PrunePropagationPolicy=foreground
    - PruneLast=true
    - ApplyOutOfSyncOnly=true
    - RespectIgnoreDifferences=true
    - ServerSideApply=true
  retry:
    limit: 5
    backoff:
      duration: 5s
      factor: 2
      maxDuration: 3m
```

### Sync Hooks and Waves

Use hooks for ordered operations around sync events:

```yaml
# PreSync hook — run database migration before deploying
apiVersion: batch/v1
kind: Job
metadata:
  name: database-migration
  annotations:
    argocd.argoproj.io/hook: PreSync
    argocd.argoproj.io/hook-delete-policy: HookSucceeded
    argocd.argoproj.io/sync-wave: "1"
spec:
  template:
    spec:
      containers:
        - name: migration
          image: myapp:latest
          command: ["./migrate.sh"]
      restartPolicy: Never

---
# PostSync hook — smoke test after deploying
apiVersion: batch/v1
kind: Job
metadata:
  name: smoke-test
  annotations:
    argocd.argoproj.io/hook: PostSync
    argocd.argoproj.io/hook-delete-policy: BeforeHookCreation
    argocd.argoproj.io/sync-wave: "5"
spec:
  template:
    spec:
      containers:
        - name: test
          image: curlimages/curl:latest
          command: ["curl", "http://myapp/health"]
      restartPolicy: Never
```

## SSO with GitHub

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-cm
  namespace: argocd
data:
  url: https://argocd.example.com
  dex.config: |
    connectors:
      - type: github
        id: github
        name: GitHub
        config:
          clientID: $dex.github.clientId
          clientSecret: $dex.github.clientSecret
          orgs:
            - name: myorg
              teams:
                - platform-team
                - developers

---
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-rbac-cm
  namespace: argocd
data:
  policy.default: role:readonly
  policy.csv: |
    g, myorg:platform-team, role:admin
    g, myorg:developers, role:developer
    p, role:developer, applications, get, */*, allow
    p, role:developer, applications, sync, */*, allow
    p, role:developer, repositories, get, *, allow
    p, role:developer, projects, get, *, allow
  scopes: "[groups, email]"
```

## Custom Health Checks

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-cm
  namespace: argocd
data:
  resource.customizations.health.argoproj.io_Rollout: |
    hs = {}
    if obj.status ~= nil then
      if obj.status.conditions ~= nil then
        for i, condition in ipairs(obj.status.conditions) do
          if condition.type == "Progressing"
            and condition.reason == "RolloutCompleted" then
            hs.status = "Healthy"
            hs.message = "Rollout completed"
            return hs
          end
        end
      end
    end
    hs.status = "Progressing"
    hs.message = "Rollout in progress"
    return hs
```

## CLI Commands

### Application Management

```bash
# Create
argocd app create myapp \
  --repo https://github.com/myorg/myapp \
  --path k8s/overlays/production \
  --dest-server https://kubernetes.default.svc \
  --dest-namespace production

# List / inspect
argocd app list
argocd app list -o wide
argocd app get myapp
argocd app get myapp --refresh

# Sync
argocd app sync myapp
argocd app sync myapp --prune
argocd app sync myapp --dry-run
argocd app sync myapp --force

# Rollback / delete
argocd app rollback myapp
argocd app delete myapp
argocd app delete myapp --cascade=false  # Keep resources
```

### Repository Management

```bash
argocd repo add https://github.com/myorg/myapp \
  --username myuser --password mytoken
argocd repo list
argocd repo rm https://github.com/myorg/myapp
```

### Cluster Management

```bash
argocd cluster add my-cluster-context
argocd cluster list
argocd cluster rm https://cluster.example.com
```

### Project Management

```bash
argocd proj create production
argocd proj add-source production https://github.com/myorg/*
argocd proj add-destination production \
  https://kubernetes.default.svc production
argocd proj list
argocd proj get production
```

## CI Integration Pattern

CI builds and pushes the image, then updates the manifests repo. ArgoCD detects the commit and
syncs.

```yaml
# GitHub Actions — update manifests repo after image push
update-manifests:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
      with:
        repository: org/k8s-manifests
        token: ${{ secrets.DEPLOY_TOKEN }}
    - run: |
        cd overlays/production
        kustomize edit set image app=ghcr.io/org/app:${{ github.sha }}
    - run: |
        git config user.name "github-actions"
        git config user.email "actions@github.com"
        git add .
        git commit -m "deploy: app ${{ github.sha }}"
        git push
```

```yaml
# GitLab CI — update manifests repo after image push
deploy:
  stage: deploy
  image: bitnami/kubectl:latest
  script:
    - git clone https://deploy:${DEPLOY_TOKEN}@gitlab.com/org/k8s-manifests
    - cd k8s-manifests/overlays/production
    - kustomize edit set image app=${CI_REGISTRY_IMAGE}:${CI_COMMIT_SHA}
    - git add . && git commit -m "deploy: app ${CI_COMMIT_SHA}"
    - git push
```

## Anti-Patterns

### No Resource Pruning

```yaml
# BAD — orphaned resources accumulate
syncPolicy:
  automated: {}

# GOOD — prune resources removed from Git
syncPolicy:
  automated:
    prune: true
    selfHeal: true
```

### Manual Sync Only

```yaml
# BAD — requires human intervention, defeats GitOps
syncPolicy: {}

# GOOD — automated sync with self-heal
syncPolicy:
  automated:
    prune: true
    selfHeal: true
```

### Single Giant Application

```yaml
# BAD — one Application for entire cluster
# GOOD — separate Applications per service/component
#   Use ApplicationSets to manage many apps declaratively
```

### No RBAC

```yaml
# BAD — everyone is admin
# GOOD — project-level RBAC with least privilege
roles:
  - name: developer
    policies:
      - p, proj:prod:dev, applications, sync, prod/*, allow
```

## Best Practices Checklist

- [ ] Enable automated sync with prune and self-heal
- [ ] Use AppProjects to isolate teams and environments
- [ ] Implement RBAC with least-privilege roles
- [ ] Set sync windows to control deployment timing
- [ ] Use sync waves for ordered deployments (DB migration first)
- [ ] Configure health checks for custom resources
- [ ] Use ApplicationSets for multi-cluster or multi-environment
- [ ] Set up notifications (Slack, Teams, email)
- [ ] Enable SSO via Dex (GitHub, GitLab, OIDC)
- [ ] Audit all changes through Git history
