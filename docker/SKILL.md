---
name: docker
description: >-
  Containerize applications with Docker using multi-stage builds, security hardening, layer caching,
  image optimization, health checks, and Docker Compose orchestration. Use when creating
  Dockerfiles, optimizing container images, setting up Docker Compose services, containerizing any
  application (Node.js, Python, Go, Rust, Java), reducing image size, hardening container security,
  or configuring multi-container environments.
---

# Docker

## When to Use

- Creating or optimizing Dockerfiles for any language or framework
- Building multi-stage Docker images for production
- Setting up Docker Compose for multi-container applications
- Hardening container security (non-root users, minimal images, secrets)
- Reducing image size or improving build cache efficiency
- Configuring health checks, networking, or volume management
- Creating development environments with hot reload

## Related Skills

- **kubernetes** — load when deploying containers to Kubernetes clusters
- **helm** — load when packaging Docker-based apps as Helm charts

## Core Workflow

1. **Choose a base image** — match language/framework, prefer minimal variants
2. **Write a multi-stage Dockerfile** — separate build and runtime stages
3. **Optimize layer caching** — order instructions from least to most frequently changing
4. **Harden security** — non-root user, minimal capabilities, no secrets in image
5. **Add health checks** — appropriate for the application type
6. **Create `.dockerignore`** — exclude build artifacts, VCS, IDE files
7. **Compose services** — if multi-container, define in `compose.yaml`
8. **Validate** — build, scan, verify health

## Base Image Selection

Pick the smallest image that supports the application's runtime needs.

| Base Type     | Size       | Use Case                        |
| ------------- | ---------- | ------------------------------- |
| Full (Debian) | ~1 GB      | Development, debugging only     |
| `-slim`       | ~200 MB    | General production              |
| `-alpine`     | ~50–130 MB | Size-critical, compatible apps  |
| Distroless    | ~20–120 MB | Maximum security, no shell      |
| `scratch`     | 0 MB       | Statically linked binaries (Go) |

### Recommended base images by language

```dockerfile
# Node.js
FROM node:22-alpine

# Python
FROM python:3.13-slim

# Go
FROM golang:1.24-alpine AS builder
FROM scratch AS runtime

# Rust
FROM rust:1.86-alpine AS builder
FROM alpine:3.21 AS runtime

# Java
FROM eclipse-temurin:21-jdk-alpine AS builder
FROM eclipse-temurin:21-jre-alpine AS runtime
```

## Multi-Stage Builds

Separate dependency installation, compilation, and runtime into distinct stages. Copy only the
artifacts needed to run the application into the final stage.

### Node.js

```dockerfile
# ── Build ──
FROM node:22-alpine AS builder
WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci --ignore-scripts

COPY . .
RUN npm run build && npm prune --production

# ── Runtime ──
FROM node:22-alpine
RUN addgroup -g 1001 -S nodejs && adduser -S appuser -u 1001
WORKDIR /app

COPY --from=builder --chown=appuser:nodejs /app/node_modules ./node_modules
COPY --from=builder --chown=appuser:nodejs /app/dist ./dist
COPY --from=builder --chown=appuser:nodejs /app/package.json ./

USER appuser
EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD node -e "require('http').get('http://localhost:3000/health', r => \
    process.exit(r.statusCode === 200 ? 0 : 1))"

CMD ["node", "dist/index.js"]
```

### Python

```dockerfile
# ── Build ──
FROM python:3.13-slim AS builder
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Runtime ──
FROM python:3.13-slim
WORKDIR /app

RUN groupadd -r appgroup && useradd -r -g appgroup appuser

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY --chown=appuser:appgroup . .
USER appuser
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD python -c "import urllib.request; \
    urllib.request.urlopen('http://localhost:8000/health')"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Go

```dockerfile
# ── Build ──
FROM golang:1.24-alpine AS builder
RUN apk add --no-cache git ca-certificates tzdata
WORKDIR /app

COPY go.mod go.sum ./
RUN go mod download && go mod verify

COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build \
    -ldflags="-w -s" -o /app/server ./cmd/server

# ── Runtime ──
FROM scratch
COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/
COPY --from=builder /usr/share/zoneinfo /usr/share/zoneinfo
COPY --from=builder /app/server /server

EXPOSE 8080
ENTRYPOINT ["/server"]
```

### Rust

```dockerfile
# ── Build ──
FROM rust:1.86-alpine AS builder
RUN apk add --no-cache musl-dev
WORKDIR /app

COPY Cargo.toml Cargo.lock ./
RUN mkdir src && echo "fn main() {}" > src/main.rs && \
    cargo build --release && rm -rf src

COPY . .
RUN touch src/main.rs && cargo build --release

# ── Runtime ──
FROM alpine:3.21
RUN addgroup -S appgroup && adduser -S appuser -G appgroup
COPY --from=builder /app/target/release/app /usr/local/bin/app

USER appuser
EXPOSE 8080
CMD ["app"]
```

## Layer Caching

Order Dockerfile instructions from least to most frequently changing to maximize cache hits.
Dependency files (lockfiles) change less often than source code.

```dockerfile
# 1. System deps     (rarely change)
RUN apk add --no-cache dumb-init

# 2. Create user      (rarely changes)
RUN adduser -D appuser

# 3. Dependency files  (change occasionally)
COPY package.json package-lock.json ./

# 4. Install deps      (cached if lockfile unchanged)
RUN npm ci --production

