# GitLab CI Patterns

## Complete Pipeline

Full `.gitlab-ci.yml` with lint, test, build, security, and deploy stages.

```yaml
image: node:20-alpine

variables:
  DOCKER_DRIVER: overlay2
  DOCKER_TLS_CERTDIR: "/certs"
  FF_USE_FASTZIP: "true"

stages:
  - lint
  - test
  - build
  - security
  - deploy

cache:
  key: ${CI_COMMIT_REF_SLUG}
  paths:
    - node_modules/
    - .npm/

lint:
  stage: lint
  script:
    - npm ci --cache .npm
    - npm run lint

test:unit:
  stage: test
  script:
    - npm ci --cache .npm
    - npm test
  coverage: '/Lines\s*:\s*(\d+\.\d+)%/'
  artifacts:
    reports:
      coverage_report:
        coverage_format: cobertura
        path: coverage/cobertura-coverage.xml
    expire_in: 7 days

test:integration:
  stage: test
  services:
    - postgres:16-alpine
  variables:
    POSTGRES_DB: test
    POSTGRES_USER: test
    POSTGRES_PASSWORD: test
    DATABASE_URL: postgresql://test:test@postgres:5432/test
  script:
    - npm ci --cache .npm
    - npm run test:integration

build:
  stage: build
  script:
    - npm ci --cache .npm
    - npm run build
  artifacts:
    paths:
      - dist/
    expire_in: 1 hour

include:
  - template: Security/SAST.gitlab-ci.yml
  - template: Security/Dependency-Scanning.gitlab-ci.yml
  - template: Security/Secret-Detection.gitlab-ci.yml

deploy:staging:
  stage: deploy
  image: bitnami/kubectl:latest
  script:
    - kubectl apply -f k8s/ -n staging
    - kubectl rollout status deployment/app -n staging --timeout=5m
  environment:
    name: staging
    url: https://staging.example.com
  rules:
    - if: $CI_COMMIT_BRANCH == "develop"

deploy:production:
  stage: deploy
  image: bitnami/kubectl:latest
  script:
    - kubectl apply -f k8s/ -n production
    - kubectl rollout status deployment/app -n production --timeout=5m
  environment:
    name: production
    url: https://app.example.com
  when: manual
  rules:
    - if: $CI_COMMIT_BRANCH == "main"
```

## Docker Build and Push

```yaml
build-docker:
  stage: build
  image: docker:24
  services:
    - docker:24-dind
  before_script:
    - docker login -u $CI_REGISTRY_USER -p $CI_REGISTRY_PASSWORD $CI_REGISTRY
  script:
    - >-
      docker build
      --cache-from $CI_REGISTRY_IMAGE:latest
      -t $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA
      -t $CI_REGISTRY_IMAGE:latest .
    - docker push $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA
    - docker push $CI_REGISTRY_IMAGE:latest
  rules:
    - if: $CI_COMMIT_BRANCH == "main"
    - if: $CI_COMMIT_TAG
```

## DAG Pipeline

Use `needs` to create a directed acyclic graph instead of strict stage ordering. Jobs start as soon
as their dependencies finish.

```yaml
stages:
  - prepare
  - test
  - build
  - deploy

install:
  stage: prepare
  script:
    - npm ci
  artifacts:
    paths:
      - node_modules/

lint:
  stage: test
  needs: [install]
  script:
    - npm run lint

unit-test:
  stage: test
  needs: [install]
  script:
    - npm test

integration-test:
  stage: test
  needs: [install]
  script:
    - npm run test:integration

build:
  stage: build
  needs: [lint, unit-test]
  script:
    - npm run build
  artifacts:
    paths:
      - dist/

deploy:
  stage: deploy
  needs: [build, integration-test]
  script:
    - kubectl apply -f k8s/
```

## Parent-Child Pipelines

Split large pipelines into smaller, independently managed child pipelines.

```yaml
# .gitlab-ci.yml (parent)
stages:
  - triggers

trigger-backend:
  stage: triggers
  trigger:
    include: backend/.gitlab-ci.yml
    strategy: depend
  rules:
    - changes: [backend/**]

trigger-frontend:
  stage: triggers
  trigger:
    include: frontend/.gitlab-ci.yml
    strategy: depend
  rules:
    - changes: [frontend/**]
```

```yaml
# backend/.gitlab-ci.yml (child)
stages:
  - test
  - build

test:
  stage: test
  image: python:3.12
  script:
    - pip install -r requirements.txt
    - pytest

build:
  stage: build
  script:
    - docker build -t backend .
```

