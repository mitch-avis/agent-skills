# Kubernetes Networking

## Service Types

### ClusterIP (Default — Internal Only)

```yaml
apiVersion: v1
kind: Service
metadata:
  name: web-app
  namespace: production
spec:
  type: ClusterIP
  selector:
    app.kubernetes.io/name: web-app
  ports:
    - name: http
      port: 80
      targetPort: 8080
    - name: metrics
      port: 9090
      targetPort: metrics
```

### Headless Service (StatefulSet)

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

DNS names: `postgres-0.postgres-headless.database.svc.cluster.local`

### NodePort

```yaml
apiVersion: v1
kind: Service
metadata:
  name: external-app
  namespace: production
spec:
  type: NodePort
  selector:
    app.kubernetes.io/name: external-app
  ports:
    - name: http
      port: 80
      targetPort: 8080
      nodePort: 30080
```

### LoadBalancer

```yaml
apiVersion: v1
kind: Service
metadata:
  name: public-web
  namespace: production
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-type: "nlb"
spec:
  type: LoadBalancer
  selector:
    app.kubernetes.io/name: web-app
  ports:
    - name: http
      port: 80
      targetPort: 8080
    - name: https
      port: 443
      targetPort: 8443
  loadBalancerSourceRanges:
    - 203.0.113.0/24
```

## Ingress

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: web-ingress
  namespace: production
  annotations:
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/proxy-body-size: "10m"
    nginx.ingress.kubernetes.io/rate-limit: "100"
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  ingressClassName: nginx
  tls:
    - hosts:
        - www.example.com
        - api.example.com
      secretName: example-tls
  rules:
    - host: www.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: frontend
                port:
                  number: 80
    - host: api.example.com
      http:
        paths:
          - path: /v1
            pathType: Prefix
            backend:
              service:
                name: api-v1
                port:
                  number: 8080
          - path: /v2
            pathType: Prefix
            backend:
              service:
                name: api-v2
                port:
                  number: 8080
```

## NetworkPolicy

### Default Deny All

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: production
spec:
  podSelector: {}
  policyTypes: ["Ingress", "Egress"]
```

### Allow DNS

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-dns
  namespace: production
spec:
  podSelector: {}
  policyTypes: ["Egress"]
  egress:
    - to:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: kube-system
      ports:
        - protocol: UDP
          port: 53
```

### Allow Frontend to Backend

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: frontend-to-backend
  namespace: production
spec:
  podSelector:
    matchLabels:
      app.kubernetes.io/component: backend
  policyTypes: ["Ingress"]
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app.kubernetes.io/component: frontend
      ports:
        - protocol: TCP
          port: 8080
```

### Backend to Database

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: backend-to-database
  namespace: production
spec:
  podSelector:
    matchLabels:
      app.kubernetes.io/name: postgres
  policyTypes: ["Ingress"]
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app.kubernetes.io/component: backend
      ports:
        - protocol: TCP
          port: 5432
```

### Cross-Namespace (Monitoring)

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-monitoring
  namespace: production
spec:
  podSelector: {}
  policyTypes: ["Ingress"]
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: monitoring
          podSelector:
            matchLabels:
              app.kubernetes.io/name: prometheus
      ports:
        - protocol: TCP
          port: 8080
```

## DNS

```text
# Within same namespace
http://web-app

# Cross-namespace
http://web-app.production.svc.cluster.local

# Headless (StatefulSet)
postgres-0.postgres-headless.database.svc.cluster.local
```

## Service Mesh (Istio)

### VirtualService (Traffic Splitting)

```yaml
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: web-app-routes
  namespace: production
spec:
  hosts:
    - web-app
  http:
    - match:
        - headers:
            canary:
              exact: "true"
      route:
        - destination:
            host: web-app
            subset: v2
    - route:
        - destination:
            host: web-app
            subset: v1
          weight: 90
        - destination:
            host: web-app
            subset: v2
          weight: 10
```

### DestinationRule

```yaml
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: web-app
  namespace: production
spec:
  host: web-app
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
      http:
        http2MaxRequests: 100
    loadBalancer:
      simple: LEAST_REQUEST
  subsets:
    - name: v1
      labels:
        version: v1.0.0
    - name: v2
      labels:
        version: v2.0.0
```

