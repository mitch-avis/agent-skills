# Infrastructure Observability

Telemetry for the platforms below the application: containers, Kubernetes, service meshes,
and CI/CD pipelines.

## Table of Contents

- [Containers and Docker](#containers-and-docker)
- [Kubernetes](#kubernetes)
- [Service mesh — Istio](#service-mesh--istio)
- [Service mesh — Linkerd](#service-mesh--linkerd)
- [Distributed tracing in mesh](#distributed-tracing-in-mesh)
- [Kiali — mesh topology visualization](#kiali--mesh-topology-visualization)
- [CI/CD observability](#cicd-observability)
- [GitOps / ArgoCD](#gitops--argocd)
- [Mesh alerting rules](#mesh-alerting-rules)

## Containers and Docker

- Use the `json-file` log driver (default) and let a node agent ship logs
- Add labels for `service`, `environment`, `version` so the agent can promote them to log
  fields
- Expose `/metrics` on a separate port from the app; in Compose, publish only internally and
  let Prometheus scrape via the Docker network
- For health: use Docker `HEALTHCHECK` and Compose `depends_on: condition: service_healthy`

```yaml
services:
  api:
    image: myorg/api:1.4.2
    labels:
      service: api
      environment: prod
    healthcheck:
      test: ["CMD", "wget", "-qO-", "http://localhost:8080/healthz"]
      interval: 10s
      timeout: 2s
      retries: 3
    logging:
      driver: json-file
      options: { max-size: "10m", max-file: "5" }
```

## Kubernetes

### kube-prometheus-stack (Helm)

Bundles Prometheus Operator, Grafana, Alertmanager, node-exporter, kube-state-metrics.

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm upgrade --install kps prometheus-community/kube-prometheus-stack \
  --namespace monitoring --create-namespace
```

### Scrape application metrics

Use a `ServiceMonitor` (Prometheus Operator) so apps don't need pod annotations:

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: api
  namespace: monitoring
  labels:
    release: kps
spec:
  namespaceSelector:
    matchNames: [default]
  selector:
    matchLabels: { app: api }
  endpoints:
    - port: metrics
      interval: 15s
      path: /metrics
```

### Useful baseline metrics

| Source             | Metric examples                                                           |
| ------------------ | ------------------------------------------------------------------------- |
| kube-state-metrics | `kube_pod_status_phase`, `kube_deployment_status_replicas`                |
| node-exporter      | `node_cpu_seconds_total`, `node_memory_MemAvailable_bytes`                |
| cAdvisor (kubelet) | `container_cpu_usage_seconds_total`, `container_memory_working_set_bytes` |
| API server         | `apiserver_request_duration_seconds`                                      |

### PromQL recipes

```promql
# Pods not Ready for > 5m
sum by (namespace, pod) (kube_pod_status_ready{condition="true"} == 0)

# Container memory utilization
container_memory_working_set_bytes
  / on (container, pod, namespace) kube_pod_container_resource_limits{resource="memory"}

# CPU throttling
rate(container_cpu_cfs_throttled_seconds_total[5m]) > 0

# Recent restarts
increase(kube_pod_container_status_restarts_total[15m]) > 0
```

## Service mesh — Istio

Istio Envoy sidecars emit RED metrics for free; configure tracing via `MeshConfig`.

### Enable tracing

```yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  meshConfig:
    enableTracing: true
    defaultConfig:
      tracing:
        sampling: 10.0
        zipkin:
          address: jaeger-collector.istio-system:9411
```

### Per-namespace sampling override

```yaml
apiVersion: telemetry.istio.io/v1alpha1
kind: Telemetry
metadata:
  name: tracing-sampling
  namespace: orders
spec:
  tracing:
    - providers: [{ name: otel }]
      randomSamplingPercentage: 100
```

### Key Istio PromQL queries

```promql
# Request rate per destination service
sum by (destination_service_name) (
  rate(istio_requests_total{reporter="destination"}[5m])
)

# 5xx error ratio
sum by (destination_service_name) (
  rate(istio_requests_total{reporter="destination", response_code=~"5.."}[5m])
)
/ sum by (destination_service_name) (
  rate(istio_requests_total{reporter="destination"}[5m])
)

# p99 latency
histogram_quantile(
  0.99,
  sum by (le, destination_service_name) (
    rate(istio_request_duration_milliseconds_bucket{reporter="destination"}[5m])
  )
)
```

## Service mesh — Linkerd

Linkerd ships its own viz extension with built-in dashboards.

```bash
linkerd viz install | kubectl apply -f -
linkerd viz dashboard
```

Useful CLI:

```bash
linkerd viz top    deploy/api                       # live RED for a workload
linkerd viz routes deploy/api --to deploy/db        # per-route metrics
linkerd viz tap    deploy/api --to deploy/db        # live request inspection
linkerd viz edges  deployment -n orders             # service dependency edges
```

## Distributed tracing in mesh

The mesh injects `traceparent` and B3 headers, but **applications must propagate them** to
downstream calls — otherwise the trace breaks at the first internal hop. See
[tracing.md](tracing.md) for SDK-level propagation.

### Jaeger (all-in-one)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata: { name: jaeger, namespace: istio-system }
spec:
  selector: { matchLabels: { app: jaeger } }
  template:
    metadata: { labels: { app: jaeger } }
    spec:
      containers:
        - name: jaeger
          image: jaegertracing/all-in-one:1.57
          env:
            - { name: COLLECTOR_ZIPKIN_HOST_PORT, value: ":9411" }
          ports:
            - { containerPort: 16686 }   # UI
            - { containerPort: 14250 }   # gRPC
            - { containerPort: 9411 }    # Zipkin
```

For production, replace all-in-one with the Jaeger Operator (Cassandra/Elastic backend) or
swap to **Tempo + Grafana**.

## Kiali — mesh topology visualization

```yaml
apiVersion: kiali.io/v1alpha1
kind: Kiali
metadata: { name: kiali, namespace: istio-system }
spec:
  auth: { strategy: anonymous }     # use openid / token in prod
  deployment:
    accessible_namespaces: ["**"]
  external_services:
    prometheus: { url: http://prometheus.istio-system:9090 }
    tracing:    { url: http://jaeger-query.istio-system:16686 }
    grafana:    { url: http://grafana.istio-system:3000 }
```

## CI/CD observability

Treat pipelines as services: emit duration, success rate, queue time. Pair with the
[cicd](../../cicd/SKILL.md) skill.

### Deploy markers

Push a "deploy" event into Grafana / your trace backend on every release so dashboards show
*when* something changed. GitHub Actions example:

```yaml
- name: Annotate Grafana
  run: |
    curl -X POST "$GRAFANA_URL/api/annotations" \
      -H "Authorization: Bearer $GRAFANA_TOKEN" \
      -H "Content-Type: application/json" \
      -d "{\"text\": \"deploy ${{ github.sha }}\", \"tags\": [\"deploy\", \"$SERVICE\"]}"
```

### Pipeline metrics

Useful counters/gauges to expose from a CI runner or scrape from the SCM API:

| Metric                         | Purpose                       |
| ------------------------------ | ----------------------------- |
| `ci_pipeline_duration_seconds` | DORA: lead time for changes   |
| `ci_pipeline_failures_total`   | DORA: change failure rate     |
| `ci_pipeline_queue_seconds`    | Runner saturation             |
| `cd_deployment_total`          | DORA: deployment frequency    |
| `cd_rollback_total`            | DORA: change failure rate     |
| `cd_mttr_seconds`              | DORA: time to restore service |

Track the [DORA metrics](https://dora.dev/) — they correlate strongly with delivery health.

### Pipeline tracing

OTel has CI/CD semantic conventions and exporters for GitHub Actions / GitLab. Each job
becomes a span; failing jobs become error spans. Browseable in Tempo/Jaeger like any other
trace.

## GitOps / ArgoCD

Scrape Argo CD's `/metrics` endpoint:

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata: { name: argocd-metrics, namespace: argocd, labels: { release: kps } }
spec:
  selector: { matchLabels: { app.kubernetes.io/name: argocd-metrics } }
  endpoints: [ { port: metrics, interval: 30s } ]
```

Useful Argo metrics:

| Metric                                        | Meaning                        |
| --------------------------------------------- | ------------------------------ |
| `argocd_app_info{sync_status, health_status}` | App sync/health state          |
| `argocd_app_sync_total`                       | Sync attempts                  |
| `argocd_app_reconcile_bucket`                 | Reconcile latency histogram    |
| `argocd_kubectl_exec_pending`                 | Backpressure on the controller |

Alert when `sync_status != Synced` or `health_status != Healthy` for > 10 minutes.

## Mesh alerting rules

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata: { name: mesh-alerts, namespace: monitoring }
spec:
  groups:
    - name: mesh.rules
      rules:
        - alert: HighErrorRate
          expr: |
            sum by (destination_service_name) (
              rate(istio_requests_total{response_code=~"5.."}[5m])
            )
            / sum by (destination_service_name) (
              rate(istio_requests_total[5m])
            ) > 0.05
          for: 5m
          labels: { severity: critical }
          annotations:
            summary: "5xx > 5% on {{ $labels.destination_service_name }}"
            runbook: "https://runbooks/mesh-high-error-rate"

        - alert: HighP99Latency
          expr: |
            histogram_quantile(
              0.99,
              sum by (le, destination_service_name) (
                rate(istio_request_duration_milliseconds_bucket[5m])
              )
            ) > 1000
          for: 10m
          labels: { severity: warning }

        - alert: MeshCertExpiring
          expr: (cert_expiry_timestamp_seconds - time()) / 86400 < 7
          labels: { severity: warning }
          annotations:
            summary: "Mesh cert expiring in < 7 days"
```

For SLO-driven alerts (multi-window burn rate), see
[slos-and-alerting.md](slos-and-alerting.md).
