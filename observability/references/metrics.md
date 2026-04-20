# Metrics with Prometheus

Numeric, time-series telemetry for dashboards and alerting. Covers metric types, naming, RED/USE,
cardinality discipline, exemplars, Python and Rust integrations.

## Table of Contents

- [Metrics with Prometheus](#metrics-with-prometheus)
  - [Table of Contents](#table-of-contents)
  - [Metric types](#metric-types)
  - [Naming conventions](#naming-conventions)
  - [RED, USE, and the four golden signals](#red-use-and-the-four-golden-signals)
  - [Cardinality discipline](#cardinality-discipline)
    - [Safe label values](#safe-label-values)
    - [Never use as labels](#never-use-as-labels)
    - [Rule of thumb](#rule-of-thumb)
  - [Histograms vs summaries](#histograms-vs-summaries)
  - [Python](#python)
    - [Decorator pattern (FastAPI)](#decorator-pattern-fastapi)
    - [Exposition](#exposition)
  - [Rust](#rust)
  - [Exposing metrics](#exposing-metrics)
  - [Exemplars (linking metrics to traces)](#exemplars-linking-metrics-to-traces)
  - [PromQL essentials](#promql-essentials)
  - [Validation](#validation)

## Metric types

| Type      | Semantics                                      | Example                         |
| --------- | ---------------------------------------------- | ------------------------------- |
| Counter   | Monotonic — only increases (resets on restart) | `http_requests_total`           |
| Gauge     | Arbitrary up/down value                        | `db_connections_in_use`         |
| Histogram | Bucketed observations + count + sum            | `http_request_duration_seconds` |
| Summary   | Pre-computed quantiles (rarely preferred)      | `gc_pause_quantile_seconds`     |

Prefer **histograms** over summaries: they aggregate across instances and let Prometheus compute
quantiles via `histogram_quantile`.

## Naming conventions

```text
<namespace>_<subsystem>_<name>_<unit>
```

Rules:

- Lowercase with underscores
- End counters with `_total`
- Append the base unit (`_seconds`, `_bytes`, `_celsius`) — never milliseconds or kilobytes
- Use a stable namespace per service: `myservice_http_request_duration_seconds`

## RED, USE, and the four golden signals

| Method | For                 | Signals                              |
| ------ | ------------------- | ------------------------------------ |
| RED    | Request-driven code | Rate, Errors, Duration               |
| USE    | Resources / queues  | Utilization, Saturation, Errors      |
| Golden | All services (SRE)  | Latency, Traffic, Errors, Saturation |

Combine them: every HTTP/gRPC handler emits RED; every connection pool, queue, and worker emits USE.

## Cardinality discipline

A time series is created for every unique combination of metric name + label values. Unbounded
labels (user IDs, request UUIDs, full URLs) generate millions of series and crash Prometheus.

### Safe label values

- HTTP method (small set)
- Templated route (`/users/:id`, NOT `/users/123`)
- Status class (`2xx`, `4xx`, `5xx`) or status code if bounded
- Service name, environment
- Tier/plan (`free`, `pro`, `enterprise`)

### Never use as labels

- User IDs, account IDs, session IDs
- Request UUIDs, trace IDs (use exemplars instead)
- Full URLs with query strings
- Free-form error messages (use `error.type`/exception class)
- Timestamps

### Rule of thumb

Total series per metric < ~10,000. If you need per-user data, log it and query logs — don't put it
in a metric.

## Histograms vs summaries

Use a histogram with explicit buckets sized to your SLO:

```python
buckets = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10)
```

Then compute quantiles in PromQL:

```promql
histogram_quantile(
  0.99,
  sum by (le, route) (rate(http_request_duration_seconds_bucket[5m]))
)
```

## Python

`prometheus_client` is the canonical library.

```python
from prometheus_client import Counter, Gauge, Histogram

REQUESTS = Counter(
    "http_requests_total",
    "HTTP requests handled.",
    ["method", "route", "status"],
)

LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency.",
    ["method", "route"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
)

POOL = Gauge(
    "db_connections_in_use",
    "Active DB connections.",
)
```

### Decorator pattern (FastAPI)

```python
import time
from contextlib import contextmanager


@contextmanager
def track(method: str, route: str):
    start = time.perf_counter()
    status = "500"
    try:
        yield
        status = "200"
    finally:
        REQUESTS.labels(method=method, route=route, status=status).inc()
        LATENCY.labels(method=method, route=route).observe(time.perf_counter() - start)
```

### Exposition

```python
from prometheus_client import make_asgi_app

# mount under /metrics in your ASGI app
metrics_app = make_asgi_app()
```

## Rust

The `metrics` facade with a Prometheus exporter is the most ergonomic option.

`Cargo.toml`:

```toml
[dependencies]
metrics = "0.23"
metrics-exporter-prometheus = "0.15"
```

```rust
use metrics::{counter, histogram, gauge, describe_counter, describe_histogram};
use metrics_exporter_prometheus::PrometheusBuilder;

pub fn install_metrics() {
    PrometheusBuilder::new()
        .with_http_listener(([0, 0, 0, 0], 9000))
        .install()
        .expect("failed to install metrics exporter");

    describe_counter!("http_requests_total", "HTTP requests handled.");
    describe_histogram!("http_request_duration_seconds", "HTTP request latency.");
}

pub async fn handle(method: &str, route: &str) {
    let start = std::time::Instant::now();
    // ... handle request ...
    counter!("http_requests_total", "method" => method.to_owned(), "route" => route.to_owned(), "status" => "200").increment(1);
    histogram!("http_request_duration_seconds", "method" => method.to_owned(), "route" => route.to_owned())
        .record(start.elapsed().as_secs_f64());
}
```

`gauge!` for current values:

```rust
gauge!("db_connections_in_use").set(pool.in_use() as f64);
```

## Exposing metrics

- Prefer pull (Prometheus scraping `/metrics`) for long-running services
- Use push (`prometheus_pushgateway`) only for short-lived batch jobs
- In Kubernetes, annotate the service for scraping or use a `ServiceMonitor` (Prometheus Operator)

```yaml
apiVersion: v1
kind: Service
metadata:
  name: myservice
  annotations:
    prometheus.io/scrape: "true"
    prometheus.io/port: "9000"
    prometheus.io/path: "/metrics"
```

## Exemplars (linking metrics to traces)

Exemplars attach a sample trace ID to a histogram observation, so a Grafana panel can jump straight
from a latency spike to the trace that caused it.

```python
from opentelemetry import trace

span = trace.get_current_span()
ctx = span.get_span_context() if span else None
trace_id = format(ctx.trace_id, "032x") if ctx and ctx.trace_id else None

LATENCY.labels(method="GET", route="/orders").observe(
    duration,
    exemplar={"trace_id": trace_id} if trace_id else None,
)
```

## PromQL essentials

```promql
# Request rate per route (RPS)
sum by (route) (rate(http_requests_total[5m]))

# Error ratio (%)
sum(rate(http_requests_total{status=~"5.."}[5m]))
  / sum(rate(http_requests_total[5m])) * 100

# p99 latency per route
histogram_quantile(
  0.99,
  sum by (le, route) (rate(http_request_duration_seconds_bucket[5m]))
)

# Saturation: pool utilization
db_connections_in_use / db_connections_max

# Anomaly: deviation from 1h baseline
abs(rate(http_requests_total[5m]) - rate(http_requests_total[5m] offset 1h))
  / rate(http_requests_total[5m] offset 1h) > 0.5
```

## Validation

- Scrape `/metrics` locally and grep for the metric name + a representative label set
- Check series count: `count by (__name__)({__name__=~"myservice_.*"})` — investigate any name with
  > 10k series
- Plot every metric on a dashboard before merging — unviewed metrics rot
