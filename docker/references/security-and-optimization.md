# Security and Optimization

## Image Size Reduction

### Clean up in the same layer

A later `RUN rm` does not shrink earlier layers. Always clean up in the same `RUN` instruction that
installs packages.

```dockerfile
# Correct — single layer
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Wrong — cleanup in separate layer has no size effect
RUN apt-get update && apt-get install -y build-essential
RUN rm -rf /var/lib/apt/lists/*
```

### Alpine package management

```dockerfile
RUN apk add --no-cache curl git
```

The `--no-cache` flag avoids storing the package index, eliminating the need for a separate cleanup
step.

### Combine RUN commands

```dockerfile
# Fewer layers, smaller image
RUN npm ci --production && \
    npm cache clean --force && \
    rm -rf /tmp/*
```

### Copy only what is needed

In multi-stage builds, copy specific directories rather than everything:

```dockerfile
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./
```

### Image size comparison

| Strategy                     | Typical Reduction |
| ---------------------------- | ----------------- |
| Multi-stage build            | 50–85%            |
| Alpine base instead of full  | 70–90%            |
| Distroless instead of Alpine | 10–30%            |
| Pruning dev dependencies     | 20–50%            |
| `.dockerignore`              | Faster builds     |

## Distroless Images

Distroless images contain only the application runtime — no shell, package manager, or OS utilities.
This minimizes the attack surface.

### Node.js

```dockerfile
FROM gcr.io/distroless/nodejs22-debian12
COPY --from=builder /app/dist /app/dist
COPY --from=builder /app/node_modules /app/node_modules
WORKDIR /app
EXPOSE 3000
CMD ["dist/index.js"]
```

### Go (static binary)

```dockerfile
FROM gcr.io/distroless/static-debian12
COPY --from=builder /app/server /server
EXPOSE 8080
ENTRYPOINT ["/server"]
```

### Java

```dockerfile
FROM gcr.io/distroless/java21-debian12
COPY --from=builder /app/build/libs/app.jar /app.jar
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "/app.jar"]
```

Trade-off: distroless images have no shell, so debugging requires attaching a debug sidecar or using
`docker debug` (Docker Desktop). Prefer Alpine for development and distroless for production when
maximum security matters.

## Build-Time Secrets

Use BuildKit secrets to pass sensitive data during build without baking it into image layers.

```dockerfile
# syntax=docker/dockerfile:1
FROM node:22-alpine
WORKDIR /app

COPY package.json package-lock.json ./

# Mount secret at build time — never stored in a layer
RUN --mount=type=secret,id=npm_token \
    NPM_TOKEN=$(cat /run/secrets/npm_token) \
    npm ci

COPY . .
RUN npm run build
```

Build command:

```bash
DOCKER_BUILDKIT=1 docker build \
  --secret id=npm_token,src=./.npm_token \
  -t myapp .
```

For SSH keys (e.g., private Git repos):

```dockerfile
RUN --mount=type=ssh git clone git@github.com:org/private-repo.git
```

```bash
docker build --ssh default -t myapp .
```

## Runtime Security

### Drop all capabilities

```yaml
services:
  app:
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE    # only if binding port < 1024
    security_opt:
      - no-new-privileges:true
```

### Read-only root filesystem

```yaml
services:
  app:
    read_only: true
    tmpfs:
      - /tmp
      - /var/run
    volumes:
      - app-data:/data      # writable mount for persistent data
```

### Resource limits

```yaml
services:
  app:
    deploy:
      resources:
        limits:
          cpus: "0.5"
          memory: 512M
        reservations:
          cpus: "0.25"
          memory: 256M
    pids_limit: 100
```

### OCI labels

```dockerfile
LABEL org.opencontainers.image.source="https://github.com/org/repo"
LABEL org.opencontainers.image.description="Application description"
LABEL org.opencontainers.image.version="1.0.0"
LABEL org.opencontainers.image.licenses="MIT"
```

## Vulnerability Scanning

Scan images as part of the CI pipeline, not just locally.

### Docker Scout

```bash
docker scout cves my-image:latest
docker scout quickview my-image:latest
docker scout recommendations my-image:latest
```

### Trivy

```bash
# Scan local image
trivy image my-image:latest

# Scan and fail on HIGH/CRITICAL
trivy image --severity HIGH,CRITICAL --exit-code 1 my-image:latest

# Scan Dockerfile for misconfigurations
trivy config Dockerfile
```

### Grype

```bash
grype my-image:latest
grype my-image:latest --fail-on high
```

### CI integration (GitHub Actions)

```yaml
- name: Scan image
  uses: aquasecurity/trivy-action@master
  with:
    image-ref: my-image:${{ github.sha }}
    severity: HIGH,CRITICAL
    exit-code: "1"
```

## Signal Handling

Containers receive `SIGTERM` on `docker stop`. The application must handle it for graceful shutdown
(close connections, flush buffers, complete in-flight requests).

### Problem: shell form does not forward signals

```dockerfile
# Shell form — runs as /bin/sh -c "node ..." — PID 1 is sh, not node
CMD node server.js
```

### Solution: exec form

```dockerfile
# Exec form — node is PID 1, receives signals directly
CMD ["node", "server.js"]
```

### Alternative: use an init process

For applications that spawn child processes, use a lightweight init like `dumb-init` or `tini` to
reap zombies and forward signals.

```dockerfile
RUN apk add --no-cache dumb-init
ENTRYPOINT ["dumb-init", "--"]
CMD ["node", "server.js"]
```

Or use Docker's built-in init:

```bash
docker run --init my-image
```

```yaml
# compose.yaml
services:
  app:
    init: true
```

## CI/CD Integration

### GitHub Actions

```yaml
name: Docker Build

on:
  push:
    branches: [main]
    tags: ["v*"]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: docker/setup-buildx-action@v3

      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - uses: docker/build-push-action@v6
        with:
          context: .
          push: true
          tags: |
            ghcr.io/${{ github.repository }}:${{ github.sha }}
            ghcr.io/${{ github.repository }}:latest
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

### Multi-platform builds

```bash
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --tag my-image:latest \
  --push .
```

### Registry tagging strategy

| Tag Pattern      | Use Case                    |
| ---------------- | --------------------------- |
| `git-sha`        | Immutable, traceable        |
| `v1.2.3`         | Semantic version releases   |
| `latest`         | Most recent build (mutable) |
| `main`, `staging`| Branch-based deployments    |

## Docker Commands Reference

### Build

```bash
docker build -t myapp:latest .
docker build -t myapp:latest --no-cache .
docker build -t myapp:latest --target production .
docker build --build-arg NODE_ENV=production -t myapp .
```

### Run

```bash
docker run -d -p 3000:3000 --name myapp myapp:latest
docker run --rm -it myapp:latest sh          # interactive shell
docker run --env-file .env myapp:latest      # load env vars
docker run --init myapp:latest               # use init process
```

### Inspect

```bash
docker logs -f myapp                  # follow logs
docker exec -it myapp sh             # shell into running container
docker inspect myapp                  # full container metadata
docker stats                          # live resource usage
docker history myapp:latest           # layer history and sizes
```

### Clean up

```bash
docker system prune -a                # remove all unused data
docker image prune -a                 # remove dangling images
docker volume prune                   # remove unused volumes
docker container prune                # remove stopped containers
```