## Best Practices

1. **Default deny** — start with deny-all NetworkPolicy, allow specific traffic
2. **Least privilege** — open only required ports and protocols
3. **ClusterIP first** — use ClusterIP by default, LoadBalancer sparingly
4. **DNS names** — use service DNS, never hardcode IPs
5. **TLS termination** — terminate TLS at Ingress level
6. **Rate limiting** — apply at Ingress layer
7. **Metrics endpoints** — expose for Prometheus scraping

## Additional Service Types

### ExternalName

Maps a service to an external DNS name (CNAME record). No proxying — the cluster DNS returns a CNAME
directly:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: external-db
  namespace: production
spec:
  type: ExternalName
  externalName: db.legacy.example.com
```

## Service Discovery

Kubernetes injects service coordinates as environment variables into every pod in the same
namespace. DNS is preferred, but env vars work without CoreDNS:

```text
# For a Service named "web-app" on port 80:
WEB_APP_SERVICE_HOST=10.96.0.42
WEB_APP_SERVICE_PORT=80
WEB_APP_PORT=tcp://10.96.0.42:80
```

## Gateway API

Gateway API is the successor to Ingress, providing richer routing and role-oriented resource model
(GatewayClass → Gateway → HTTPRoute):

### GatewayClass + Gateway

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: GatewayClass
metadata:
  name: istio
spec:
  controllerName: istio.io/gateway-controller
---
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: production-gateway
  namespace: production
spec:
  gatewayClassName: istio
  listeners:
    - name: http
      port: 80
      protocol: HTTP
      allowedRoutes:
        namespaces:
          from: Same
    - name: https
      port: 443
      protocol: HTTPS
      tls:
        mode: Terminate
        certificateRefs:
          - name: example-tls
      allowedRoutes:
        namespaces:
          from: Same
```

### HTTPRoute

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: web-app
  namespace: production
spec:
  parentRefs:
    - name: production-gateway
  hostnames:
    - www.example.com
  rules:
    - matches:
        - path:
            type: PathPrefix
            value: /api
      backendRefs:
        - name: api-service
          port: 8080
          weight: 90
        - name: api-service-canary
          port: 8080
          weight: 10
    - matches:
        - path:
            type: PathPrefix
            value: /
      backendRefs:
        - name: frontend
          port: 80
```

## Additional NetworkPolicy Patterns

### Allow Ingress Controller

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-ingress-controller
  namespace: production
spec:
  podSelector: {}
  policyTypes:
    - Ingress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: ingress-nginx
      ports:
        - protocol: TCP
          port: 8080
        - protocol: TCP
          port: 8443
```

### Allow Prometheus Scraping

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-prometheus
  namespace: production
spec:
  podSelector: {}
  policyTypes:
    - Ingress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: monitoring
      ports:
        - protocol: TCP
          port: 9090
```

### Allow External HTTPS (Block Metadata)

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-external-https
  namespace: production
spec:
  podSelector:
    matchLabels:
      egress: external
  policyTypes:
    - Egress
  egress:
    - to:
        - ipBlock:
            cidr: 0.0.0.0/0
            except:
              - 169.254.169.254/32  # Block cloud metadata
      ports:
        - protocol: TCP
          port: 443
```

## PodDisruptionBudget

Limits voluntary disruptions (node drain, cluster upgrade) to maintain availability:

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: web-app-pdb
  namespace: production
spec:
  minAvailable: 2
  # OR: maxUnavailable: 1
  selector:
    matchLabels:
      app.kubernetes.io/name: web-app
```

## Common CRDs

### cert-manager Certificate + ClusterIssuer

```yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: admin@example.com
    privateKeySecretRef:
      name: letsencrypt-prod-key
    solvers:
      - http01:
          ingress:
            ingressClassName: nginx
---
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: example-tls
  namespace: production
spec:
  secretName: example-tls
  issuerRef:
    name: letsencrypt-prod
    kind: ClusterIssuer
  dnsNames:
    - www.example.com
    - api.example.com
```

### Prometheus ServiceMonitor

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: web-app
  namespace: production
  labels:
    release: prometheus
spec:
  selector:
    matchLabels:
      app.kubernetes.io/name: web-app
  endpoints:
    - port: metrics
      interval: 30s
      path: /metrics
```
