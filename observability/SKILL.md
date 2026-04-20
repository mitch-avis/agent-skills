---
name: observability
description: >-
  End-to-end observability for backend services and infrastructure — structured logging, metrics,
  distributed tracing, log aggregation, alerting, SLOs, and the three pillars across Python, Rust,
  containers, Kubernetes, service meshes, and CI/CD pipelines. Use when adding logs/metrics/traces
  to an application, designing SLIs/SLOs, propagating correlation IDs, instrumenting with
  OpenTelemetry, configuring Prometheus/Grafana/Loki/ELK, debugging production with insufficient
  telemetry, building dashboards, writing alert rules, or investigating log spikes during an
  incident.
---

# Observability

Make backend services and infrastructure observable: emit signals an operator can use to answer
"what is happening, where, and why" without redeploying code. Covers logs, metrics, and traces for
applications (Python, Rust) and the platforms that run them (containers, Kubernetes, service meshes,
CI/CD).

## When to Use

- Instrumenting a service with logs, metrics, or traces
- Wiring OpenTelemetry into a Python or Rust application
- Configuring Prometheus, Grafana, Loki, or the ELK/Elastic stack
- Adding correlation IDs that flow across services and async boundaries
- Designing SLIs/SLOs and writing alert rules
- Hardening logs against PII leakage or unbounded cardinality
- Investigating a log spike, error surge, or latency regression
- Adding pipeline visibility to CI/CD or GitOps workflows
- Setting up tracing/metrics for an Istio or Linkerd service mesh

## The Three Pillars

| Pillar      | Question Answered               | Tooling                                  |
| ----------- | ------------------------------- | ---------------------------------------- |
| **Logs**    | What happened? (events, errors) | structlog, `tracing`, Loki, Elastic, ELK |
| **Metrics** | How much/how fast? (aggregates) | Prometheus, OpenMetrics, Grafana         |
| **Traces**  | Where did time go across calls? | OpenTelemetry, Tempo, Jaeger, Zipkin     |

The three are correlated by a **trace ID / correlation ID** propagated through every request. Every
log line, metric exemplar, and span carries that ID — that is what makes telemetry investigatable.

## Core Principles

1. **Structured over free-form.** Emit JSON in production with consistent fields; never rely on
   `printf`-style strings to encode state.
2. **Correlate everything.** Generate a trace/correlation ID at ingress, propagate it via headers
   (`traceparent`, `X-Correlation-ID`), and bind it to every log and span.
3. **Bounded cardinality.** Metric labels must come from a small fixed set. Never label by
   `user_id`, `request_id`, full URL, or any unbounded value — it explodes storage cost.
4. **Alert on symptoms, not causes.** Page on user-visible SLO breaches (latency, error rate), not
   on internal CPU or queue depth alone.
5. **Sample intelligently.** 100% in dev, 1–10% (head-based) or tail-based in prod. Always keep
   errors and slow traces.
6. **Never log secrets or PII.** Redact at the logger boundary, not after the fact.
7. **Every alert has a runbook.** No alert without a documented next action.

## Quick Start

### Python — structured logs with structlog

```python
import structlog

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(),
    ],
)

log = structlog.get_logger()
log.info("order_created", order_id="ord_123", user_id="usr_456", total=99.99, items=3)
```

### Rust — structured logs with `tracing`

```rust
use tracing_subscriber::{fmt, EnvFilter};

fn main() {
    tracing_subscriber::fmt()
        .json()
        .with_env_filter(EnvFilter::from_default_env())
        .init();

    tracing::info!(order_id = "ord_123", user_id = "usr_456", total = 99.99, "order_created");
}
```

### Prometheus metric (any language) — RED for HTTP

```text
http_requests_total{method,route,status}             # Counter (Rate, Errors)
http_request_duration_seconds_bucket{method,route}   # Histogram (Duration)
```

## Signals to Emit at Every Service Boundary

### RED (request-driven services)

| Signal       | Metric type | What to alert on            |
| ------------ | ----------- | --------------------------- |
| **R**ate     | Counter     | Anomalous deviation         |
| **E**rrors   | Counter     | Error ratio > SLO threshold |
| **D**uration | Histogram   | p95/p99 > SLO threshold     |

### USE (resources / queues / pools)

| Signal          | Metric type | Examples                       |
| --------------- | ----------- | ------------------------------ |
| **U**tilization | Gauge       | CPU %, pool used / pool size   |
| **S**aturation  | Gauge       | Queue depth, wait time         |
| **E**rrors      | Counter     | Connection failures, OOM kills |

### The Four Golden Signals (SRE)

Latency, traffic, errors, saturation. Same idea as RED + USE; track for every dependency.

## Log Levels — Semantic Use

| Level | Use For                                             | Production?        |
| ----- | --------------------------------------------------- | ------------------ |
| TRACE | Verbose flow tracing (Rust `tracing` only)          | Off                |
| DEBUG | Variable values, internal state                     | Off (or sampled)   |
| INFO  | Business events, request lifecycle, state changes   | On                 |
| WARN  | Recoverable anomalies — retry, fallback, near-limit | On                 |
| ERROR | Failures requiring investigation                    | On (alert on rate) |
| FATAL | Process must exit                                   | On (page)          |

