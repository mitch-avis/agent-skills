# GitHub Actions Patterns

## Multi-Stage Pipeline

Complete workflow with security, build, container, and deployment stages.

```yaml
name: CI/CD Pipeline

on:
  pull_request:
    branches: [main, develop]
  push:
    branches: [main]

permissions:
  contents: read
  security-events: write
  id-token: write

jobs:
  code-quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - name: Run Semgrep SAST
        uses: semgrep/semgrep-action@v1
        with:
          config: p/security-audit
      - name: SonarQube Scan
        uses: sonarsource/sonarqube-scan-action@master
        env:
          SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}
          SONAR_HOST_URL: ${{ secrets.SONAR_HOST_URL }}

  dependency-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/dependency-review-action@v4
        with:
          fail-on-severity: high
      - uses: snyk/actions/node@master
        env:
          SNYK_TOKEN: ${{ secrets.SNYK_TOKEN }}

  build:
    needs: [code-quality, dependency-check]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: npm
      - run: npm ci
      - run: npm run test:coverage
      - uses: codecov/codecov-action@v3
      - run: npm run build
      - uses: actions/upload-artifact@v4
        with:
          name: dist
          path: dist/
          retention-days: 7

  container:
    needs: build
    runs-on: ubuntu-latest
    outputs:
      image-digest: ${{ steps.build.outputs.digest }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/download-artifact@v4
        with:
          name: dist
          path: dist/
      - uses: docker/setup-buildx-action@v3
      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - id: build
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: |
            ghcr.io/${{ github.repository }}:${{ github.sha }}
            ghcr.io/${{ github.repository }}:latest
          cache-from: type=gha
          cache-to: type=gha,mode=max
      - uses: aquasecurity/trivy-action@master
        with:
          image-ref: ghcr.io/${{ github.repository }}:${{ github.sha }}
          format: sarif
          output: trivy-results.sarif
          severity: CRITICAL,HIGH
      - uses: github/codeql-action/upload-sarif@v2
        with:
          sarif_file: trivy-results.sarif

  sign:
    needs: container
    runs-on: ubuntu-latest
    permissions:
      packages: write
      id-token: write
    steps:
      - uses: sigstore/cosign-installer@v3
      - run: >-
          cosign sign --yes
          ghcr.io/${{ github.repository }}@${{ needs.container.outputs.image-digest }}

  deploy-staging:
    needs: sign
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    environment: staging
    steps:
      - uses: actions/checkout@v4
      - run: >-
          kubectl set image deployment/app
          app=ghcr.io/${{ github.repository }}:${{ github.sha }}
          --namespace=staging
      - run: kubectl rollout status deployment/app --namespace=staging --timeout=5m
      - run: npm run test:smoke -- --env=staging

  deploy-production:
    needs: deploy-staging
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    environment: production
    steps:
      - uses: actions/checkout@v4
      - run: >-
          argocd app set app --parameter image.tag=${{ github.sha }}
      - run: argocd app sync app --prune
      - run: argocd app wait app --health --timeout 600
```

## Reusable Workflows

Extract common build logic into callable workflows for microservices.

```yaml
# .github/workflows/reusable-service-build.yml
name: Reusable Service Build

on:
  workflow_call:
    inputs:
      service-name:
        required: true
        type: string
      node-version:
        required: false
        type: string
        default: "20"
      run-e2e:
        required: false
        type: boolean
        default: false
    secrets:
      SONAR_TOKEN:
        required: true

jobs:
  build-test:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: services/${{ inputs.service-name }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: ${{ inputs.node-version }}
          cache: npm
          cache-dependency-path: services/${{ inputs.service-name }}/package-lock.json
      - run: npm ci
      - run: npm run test:unit
      - if: inputs.run-e2e
        run: npm run test:integration
      - run: npm run build
```

Caller workflow:

