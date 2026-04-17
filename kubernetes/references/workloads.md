# Kubernetes Workloads

## Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
  namespace: production
  labels:
    app.kubernetes.io/name: web-app
    app.kubernetes.io/version: "1.2.0"
spec:
  replicas: 3
  revisionHistoryLimit: 10
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  selector:
    matchLabels:
      app.kubernetes.io/name: web-app
  template:
    metadata:
      labels:
        app.kubernetes.io/name: web-app
        app.kubernetes.io/version: "1.2.0"
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8080"
    spec:
      serviceAccountName: web-app-sa
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        fsGroup: 2000
      containers:
        - name: app
          image: myregistry.io/web-app:v1.2.0
          imagePullPolicy: IfNotPresent
          ports:
            - name: http
              containerPort: 8080
          env:
            - name: DB_HOST
              valueFrom:
                configMapKeyRef:
                  name: app-config
                  key: database.host
            - name: DB_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: app-secrets
                  key: db-password
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
            limits:
              cpu: 500m
              memory: 512Mi
          livenessProbe:
            httpGet:
              path: /health
              port: http
            initialDelaySeconds: 30
            periodSeconds: 10
            timeoutSeconds: 5
            failureThreshold: 3
          readinessProbe:
            httpGet:
              path: /ready
              port: http
            initialDelaySeconds: 10
            periodSeconds: 5
            timeoutSeconds: 3
            failureThreshold: 2
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities:
              drop: ["ALL"]
          volumeMounts:
            - name: config
              mountPath: /etc/config
              readOnly: true
            - name: cache
              mountPath: /var/cache
      volumes:
        - name: config
          configMap:
            name: app-config
        - name: cache
          emptyDir: {}
```

## StatefulSet

Use for workloads needing stable network identity and persistent storage (databases, caches).

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
  namespace: database
spec:
  serviceName: postgres-headless
  replicas: 3
  podManagementPolicy: OrderedReady
  updateStrategy:
    type: RollingUpdate
  selector:
    matchLabels:
      app.kubernetes.io/name: postgres
  template:
    metadata:
      labels:
        app.kubernetes.io/name: postgres
    spec:
      serviceAccountName: postgres-sa
      securityContext:
        runAsUser: 999
        fsGroup: 999
      containers:
        - name: postgres
          image: postgres:15-alpine
          ports:
            - name: postgres
              containerPort: 5432
          env:
            - name: POSTGRES_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: postgres-secrets
                  key: password
            - name: PGDATA
              value: /var/lib/postgresql/data/pgdata
          resources:
            requests:
              cpu: 500m
              memory: 1Gi
            limits:
              cpu: 2000m
              memory: 4Gi
          livenessProbe:
            exec:
              command: ["pg_isready", "-U", "postgres"]
            initialDelaySeconds: 30
            periodSeconds: 10
          readinessProbe:
            exec:
              command: ["pg_isready", "-U", "postgres"]
            initialDelaySeconds: 10
            periodSeconds: 5
          volumeMounts:
            - name: data
              mountPath: /var/lib/postgresql/data
  volumeClaimTemplates:
    - metadata:
        name: data
      spec:
        accessModes: ["ReadWriteOnce"]
        storageClassName: fast-ssd
        resources:
          requests:
            storage: 50Gi
```

Requires a headless Service:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: postgres-headless
  namespace: database
spec:
  clusterIP: None
  selector:
    app.kubernetes.io/name: postgres
  ports:
    - name: postgres
      port: 5432
      targetPort: 5432
```

## DaemonSet

Runs one pod per node — use for log collectors, monitoring agents, node-level services.

```yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: node-exporter
  namespace: monitoring
spec:
  selector:
    matchLabels:
      app.kubernetes.io/name: node-exporter
  updateStrategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 1
  template:
    metadata:
      labels:
        app.kubernetes.io/name: node-exporter
    spec:
      hostNetwork: true
      hostPID: true
      serviceAccountName: node-exporter-sa
      tolerations:
        - effect: NoSchedule
          operator: Exists
      containers:
        - name: node-exporter
          image: prom/node-exporter:v1.7.0
          args:
            - --path.procfs=/host/proc
            - --path.sysfs=/host/sys
          ports:
            - name: metrics
              containerPort: 9100
          resources:
            requests:
              cpu: 50m
              memory: 64Mi
            limits:
              cpu: 200m
              memory: 128Mi
          volumeMounts:
            - name: proc
              mountPath: /host/proc
              readOnly: true
            - name: sys
              mountPath: /host/sys
              readOnly: true
      volumes:
        - name: proc
          hostPath:
            path: /proc
        - name: sys
          hostPath:
            path: /sys
