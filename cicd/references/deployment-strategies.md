# Deployment Strategies

## Rolling Update (Kubernetes)

Replace pods incrementally with zero downtime.

```yaml
# k8s/deployment.yml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  selector:
    matchLabels:
      app: app
  template:
    spec:
      containers:
        - name: app
          image: ghcr.io/org/app:latest
          readinessProbe:
            httpGet:
              path: /health
              port: 8080
            initialDelaySeconds: 5
            periodSeconds: 10
          livenessProbe:
            httpGet:
              path: /health
              port: 8080
            initialDelaySeconds: 15
            periodSeconds: 20
```

Deploy and verify:

```bash
kubectl set image deployment/app app=ghcr.io/org/app:v2.0.0
kubectl rollout status deployment/app --timeout=5m
# Rollback if needed
kubectl rollout undo deployment/app
```

## Blue-Green Deployment

Maintain two identical environments. Switch traffic after validation.

```yaml
# blue deployment (current production)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app-blue
  labels:
    app: app
    version: blue
spec:
  replicas: 3
  template:
    spec:
      containers:
        - name: app
          image: ghcr.io/org/app:v1.0.0

---
# green deployment (new version)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app-green
  labels:
    app: app
    version: green
spec:
  replicas: 3
  template:
    spec:
      containers:
        - name: app
          image: ghcr.io/org/app:v2.0.0

---
# Service points to active version
apiVersion: v1
kind: Service
metadata:
  name: app
spec:
  selector:
    app: app
    version: blue  # Switch to 'green' after validation
  ports:
    - port: 80
      targetPort: 8080
```

Switch traffic:

```bash
# Validate green
kubectl exec -it deploy/app-green -- curl localhost:8080/health

# Switch traffic
kubectl patch service app -p '{"spec":{"selector":{"version":"green"}}}'

# Rollback
kubectl patch service app -p '{"spec":{"selector":{"version":"blue"}}}'
```

## Canary Deployment

Route a percentage of traffic to the new version, then increase gradually.

```yaml
# Stable deployment (90% traffic)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app-stable
spec:
  replicas: 9
  template:
    spec:
      containers:
        - name: app
          image: ghcr.io/org/app:v1.0.0

---
# Canary deployment (10% traffic)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app-canary
spec:
  replicas: 1
  template:
    spec:
      containers:
        - name: app
          image: ghcr.io/org/app:v2.0.0

---
# Service selects both via shared label
apiVersion: v1
kind: Service
metadata:
  name: app
spec:
  selector:
    app: app  # Both deployments share this label
  ports:
    - port: 80
      targetPort: 8080
```

With Istio for precise traffic splitting:

```yaml
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: app
spec:
  hosts: [app]
  http:
    - route:
        - destination:
            host: app
            subset: stable
          weight: 90
        - destination:
            host: app
            subset: canary
          weight: 10
```

## GitOps with ArgoCD

Declare desired state in Git. ArgoCD syncs clusters automatically.

### Application manifest

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: app
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

### CI pipeline updates image tag in Git

```yaml
# GitHub Actions — update manifests repo
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

### Deploy via ArgoCD CLI

```yaml
deploy:
  steps:
    - run: |
        argocd app set app --parameter image.tag=${{ github.sha }}
        argocd app sync app --prune
        argocd app wait app --health --timeout 600
```

## Terraform Pipeline

### GitLab CI

```yaml
stages:
  - validate
  - plan
  - apply

variables:
  TF_ROOT: ${CI_PROJECT_DIR}/terraform

.terraform:
  image: hashicorp/terraform:1.6
  before_script:
    - cd ${TF_ROOT}

validate:
  extends: .terraform
  stage: validate
  script:
    - terraform init -backend=false
    - terraform validate
    - terraform fmt -check

plan:
  extends: .terraform
  stage: plan
  script:
    - terraform init
    - terraform plan -out=tfplan
  artifacts:
    paths:
      - ${TF_ROOT}/tfplan
    expire_in: 1 day

apply:
  extends: .terraform
  stage: apply
  script:
    - terraform init
    - terraform apply -auto-approve tfplan
  dependencies: [plan]
  when: manual
  rules:
    - if: $CI_COMMIT_BRANCH == "main"
```

### GitHub Actions

```yaml
jobs:
  terraform:
    runs-on: ubuntu-latest
    permissions:
      id-token: write
      contents: read
      pull-requests: write
    defaults:
      run:
        working-directory: terraform/
    steps:
      - uses: actions/checkout@v4
      - uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: 1.6.0
      - run: terraform init
      - run: terraform validate
      - run: terraform plan -out=tfplan
      - if: github.ref == 'refs/heads/main'
        run: terraform apply -auto-approve tfplan
```

## Release Pipeline with Semantic Versioning

```yaml
# GitLab CI
release:
  stage: deploy
  image: node:20
  script:
    - npx semantic-release
  rules:
    - if: $CI_COMMIT_BRANCH == "main"
```

```yaml
# GitHub Actions
release:
  runs-on: ubuntu-latest
  permissions:
    contents: write
  steps:
    - uses: actions/checkout@v4
      with:
        fetch-depth: 0
    - uses: actions/setup-node@v4
      with:
        node-version: "20"
    - run: npx semantic-release
      env:
        GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

## Health Check Pattern

Always verify deployments before declaring success.

```bash
#!/usr/bin/env bash
set -euo pipefail

URL="${1:?Usage: health-check.sh <url>}"
RETRIES=30
DELAY=10

for i in $(seq 1 "$RETRIES"); do
  if curl -sf "$URL/health" > /dev/null; then
    echo "Health check passed on attempt $i"
    exit 0
  fi
  echo "Attempt $i/$RETRIES failed, retrying in ${DELAY}s..."
  sleep "$DELAY"
done

echo "Health check failed after $RETRIES attempts"
exit 1
```
