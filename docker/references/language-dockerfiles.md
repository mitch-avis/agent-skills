# Language Dockerfiles

Complete multi-stage Dockerfile templates for specific frameworks. Each template includes build
optimization, security hardening, and health checks.

## Next.js

Uses standalone output mode for minimal production images.

```dockerfile
# ── Dependencies ──
FROM node:24-alpine AS deps
RUN apk add --no-cache libc6-compat
WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

# ── Build ──
FROM node:24-alpine AS builder
WORKDIR /app

COPY --from=deps /app/node_modules ./node_modules
COPY . .

ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

# ── Runtime ──
FROM node:24-alpine
WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public
RUN mkdir .next && chown nextjs:nodejs .next

COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs
EXPOSE 3000
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:3000/ || exit 1

CMD ["node", "server.js"]
```

Enable standalone mode in `next.config.js`:

```javascript
module.exports = { output: "standalone" };
```

## Java (Spring Boot)

```dockerfile
# ── Build ──
FROM eclipse-temurin:25-jdk-alpine AS builder
WORKDIR /app

COPY gradle/ gradle/
COPY gradlew build.gradle.kts settings.gradle.kts ./
RUN ./gradlew dependencies --no-daemon

COPY src ./src
RUN ./gradlew bootJar --no-daemon -x test

# ── Runtime ──
FROM eclipse-temurin:25-jre-alpine
WORKDIR /app

RUN addgroup -S appgroup && adduser -S appuser -G appgroup

COPY --from=builder /app/build/libs/*.jar app.jar
RUN chown appuser:appgroup app.jar

USER appuser
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=3s --start-period=30s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:8080/actuator/health || exit 1

ENTRYPOINT ["java", "-jar", "app.jar"]
```

For Maven, replace the Gradle commands:

```dockerfile
COPY pom.xml .
RUN mvn dependency:go-offline -B

COPY src ./src
RUN mvn package -DskipTests -B
```

## Python (FastAPI with uv)

Uses `uv` with the lockfile for reproducible, cached dependency installs.

```dockerfile
# ── Build ──
FROM python:3.14-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:0.12.22 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
WORKDIR /app

# Dependencies first, so this layer is cached until uv.lock changes
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-dev --no-install-project

# Then the project itself, installed into the venv (not editable) so the runtime needs no source
COPY . .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-editable

# ── Runtime ──
FROM python:3.14-slim
RUN groupadd -r appgroup && useradd -r -g appgroup appuser
WORKDIR /app

COPY --from=builder --chown=appuser:appgroup /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

USER appuser
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD python -c "import urllib.request; \
    urllib.request.urlopen('http://localhost:8000/health')"

CMD ["uvicorn", "myapp.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Python (Django)

```dockerfile
# ── Build ──
FROM python:3.14-slim AS builder
WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:0.12.22 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PROJECT_ENVIRONMENT=/opt/venv

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-install-project

# ── Runtime ──
FROM python:3.14-slim
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 && rm -rf /var/lib/apt/lists/*

RUN groupadd -r django && useradd -r -g django django

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY --chown=django:django . .
RUN python manage.py collectstatic --noinput

USER django
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD python -c "import urllib.request; \
    urllib.request.urlopen('http://localhost:8000/health/')"

CMD ["gunicorn", "config.wsgi:application", \
     "--bind", "0.0.0.0:8000", "--workers", "4"]
```

## Go (with CGo disabled)

Produces a statically linked binary that runs from `scratch`.

```dockerfile
# ── Build ──
FROM golang:1.27-alpine AS builder
RUN apk add --no-cache git ca-certificates tzdata
WORKDIR /app

COPY go.mod go.sum ./
RUN go mod download && go mod verify

COPY . .
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build \
    -ldflags="-w -s" -o /app/server ./cmd/server

# ── Runtime ──
FROM scratch

COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/
COPY --from=builder /usr/share/zoneinfo /usr/share/zoneinfo
COPY --from=builder /app/server /server

EXPOSE 8080
ENTRYPOINT ["/server"]
```

## Rust

Uses a dependency-caching trick: build a dummy `main.rs` first so Cargo caches all dependency
compilation. Subsequent builds only recompile the application.

```dockerfile
# ── Build ──
FROM rust:1.98-alpine AS builder
RUN apk add --no-cache musl-dev
WORKDIR /app

# Cache dependencies
COPY Cargo.toml Cargo.lock ./
RUN mkdir src && echo "fn main() {}" > src/main.rs && \
    cargo build --release && rm -rf src

# Build application
COPY . .
RUN touch src/main.rs && cargo build --release

# ── Runtime ──
FROM alpine:3.24
RUN addgroup -S appgroup && adduser -S appuser -G appgroup

COPY --from=builder /app/target/release/myapp /usr/local/bin/myapp
USER appuser

EXPOSE 8080
CMD ["myapp"]
```

## Nginx (Static Assets)

Serve pre-built static files (SPA, docs site) with optimized Nginx configuration.

```dockerfile
# ── Build ──
FROM node:24-alpine AS builder
WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

# ── Runtime ──
FROM nginx:1.29-alpine

RUN rm /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/conf.d/app.conf
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost/ || exit 1
```

Example `nginx.conf`:

```nginx
server {
    listen 80;
    root /usr/share/nginx/html;
    index index.html;

    # Gzip
    gzip on;
    gzip_types text/plain text/css application/json application/javascript
               text/xml application/xml application/xml+rss text/javascript;

    # Cache static assets
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff2?)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # SPA fallback
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
}
```