# 5. Source code        (changes frequently)
COPY --chown=appuser:appuser . .
```

Combine related `RUN` commands with `&&` to reduce layers. Clean up caches in the same layer that
creates them — a later `RUN rm` does not shrink earlier layers.

```dockerfile
# Install and clean in one layer
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*
```

## Security Hardening

### Non-root user

Create a dedicated user with explicit UID/GID. Switch with `USER` before `CMD`.

```dockerfile
# Alpine
RUN addgroup -g 1001 -S appgroup && \
    adduser -S appuser -u 1001 -G appgroup

# Debian/Ubuntu
RUN groupadd -r appgroup && useradd -r -g appgroup -u 1001 appuser
```

### Minimal capabilities

```yaml
# compose.yaml
services:
  app:
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE   # only if binding port < 1024
    security_opt:
      - no-new-privileges:true
    read_only: true
    tmpfs:
      - /tmp
      - /var/run
```

### Secrets

Never bake secrets into images via `ENV`, `ARG`, or `COPY`. Use:

- **Build-time:** `docker build --secret id=mysecret,src=./secret.txt` with `RUN
  --mount=type=secret,id=mysecret cat /run/secrets/mysecret`
- **Runtime:** Docker secrets, mounted env files, or a secrets manager

### Vulnerability scanning

```bash
# Docker Scout
docker scout cves my-image:latest

# Trivy
trivy image my-image:latest
```

## Health Checks

Match the health check to the runtime — avoid installing `curl` just for health checks.

```dockerfile
# Node.js (no curl needed)
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD node -e "require('http').get('http://localhost:3000/health', r => \
    process.exit(r.statusCode === 200 ? 0 : 1))"

# Python
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD python -c "import urllib.request; \
    urllib.request.urlopen('http://localhost:8000/health')"

# Alpine (wget available by default)
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:3000/health
```

### Compose health checks

```yaml
services:
  postgres:
    image: postgres:17-alpine
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s

  redis:
    image: redis:7-alpine
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 5
```

## .dockerignore

Exclude everything unnecessary from the build context to speed up builds and prevent leaking secrets
or bloating the image.

```dockerignore
# VCS
.git
.gitignore

# Dependencies (reinstalled in container)
node_modules
.pnpm-store
__pycache__
*.egg-info

# Build outputs
dist
build
.next
out
target

# Environment / secrets
.env*
*.pem
*.key

# IDE / editor
.idea
.vscode
*.swp

# Docker files (not needed inside image)
Dockerfile*
docker-compose*
compose.yaml
compose.override.yaml

# Docs / tests (unless needed at runtime)
*.md
docs
tests
coverage
.pytest_cache
```

## Docker Compose Essentials

Use `compose.yaml` (the modern default filename) with override files for environment-specific
configuration.

```yaml
# compose.yaml — shared base
services:
  app:
    build:
      context: .
      target: production
    depends_on:
      db:
        condition: service_healthy
    networks:
      - backend
    deploy:
      resources:
        limits:
          cpus: "0.5"
          memory: 512M

  db:
    image: postgres:17-alpine
    volumes:
      - postgres-data:/var/lib/postgresql/data
    networks:
      - backend
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

networks:
  backend:

volumes:
  postgres-data:
```

```yaml
# compose.override.yaml — auto-merged in development
services:
  app:
    build:
      target: development
    volumes:
      - ./src:/app/src
      - /app/node_modules
    ports:
      - "3000:3000"
      - "9229:9229"
    environment:
      - NODE_ENV=development
    command: npm run dev

  db:
    ports:
      - "5432:5432"
    environment:
      - POSTGRES_PASSWORD=dev
```

### Key commands

```bash
docker compose up -d              # start (reads compose.yaml + override)
docker compose -f compose.yaml \
  -f compose.prod.yaml up -d     # production (explicit override)
docker compose logs -f app        # follow logs
docker compose down               # stop and remove containers
docker compose build --no-cache   # rebuild from scratch
```

## Reference Guides

Load on demand — do not read all files upfront.

| Topic                   | File                                      | Load When                                            |
| ----------------------- | ----------------------------------------- | ---------------------------------------------------- |
| Compose patterns        | `references/compose-patterns.md`          | Multi-container apps, networking, volumes, overrides |
| Language Dockerfiles    | `references/language-dockerfiles.md`      | Next.js, Java, or additional framework templates     |
| Security & optimization | `references/security-and-optimization.md` | Image scanning, CI/CD, distroless, size reduction    |

## Constraints

### Do

- Use multi-stage builds — separate build tools from runtime
- Pin exact base image versions (e.g., `node:22.15-alpine3.21`, not `:latest`)
- Run as non-root with explicit UID/GID
- Include a health check matching the application's runtime
- Create a `.dockerignore` to minimize build context
- Install dependencies before copying source code (cache optimization)
- Clean up package manager caches in the same `RUN` layer
- Use `--no-install-recommends` (apt) or `--no-cache` (apk) to minimize size
- Set `WORKDIR` before `COPY` and `RUN` instructions

### Do Not

- Use `:latest` tags in production images
- Run containers as root without documented justification
- Store secrets in `ENV`, `ARG`, `COPY`, or image layers
- Install unnecessary packages in the runtime stage
- Create separate `RUN` layers for install and cleanup (cleanup has no effect)
- Include development dependencies, test files, or docs in production images
- Skip health checks in orchestrated environments (Compose, Kubernetes)
