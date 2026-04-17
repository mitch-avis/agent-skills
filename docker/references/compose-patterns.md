# Compose Patterns

## Table of Contents

- [Full-Stack Web Application](#full-stack-web-application)
- [Microservices with Reverse Proxy](#microservices-with-reverse-proxy)
- [Development with Hot Reload](#development-with-hot-reload)
- [Networking Strategies](#networking-strategies)
- [Volume Management](#volume-management)
- [Health Check Recipes](#health-check-recipes)
- [Environment Overrides](#environment-overrides)

## Full-Stack Web Application

React/Vue frontend + Node.js API + PostgreSQL + Redis.

```yaml
services:
  frontend:
    build:
      context: ./frontend
      target: development
    ports:
      - "3000:3000"
    volumes:
      - ./frontend/src:/app/src
      - /app/node_modules
    environment:
      - VITE_API_URL=http://localhost:4000/api
      - CHOKIDAR_USEPOLLING=true
    networks:
      - frontend
    depends_on:
      - backend

  backend:
    build:
      context: ./backend
    ports:
      - "4000:4000"
      - "9229:9229"
    volumes:
      - ./backend:/app
      - /app/node_modules
    environment:
      - NODE_ENV=development
      - DATABASE_URL=postgresql://postgres:password@db:5432/myapp
      - REDIS_URL=redis://cache:6379
    env_file:
      - ./backend/.env.local
    networks:
      - frontend
      - backend
    depends_on:
      db:
        condition: service_healthy
      cache:
        condition: service_started
    command: npm run dev

  db:
    image: postgres:17-alpine
    restart: unless-stopped
    ports:
      - "5432:5432"
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=myapp
    volumes:
      - postgres-data:/var/lib/postgresql/data
      - ./database/init.sql:/docker-entrypoint-initdb.d/init.sql
    networks:
      - backend
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

  cache:
    image: redis:7-alpine
    restart: unless-stopped
    volumes:
      - redis-data:/data
    networks:
      - backend
    command: redis-server --appendonly yes
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 5

networks:
  frontend:
  backend:

volumes:
  postgres-data:
  redis-data:
```

## Microservices with Reverse Proxy

Multiple services behind an Nginx reverse proxy with isolated internal networking.

```yaml
services:
  proxy:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/conf.d:/etc/nginx/conf.d:ro
    networks:
      - public
    depends_on:
      - auth-service
      - user-service
    restart: unless-stopped

  auth-service:
    build: ./services/auth
    expose:
      - "8001"
    environment:
      - DATABASE_URL=postgresql://db:5432/auth_db
      - JWT_SECRET=${JWT_SECRET}
    networks:
      - public
      - internal
    depends_on:
      db:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "wget", "--spider", "-q", "http://localhost:8001/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  user-service:
    build: ./services/user
    expose:
      - "8002"
    environment:
      - DATABASE_URL=postgresql://db:5432/user_db
      - AUTH_SERVICE_URL=http://auth-service:8001
    networks:
      - public
      - internal
    depends_on:
      - auth-service
      - db

  db:
    image: postgres:17-alpine
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    volumes:
      - postgres-data:/var/lib/postgresql/data
      - ./database/init-multi-db.sql:/docker-entrypoint-initdb.d/init.sql
    networks:
      - internal
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

  rabbitmq:
    image: rabbitmq:4-management-alpine
    ports:
      - "15672:15672"
    environment:
      - RABBITMQ_DEFAULT_USER=admin
      - RABBITMQ_DEFAULT_PASS=${RABBITMQ_PASSWORD}
    volumes:
      - rabbitmq-data:/var/lib/rabbitmq
    networks:
      - internal
    healthcheck:
      test: ["CMD", "rabbitmq-diagnostics", "ping"]
      interval: 30s
      timeout: 10s
      retries: 5

networks:
  public:
  internal:
    internal: true   # no external/internet access

volumes:
  postgres-data:
  rabbitmq-data:
```

## Development with Hot Reload

Development-only services with debugger ports, admin UIs, and live code mounting.

```yaml
services:
  frontend-dev:
    build:
      context: ./frontend
      dockerfile: Dockerfile
      target: development
    ports:
      - "3000:3000"
      - "9222:9222"    # Chrome DevTools
    volumes:
      - ./frontend:/app
      - /app/node_modules
      - /app/.next
    environment:
      - NODE_ENV=development
      - WATCHPACK_POLLING=true
    stdin_open: true
    tty: true
    command: npm run dev

  backend-dev:
    build:
      context: ./backend
      target: development
    ports:
      - "4000:4000"
      - "9229:9229"    # Node.js debugger
    volumes:
      - ./backend:/app
      - /app/node_modules
    environment:
      - NODE_ENV=development
      - DEBUG=app:*
    command: npm run dev:debug
    depends_on:
      - db
      - mailhog

  db:
    image: postgres:17-alpine
    ports:
      - "5432:5432"
    environment:
      - POSTGRES_PASSWORD=dev
      - POSTGRES_DB=dev_db
    volumes:
      - dev-db-data:/var/lib/postgresql/data

  pgadmin:
    image: dpage/pgadmin4:latest
    ports:
      - "5050:80"
    environment:
      - PGADMIN_DEFAULT_EMAIL=admin@dev.local
      - PGADMIN_DEFAULT_PASSWORD=admin
    depends_on:
      - db

  mailhog:
    image: mailhog/mailhog:latest
    ports:
      - "1025:1025"    # SMTP
      - "8025:8025"    # Web UI

volumes:
  dev-db-data:
```

## Networking Strategies

### Service isolation with custom networks

```yaml
services:
  frontend:
    networks:
      - public

  backend:
    networks:
      - public       # reachable from frontend
      - private      # reachable from database

  database:
    networks:
      - private      # isolated from frontend

networks:
  public:
  private:
    internal: true   # no internet access
```

### Network aliases

```yaml
services:
  api:
    networks:
      backend:
        aliases:
          - api-server
          - api.internal

networks:
  backend:
```

### Custom IPAM configuration

```yaml
networks:
  custom:
    driver: bridge
    ipam:
      config:
        - subnet: 172.28.0.0/16
          gateway: 172.28.0.1
```

### Host network mode

Use when the container needs direct access to the host network stack (no port
mapping needed). Primarily useful on Linux.

```yaml
services:
  app:
    network_mode: "host"
```

## Volume Management

### Named volumes

```yaml
services:
  db:
    volumes:
      - postgres-data:/var/lib/postgresql/data

  backup:
    volumes:
      - postgres-data:/backup:ro    # read-only mount

volumes:
  postgres-data:
```

### Bind mounts

```yaml
services:
  web:
    volumes:
      - ./html:/usr/share/nginx/html       # relative path
      - ./config/nginx.conf:/etc/nginx/nginx.conf:ro  # read-only
```

### tmpfs (in-memory)

```yaml
services:
  app:
    tmpfs:
      - /tmp
      - /run
    # Or with size limits:
    volumes:
      - type: tmpfs
        target: /app/cache
        tmpfs:
          size: 100000000   # 100 MB
```

### Advanced volume drivers

```yaml
volumes:
  nfs-data:
    driver: local
    driver_opts:
      type: "nfs"
      o: "addr=10.40.0.199,nolock,soft,rw"
      device: ":/docker/data"

  external-vol:
    external: true
    name: my-existing-volume
```

## Health Check Recipes

### Databases

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

  mysql:
    image: mysql:8
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
      interval: 10s
      timeout: 5s
      retries: 3

  mongodb:
    image: mongo:7
    healthcheck:
      test: ["CMD", "mongosh", "--eval", "db.adminCommand('ping')"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 5
```

### Applications

```yaml
services:
  node-app:
    healthcheck:
      test: ["CMD", "node", "healthcheck.js"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s

  python-app:
    healthcheck:
      test: >-
        CMD-SHELL python -c "import urllib.request;
        urllib.request.urlopen('http://localhost:8000/health')"
      interval: 30s
      timeout: 10s
      retries: 3
```

## Environment Overrides

Use layered Compose files for environment-specific configuration. Docker Compose
auto-merges `compose.yaml` + `compose.override.yaml` in development.

### Production override (`compose.prod.yaml`)

```yaml
services:
  app:
    image: myapp:${VERSION:-latest}
    restart: always
    environment:
      - NODE_ENV=production
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: "2"
          memory: 2G
        reservations:
          cpus: "1"
          memory: 1G
      update_config:
        parallelism: 1
        delay: 10s
        failure_action: rollback
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "5"

  db:
    restart: always
    environment:
      - POSTGRES_PASSWORD_FILE=/run/secrets/db_password
    secrets:
      - db_password
    deploy:
      resources:
        limits:
          cpus: "2"
          memory: 4G

secrets:
  db_password:
    external: true
```

### Usage

```bash
# Development (auto-merges compose.override.yaml)
docker compose up -d

# Production (explicit override)
docker compose -f compose.yaml -f compose.prod.yaml up -d

# Staging
docker compose -f compose.yaml -f compose.staging.yaml up -d
```
