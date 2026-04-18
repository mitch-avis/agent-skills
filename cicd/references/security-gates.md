# Security Gates

## OWASP CI/CD Top 10

| Risk        | Category                        | Impact   | Mitigation                                         |
| ----------- | ------------------------------- | -------- | -------------------------------------------------- |
| CICD-SEC-1  | Insufficient Flow Control       | Critical | Branch protection, required reviews, status checks |
| CICD-SEC-2  | Inadequate Identity & Access    | Critical | OIDC, least privilege, short-lived tokens          |
| CICD-SEC-3  | Dependency Chain Abuse          | High     | SCA scanning, dependency pinning, SBOM             |
| CICD-SEC-4  | Poisoned Pipeline Execution     | Critical | Separate build/deploy, validate inputs             |
| CICD-SEC-5  | Insufficient PBAC               | High     | Environment protection, manual approvals           |
| CICD-SEC-6  | Insufficient Credential Hygiene | Critical | Secrets scanning, rotation, vault integration      |
| CICD-SEC-7  | Insecure System Configuration   | High     | Harden runners, network isolation                  |
| CICD-SEC-8  | Ungoverned Usage                | Medium   | Policy as code, compliance gates                   |
| CICD-SEC-9  | Improper Artifact Integrity     | High     | Sign artifacts, verify provenance                  |
| CICD-SEC-10 | Insufficient Logging            | Medium   | Structured logs, audit trails, SIEM integration    |

## SAST Integration

### Semgrep (GitHub Actions)

```yaml
code-quality:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - uses: semgrep/semgrep-action@v1
      with:
        config: >-
          p/security-audit
          p/secrets
          p/owasp-top-ten
```

### CodeQL (GitHub Actions)

```yaml
codeql:
  runs-on: ubuntu-latest
  permissions:
    security-events: write
  steps:
    - uses: actions/checkout@v4
    - uses: github/codeql-action/init@v2
      with:
        languages: javascript
    - uses: github/codeql-action/analyze@v2
```

### GitLab SAST

```yaml
include:
  - template: Security/SAST.gitlab-ci.yml

sast:
  stage: security
  variables:
    SAST_EXCLUDED_ANALYZERS: spotbugs
```

## DAST Integration

### OWASP ZAP (GitHub Actions)

```yaml
dast:
  runs-on: ubuntu-latest
  steps:
    - uses: zaproxy/action-full-scan@v0.10.0
      with:
        target: https://staging.example.com
        rules_file_name: .zap/rules.tsv
        cmd_options: '-a'
```

### GitLab DAST

```yaml
include:
  - template: Security/DAST.gitlab-ci.yml

dast:
  stage: security
  variables:
    DAST_WEBSITE: https://staging.example.com
```

## SCA / Dependency Scanning

### Snyk (GitHub Actions)

```yaml
dependency-check:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - uses: snyk/actions/node@master
      env:
        SNYK_TOKEN: ${{ secrets.SNYK_TOKEN }}
      with:
        args: --severity-threshold=high
```

### Dependency Review (GitHub Actions)

```yaml
- uses: actions/dependency-review-action@v4
  with:
    fail-on-severity: high
    deny-licenses: GPL-3.0
```

### GitLab Dependency Scanning

```yaml
include:
  - template: Security/Dependency-Scanning.gitlab-ci.yml

dependency_scanning:
  stage: security
```

## Container Scanning

### Trivy (GitHub Actions)

```yaml
container-scan:
  runs-on: ubuntu-latest
  steps:
    - uses: aquasecurity/trivy-action@master
      with:
        image-ref: ghcr.io/${{ github.repository }}:${{ github.sha }}
        format: sarif
        output: trivy-results.sarif
        severity: CRITICAL,HIGH
        exit-code: 1
    - uses: github/codeql-action/upload-sarif@v2
      if: always()
      with:
        sarif_file: trivy-results.sarif
```

### Trivy (GitLab CI)