## Dynamic Child Pipelines

Generate pipeline configuration at runtime.

```yaml
generate-pipeline:
  stage: build
  script:
    - python scripts/generate_pipeline.py > child-pipeline.yml
  artifacts:
    paths:
      - child-pipeline.yml

trigger-child:
  stage: deploy
  trigger:
    include:
      - artifact: child-pipeline.yml
        job: generate-pipeline
    strategy: depend
```

## Multi-Project Pipeline

Trigger pipelines in dependent repositories.

```yaml
deploy-infrastructure:
  stage: deploy
  trigger:
    project: team/infrastructure
    branch: main
    strategy: depend
  variables:
    APP_VERSION: $CI_COMMIT_SHA
```

## Job Templates with extends

```yaml
.test_template:
  stage: test
  before_script:
    - npm ci --cache .npm
  cache:
    key: ${CI_COMMIT_REF_SLUG}
    paths: [node_modules/]

unit-test:
  extends: .test_template
  script:
    - npm test

lint:
  extends: .test_template
  script:
    - npm run lint
```

## Merge Request Pipelines

Run lighter pipelines on merge requests, full pipelines on target branches.

```yaml
workflow:
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
    - if: $CI_COMMIT_BRANCH == "main"
    - if: $CI_COMMIT_BRANCH == "develop"

test:
  stage: test
  script:
    - npm test
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
    - if: $CI_COMMIT_BRANCH == "main"

deploy:
  stage: deploy
  script:
    - kubectl apply -f k8s/
  rules:
    - if: $CI_COMMIT_BRANCH == "main"
```

## Review Apps

Deploy per-merge-request environments with automatic cleanup.

```yaml
deploy-review:
  stage: deploy
  script:
    - kubectl create namespace review-$CI_MERGE_REQUEST_IID || true
    - helm upgrade --install review-$CI_MERGE_REQUEST_IID ./chart
      --namespace review-$CI_MERGE_REQUEST_IID
      --set image.tag=$CI_COMMIT_SHA
  environment:
    name: review/$CI_MERGE_REQUEST_IID
    url: https://review-$CI_MERGE_REQUEST_IID.example.com
    on_stop: stop-review
    auto_stop_in: 1 week
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"

stop-review:
  stage: deploy
  script:
    - helm uninstall review-$CI_MERGE_REQUEST_IID
      --namespace review-$CI_MERGE_REQUEST_IID
    - kubectl delete namespace review-$CI_MERGE_REQUEST_IID
  environment:
    name: review/$CI_MERGE_REQUEST_IID
    action: stop
  when: manual
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
      when: manual
```

## Caching Strategies

```yaml
# Per-branch cache
cache:
  key: ${CI_COMMIT_REF_SLUG}
  paths:
    - node_modules/

# Per-job cache
job1:
  cache:
    key: job1-${CI_COMMIT_REF_SLUG}
    paths: [build/]

# Pull-only cache (read from cache, don't update)
test:
  cache:
    key: ${CI_COMMIT_REF_SLUG}
    paths: [node_modules/]
    policy: pull

# Fallback keys
cache:
  key: ${CI_COMMIT_REF_SLUG}
  paths: [node_modules/]
  fallback_keys:
    - main
```

## Runner Configuration

Register a GitLab Runner with Docker executor:

```bash
gitlab-runner register \
  --non-interactive \
  --url "https://gitlab.example.com/" \
  --registration-token "$REGISTRATION_TOKEN" \
  --executor docker \
  --docker-image "alpine:latest" \
  --docker-privileged \
  --docker-volumes "/certs/client"
```

Runner `config.toml` tuning:

```toml
concurrent = 10

[[runners]]
  name = "docker-runner"
  executor = "docker"
  [runners.docker]
    image = "alpine:latest"
    privileged = true
    volumes = ["/cache", "/certs/client:ro"]
    pull_policy = ["if-not-present"]
    shm_size = 268435456
  [runners.cache]
    Type = "s3"
    Shared = true
    [runners.cache.s3]
      BucketName = "gitlab-runner-cache"
      BucketLocation = "us-east-1"
```

## Validation

```bash
# Lint .gitlab-ci.yml locally
gitlab-ci-lint .gitlab-ci.yml

# Via API
curl --header "PRIVATE-TOKEN: $TOKEN" \
  --data-urlencode "content=$(cat .gitlab-ci.yml)" \
  "https://gitlab.example.com/api/v4/ci/lint"

# glab CLI
glab ci lint
```