```

## Job

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: db-migration
  namespace: production
spec:
  backoffLimit: 3
  ttlSecondsAfterFinished: 3600
  template:
    metadata:
      labels:
        app.kubernetes.io/name: db-migration
    spec:
      restartPolicy: OnFailure
      serviceAccountName: migration-sa
      containers:
        - name: migrate
          image: myregistry.io/migrations:v1.2.0
          command: ["/app/migrate", "up"]
          env:
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: db-secrets
                  key: connection-string
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
            limits:
              cpu: 500m
              memory: 512Mi
```

## CronJob

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: backup-database
  namespace: production
spec:
  schedule: "0 2 * * *"
  timeZone: "America/New_York"
  successfulJobsHistoryLimit: 3
  failedJobsHistoryLimit: 1
  concurrencyPolicy: Forbid
  jobTemplate:
    spec:
      backoffLimit: 2
      ttlSecondsAfterFinished: 86400
      template:
        metadata:
          labels:
            app.kubernetes.io/name: backup
        spec:
          restartPolicy: OnFailure
          serviceAccountName: backup-sa
          containers:
            - name: backup
              image: myregistry.io/backup-tool:v2.0.0
              command: ["/usr/local/bin/backup.sh"]
              env:
                - name: S3_BUCKET
                  valueFrom:
                    configMapKeyRef:
                      name: backup-config
                      key: s3-bucket
                - name: AWS_ACCESS_KEY_ID
                  valueFrom:
                    secretKeyRef:
                      name: backup-secrets
                      key: aws-access-key
              resources:
                requests:
                  cpu: 200m
                  memory: 256Mi
                limits:
                  cpu: 1000m
                  memory: 1Gi
```

## Init Containers

```yaml
spec:
  initContainers:
    - name: wait-for-db
      image: busybox:1.36
      command: ["sh", "-c"]
      args:
        - |
          until nc -z postgres-service 5432; do
            echo "Waiting for database..."
            sleep 2
          done
    - name: migrate-schema
      image: myregistry.io/migrations:v1.0.0
      command: ["/app/migrate", "up"]
      env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-secrets
              key: url
  containers:
    - name: app
      image: myregistry.io/app:v1.0.0
```

## HorizontalPodAutoscaler

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: web-app
  namespace: production
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: web-app
  minReplicas: 3
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
```

## Best Practices

1. **Resource management** — always set requests and limits
2. **Health checks** — include both liveness and readiness probes
3. **Security** — non-root users, read-only filesystems
4. **Labels** — consistent `app.kubernetes.io/*` labeling
5. **Update strategy** — RollingUpdate with `maxUnavailable: 0` for zero downtime
6. **Service accounts** — dedicated per workload, never use `default`
7. **Image tags** — specific versions, never `:latest` in production
8. **Cleanup** — set `ttlSecondsAfterFinished` on Jobs

## Startup, Lifecycle, and Topology

### startupProbe

Use for slow-starting containers. Disables liveness/readiness until the startup probe succeeds:

```yaml
startupProbe:
  httpGet:
    path: /healthz
    port: http
  failureThreshold: 30
  periodSeconds: 10
  # Allows up to 300s (30 × 10) for startup
```

### lifecycle.preStop

Graceful shutdown hook — runs before SIGTERM. Keeps the pod in the Service endpoints long enough for
in-flight requests to drain:

```yaml
lifecycle:
  preStop:
    exec:
      command: ["/bin/sh", "-c", "sleep 15"]
terminationGracePeriodSeconds: 30
```

### topologySpreadConstraints

Spread pods evenly across zones or nodes:

```yaml
topologySpreadConstraints:
  - maxSkew: 1
    topologyKey: topology.kubernetes.io/zone
    whenUnsatisfiable: DoNotSchedule
    labelSelector:
      matchLabels:
        app.kubernetes.io/name: web-app
  - maxSkew: 1
    topologyKey: kubernetes.io/hostname
    whenUnsatisfiable: ScheduleAnyway
    labelSelector:
      matchLabels:
        app.kubernetes.io/name: web-app
```

## QoS Classes

Kubernetes assigns a QoS class to each pod based on resource configuration. This determines eviction
priority under node pressure:

| QoS Class  | Criteria                                      | Eviction Order |
| ---------- | --------------------------------------------- | -------------- |
| Guaranteed | Every container has equal requests and limits | Last (safest)  |
| Burstable  | At least one container has requests < limits  | Middle         |
| BestEffort | No requests or limits set                     | First (risky)  |

```yaml
# Guaranteed — requests == limits
resources:
  requests:
    cpu: 500m
    memory: 256Mi
  limits:
    cpu: 500m
    memory: 256Mi
```