```yaml
jobs:
  auth-service:
    uses: ./.github/workflows/reusable-service-build.yml
    with:
      service-name: auth-service
      run-e2e: true
    secrets:
      SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}

  payment-service:
    uses: ./.github/workflows/reusable-service-build.yml
    with:
      service-name: payment-service
    secrets:
      SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}
```

## Matrix Testing

Test across multiple OS/runtime combinations in parallel.

```yaml
jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
        node-version: [18, 20, 22]
        exclude:
          - os: macos-latest
            node-version: 18
      fail-fast: false
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: ${{ matrix.node-version }}
      - run: npm ci
      - run: npm test
      - uses: codecov/codecov-action@v3
        with:
          flags: ${{ matrix.os }}-node${{ matrix.node-version }}
```

## Monorepo with Path Filters

Detect changed services and only build what changed.

```yaml
jobs:
  detect-changes:
    runs-on: ubuntu-latest
    outputs:
      frontend: ${{ steps.filter.outputs.frontend }}
      backend: ${{ steps.filter.outputs.backend }}
    steps:
      - uses: actions/checkout@v4
      - uses: dorny/paths-filter@v3
        id: filter
        with:
          filters: |
            frontend:
              - 'src/frontend/**'
            backend:
              - 'src/backend/**'

  build-frontend:
    needs: detect-changes
    if: needs.detect-changes.outputs.frontend == 'true'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - working-directory: src/frontend
        run: npm ci && npm run build

  build-backend:
    needs: detect-changes
    if: needs.detect-changes.outputs.backend == 'true'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - working-directory: src/backend
        run: npm ci && npm run build
```

## Manual Deployment with Validation

```yaml
on:
  workflow_dispatch:
    inputs:
      environment:
        description: Target environment
        required: true
        type: choice
        options: [staging, production]
      version:
        description: Version to deploy (vX.Y.Z)
        required: true
        type: string

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - name: Validate version format
        run: |
          if [[ ! "${{ inputs.version }}" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
            echo "Invalid version format. Expected: vX.Y.Z"
            exit 1
          fi

  deploy:
    needs: validate
    runs-on: ubuntu-latest
    environment:
      name: ${{ inputs.environment }}
      url: https://${{ inputs.environment }}.example.com
    steps:
      - uses: actions/checkout@v4
        with:
          ref: ${{ inputs.version }}
      - run: >-
          kubectl set image deployment/app
          app=ghcr.io/${{ github.repository }}:${{ inputs.version }}
          --namespace=${{ inputs.environment }}
      - run: >-
          kubectl rollout status deployment/app
          --namespace=${{ inputs.environment }} --timeout=10m
      - run: curl -f https://${{ inputs.environment }}.example.com/health
```

## Self-Hosted Runners

```yaml
jobs:
  build:
    runs-on: [self-hosted, linux, x64, high-memory]
    timeout-minutes: 120
    steps:
      - uses: actions/checkout@v4
      - run: |
          docker build \
            --cache-from ghcr.io/${{ github.repository }}:buildcache \
            --build-arg BUILDKIT_INLINE_CACHE=1 \
            -t app:${{ github.sha }} .
      - run: docker run --rm app:${{ github.sha }} npm test
      - if: always()
        run: docker rmi app:${{ github.sha }} || true
```

## Caching Strategy Summary

| Target        | Cache Key                                                       | Path                   |
| ------------- | --------------------------------------------------------------- | ---------------------- |
| npm deps      | `${{ runner.os }}-npm-${{ hashFiles('**/package-lock.json') }}` | `~/.npm`               |
| Build outputs | `${{ runner.os }}-build-${{ hashFiles('src/**') }}`             | `dist/`, `.next/cache` |
| Docker layers | BuildKit GHA cache                                              | `type=gha`             |
| pip deps      | `${{ runner.os }}-pip-${{ hashFiles('**/requirements*.txt') }}` | `~/.cache/pip`         |

## Validation

```bash
# Validate workflow syntax
actionlint

# Dry run locally
act -n

# Run specific workflow
gh workflow run ci-cd.yml
```