```yaml
trivy-scan:
  stage: security
  image: aquasec/trivy:latest
  script:
    - >-
      trivy image
      --exit-code 1
      --severity HIGH,CRITICAL
      $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA
  allow_failure: false
```

### Grype

```yaml
- uses: anchore/scan-action@v3
  with:
    image: ghcr.io/${{ github.repository }}:${{ github.sha }}
    fail-build: true
    severity-cutoff: high
```

## Secrets Scanning

### Gitleaks (GitHub Actions)

```yaml
secrets-scan:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
      with:
        fetch-depth: 0
    - uses: gitleaks/gitleaks-action@v2
      env:
        GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### GitLab Secret Detection

```yaml
include:
  - template: Security/Secret-Detection.gitlab-ci.yml

secret_detection:
  stage: security
```

## Infrastructure as Code Scanning

### Checkov

```yaml
iac-scan:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - uses: bridgecrewio/checkov-action@master
      with:
        directory: terraform/
        framework: terraform
        soft_fail: false
```

### tfsec

```yaml
- uses: aquasecurity/tfsec-action@v1.0.3
  with:
    working_directory: terraform/
    soft_fail: false
```

## Artifact Signing

### Cosign (Keyless with OIDC)

```yaml
sign:
  runs-on: ubuntu-latest
  permissions:
    packages: write
    id-token: write
  steps:
    - uses: sigstore/cosign-installer@v3
    - run: >-
        cosign sign --yes
        ghcr.io/${{ github.repository }}@${{ needs.build.outputs.digest }}
```

### Verify Signed Image

```bash
cosign verify \
  --certificate-identity=https://github.com/org/repo/.github/workflows/ci.yml@refs/heads/main \
  --certificate-oidc-issuer=https://token.actions.githubusercontent.com \
  ghcr.io/org/repo:latest
```

## SBOM Generation

```yaml
- uses: docker/build-push-action@v5
  with:
    context: .
    push: true
    provenance: true
    sbom: true
    tags: ghcr.io/${{ github.repository }}:${{ github.sha }}
```

## Policy Enforcement with OPA

```yaml
policy-check:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - name: Evaluate OPA policies
      run: |
        opa eval \
          --data policies/ \
          --input pipeline-context.json \
          'data.cicd.allow' \
          --fail-defined
```

## Secrets Management Best Practices

### OIDC Authentication (no static credentials)

```yaml
# GitHub Actions — AWS
- uses: aws-actions/configure-aws-credentials@v4
  with:
    role-to-assume: arn:aws:iam::123456789012:role/GitHubActions
    aws-region: us-east-1

# GitHub Actions — GCP
- uses: google-github-actions/auth@v2
  with:
    workload_identity_provider: projects/123/locations/global/workloadIdentityPools/pool/providers/ghactions
    service_account: deploy@project.iam.gserviceaccount.com

# GitHub Actions — Azure
- uses: azure/login@v2
  with:
    client-id: ${{ secrets.AZURE_CLIENT_ID }}
    tenant-id: ${{ secrets.AZURE_TENANT_ID }}
    subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}
```

### Mask Secrets in Logs

```yaml
- run: |
    echo "::add-mask::${{ secrets.API_KEY }}"
    # Now safe to use in subsequent steps
```

### Environment-Scoped Secrets

```yaml
deploy-prod:
  environment: production
  steps:
    - run: deploy.sh
      env:
        API_KEY: ${{ secrets.PROD_API_KEY }}
```

## Complete Security Pipeline

Combine all scanning stages into a unified gate.

```yaml
name: Security Gate

on: pull_request

permissions:
  contents: read
  security-events: write

jobs:
  sast:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: semgrep/semgrep-action@v1
        with:
          config: p/security-audit

  sca:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/dependency-review-action@v4
        with:
          fail-on-severity: high

  secrets:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

  container:
    needs: [sast, sca, secrets]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: docker/build-push-action@v5
        with:
          context: .
          push: false
          load: true
          tags: app:scan
      - uses: aquasecurity/trivy-action@master
        with:
          image-ref: app:scan
          exit-code: 1
          severity: CRITICAL,HIGH
```