A user typing the wrong password is `INFO`, not `ERROR`. Reserve `ERROR` for things that need a
human.

## Reference Map

Load on demand based on the task:

| Topic                                           | File                                                        | Load When                                             |                                                       |
| ----------------------------------------------- | ----------------------------------------------------------- | ----------------------------------------------------- | ----------------------------------------------------- |
| Structured logging in Python and Rust           | [structured-logging.md](references/structured-logging.md)   | Wiring `structlog` / `tracing`, levels, PII, sampling |                                                       |
| Metrics with Prometheus                         | [metrics.md](references/metrics.md)                         | Adding counters/histograms, RED/USE, cardinality      |                                                       |
| Distributed tracing with OpenTelemetry          | [tracing.md](references/tracing.md)                         | Adding spans, propagation, sampling, exporters        |                                                       |
| Log aggregation (ELK, Loki, Vector, Fluent Bit) | [log-aggregation.md](references/log-aggregation.md)         | Standing up centralized logging, shippers, parsing    |                                                       |
| Investigating logs with Elastic ES\             | QL                                                          | [log-search-esql.md](references/log-search-esql.md)   | Hunting an incident in Kibana / Elastic Observability |
| Kubernetes, service mesh, CI/CD observability   | [infra-observability.md](references/infra-observability.md) | Istio/Linkerd, K8s metrics, GitHub Actions, ArgoCD    |                                                       |
| SLIs, SLOs, alerting, runbooks                  | [slos-and-alerting.md](references/slos-and-alerting.md)     | Defining SLOs, writing PrometheusRules, error budgets |                                                       |

## Related Skills

- [python](../python/SKILL.md) and [python-resilience](../python-resilience/SKILL.md) — pair with
  this skill for Python service instrumentation
- [python-async](../python-async/SKILL.md) — `contextvars` propagation across `async` boundaries
- [rust](../rust/SKILL.md) and [rust-async](../rust-async/SKILL.md) — `tracing` integrates deeply
  with Tokio
- [kubernetes](../kubernetes/SKILL.md) and [helm](../helm/SKILL.md) — deploying Prometheus, Grafana,
  Loki, OTel collectors
- [docker](../docker/SKILL.md) — sidecar collectors, log drivers
- [cicd](../cicd/SKILL.md) — pipeline telemetry and deploy markers
- [systematic-debugging](../systematic-debugging/SKILL.md) — once telemetry exists, use it to do
  evidence-based root cause analysis

## Anti-Patterns

- String-interpolated log messages (`f"user {id} failed"`) — unparseable, unsearchable
- Logging secrets, tokens, passwords, full request bodies, full PII
- Alerting on every error — alert on rates and SLO burn
- Metrics with unbounded labels (`user_id`, full URL path, request UUID)
- 100% trace sampling in production without head/tail strategy
- Collecting metrics with no dashboards or alerts attached
- Per-line `print` debugging in production hot paths
- Ignoring trace context — logs without a correlation ID are nearly useless during an incident
- Treating `log.level: error` as the source of truth — levels are often missing or wrong; funnel by
  message content (see [log-search-esql.md](references/log-search-esql.md))
- Synchronous logging on the request hot path (use buffered/async appenders)

## Standard Field Names (ECS-aligned)

Use these field names so logs interoperate with Elastic, Loki, OTel, and most dashboards:

| Field                 | Meaning                                         |
| --------------------- | ----------------------------------------------- |
| `@timestamp`          | ISO-8601 event time                             |
| `log.level`           | DEBUG / INFO / WARN / ERROR                     |
| `service.name`        | Logical service identifier                      |
| `service.version`     | Build / release version                         |
| `service.environment` | dev / staging / prod                            |
| `trace.id`            | OpenTelemetry trace ID                          |
| `span.id`             | OpenTelemetry span ID                           |
| `correlation.id`      | Application-level request ID (alias trace.id)   |
| `user.id`             | Authenticated principal (hash if PII-sensitive) |
| `http.method`         | GET / POST / ...                                |
| `http.route`          | Templated route, not raw URL                    |
| `http.status_code`    | Numeric response code                           |
| `error.type`          | Exception class / Rust error variant            |
| `error.message`       | Human-readable error                            |
| `error.stack_trace`   | Full stack (server-side only)                   |

## Verification Checklist

Before considering a service "observable":

- [ ] Logs are JSON in prod, include `trace.id` and `service.name` on every line
- [ ] No secrets, tokens, or unmasked PII reach the logger
- [ ] RED metrics exposed at every HTTP/gRPC endpoint
- [ ] USE metrics exposed for every connection pool, queue, and worker
- [ ] OpenTelemetry traces emitted for every request and outbound dependency call
- [ ] Trace context propagates via `traceparent` to all downstream services
- [ ] Dashboards exist for RED + USE per service
- [ ] PrometheusRules / alerts configured for SLO burn, with linked runbooks
- [ ] Sampling configured (head + tail) appropriate to traffic volume
- [ ] Log/metric/trace retention policy documented and enforced
