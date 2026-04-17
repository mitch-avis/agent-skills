# Kubernetes Configuration Management

## ConfigMap

### Key-Value and File Data

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
  namespace: production
data:
  database.host: "postgres.database.svc.cluster.local"
  database.port: "5432"

  app.properties: |
    server.port=8080
    logging.level=INFO
    cache.enabled=true

  config.yaml: |
    server:
      port: 8080
      timeout: 30s
    database:
      pool_size: 20
```

### From CLI

```bash
kubectl create configmap app-config \
  --from-literal=database.host=postgres \
  --from-file=nginx.conf \
  --from-file=configs/
```

## Secrets

### Opaque Secret

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: app-secrets
  namespace: production
type: Opaque
stringData:
  db-password: "MySecurePassword123!"
  api-key: "sk-1234567890abcdef"
```

### TLS Secret

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: example-tls
  namespace: production
type: kubernetes.io/tls
stringData:
  tls.crt: |
    -----BEGIN CERTIFICATE-----
    ...
    -----END CERTIFICATE-----
  tls.key: |
    -----BEGIN PRIVATE KEY-----
    ...
    -----END PRIVATE KEY-----
```

### Docker Registry Secret

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: registry-credentials
  namespace: production
type: kubernetes.io/dockerconfigjson
stringData:
  .dockerconfigjson: |
    {
      "auths": {
        "myregistry.io": {
          "username": "myuser",
          "password": "mypassword"
        }
      }
    }
```

## Using ConfigMaps and Secrets

### Environment Variables

```yaml
containers:
  - name: app
    env:
      # From ConfigMap
      - name: DATABASE_HOST
        valueFrom:
          configMapKeyRef:
            name: app-config
            key: database.host
      # From Secret
      - name: DATABASE_PASSWORD
        valueFrom:
          secretKeyRef:
            name: app-secrets
            key: db-password
    # Bulk import
    envFrom:
      - configMapRef:
          name: app-config
        prefix: CONFIG_
      - secretRef:
          name: app-secrets
        prefix: SECRET_
```

### Volume Mounts

```yaml
containers:
  - name: app
    volumeMounts:
      - name: config-volume
        mountPath: /etc/config
        readOnly: true
      - name: secrets-volume
        mountPath: /etc/secrets
        readOnly: true
volumes:
  - name: config-volume
    configMap:
      name: app-config
  - name: secrets-volume
    secret:
      secretName: app-secrets
      defaultMode: 0400
```

### Kubernetes Downward API

```yaml
env:
  - name: POD_NAME
    valueFrom:
      fieldRef:
        fieldPath: metadata.name
  - name: POD_NAMESPACE
    valueFrom:
      fieldRef:
        fieldPath: metadata.namespace
  - name: POD_IP
    valueFrom:
      fieldRef:
        fieldPath: status.podIP
  - name: NODE_NAME
    valueFrom:
      fieldRef:
        fieldPath: spec.nodeName
  - name: MEMORY_LIMIT
    valueFrom:
      resourceFieldRef:
        containerName: app
        resource: limits.memory
```

## External Secrets Operator

```yaml
apiVersion: external-secrets.io/v1beta1
kind: SecretStore
metadata:
  name: aws-secrets-manager
  namespace: production
spec:
  provider:
    aws:
      service: SecretsManager
      region: us-east-1
      auth:
        jwt:
          serviceAccountRef:
            name: external-secrets-sa
---
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: app-secrets
  namespace: production
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-secrets-manager
    kind: SecretStore
  target:
    name: app-secrets
    creationPolicy: Owner
  data:
    - secretKey: db-password
      remoteRef:
        key: prod/database/password
```

## Sealed Secrets (GitOps-Safe)

```yaml
apiVersion: bitnami.com/v1alpha1
kind: SealedSecret
metadata:
  name: app-secrets
  namespace: production
spec:
  encryptedData:
    db-password: AgBj8xK5...encrypted...base64
  template:
    metadata:
      name: app-secrets
      namespace: production
    type: Opaque
```

## Immutable ConfigMaps and Secrets

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: immutable-config
immutable: true
data:
  key: value
```

## Best Practices

1. **Separation** — ConfigMaps for non-sensitive data, Secrets for credentials
2. **Immutability** — mark production configs as immutable
3. **Least privilege** — mount secrets as files with mode `0400`
4. **External management** — use External Secrets Operator or Sealed Secrets
5. **Never hardcode** — no credentials in container images or plain env vars
6. **Encryption at rest** — enable etcd encryption for Secrets
7. **Rotation** — implement secret rotation strategies
8. **Config checksums** — force pod restarts on config change via annotations

## Kustomize

### Base / Overlays Structure

```text
k8s/
├── base/
│   ├── kustomization.yaml
│   ├── deployment.yaml
│   ├── service.yaml
│   └── configmap.yaml
└── overlays/
    ├── development/
    │   ├── kustomization.yaml
    │   └── replicas-patch.yaml
    ├── staging/
    │   ├── kustomization.yaml
    │   └── replicas-patch.yaml
    └── production/
        ├── kustomization.yaml
        ├── replicas-patch.yaml
        └── resources-patch.yaml
```

### Base kustomization.yaml

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - deployment.yaml
  - service.yaml
  - configmap.yaml
commonLabels:
  app.kubernetes.io/name: web-app
```

### Production Overlay

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - ../../base
namespace: production
patches:
  - path: replicas-patch.yaml
  - path: resources-patch.yaml
configMapGenerator:
  - name: app-config
    behavior: merge
    literals:
      - LOG_LEVEL=warn
```

### Strategic Merge Patch

```yaml
# replicas-patch.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
spec:
  replicas: 5
```

```bash
# Preview rendered output
kubectl kustomize overlays/production

# Apply directly
kubectl apply -k overlays/production
```
