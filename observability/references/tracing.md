# Distributed Tracing with OpenTelemetry

Traces show how time is spent across services. A trace is a tree of spans; each span has a name,
start/end, attributes, and links. OpenTelemetry (OTel) is the vendor-neutral standard.

## Table of Contents

- [Concepts](#concepts)
- [Context propagation](#context-propagation)
- [Sampling strategies](#sampling-strategies)
- [Python — OpenTelemetry SDK](#python--opentelemetry-sdk)
- [Rust — `tracing` + `tracing-opentelemetry`](#rust--tracing--tracing-opentelemetry)
- [OTel Collector](#otel-collector)
- [Backends](#backends)
- [Span attributes — semantic conventions](#span-attributes--semantic-conventions)
- [Anti-patterns](#anti-patterns)

## Concepts

| Term     | Meaning                                                           |
| -------- | ----------------------------------------------------------------- |
| Trace    | The whole request — one trace ID end-to-end                       |
| Span     | A single operation within a trace (HTTP call, DB query, function) |
| Parent   | The span that started the current one                             |
| Baggage  | Key-value data propagated alongside trace context                 |
| Exporter | Sends spans to a backend (OTLP, Jaeger, Zipkin)                   |
| Sampler  | Decides which traces to keep                                      |

## Context propagation

OTel uses W3C `traceparent` (and `tracestate`) HTTP headers. Format:

```text
traceparent: 00-<trace-id-32hex>-<span-id-16hex>-<flags-2hex>
```

Always prefer `traceparent` to custom headers — every OTel SDK and most observability tools
understand it.

## Sampling strategies

| Strategy     | When to use                                             |
| ------------ | ------------------------------------------------------- |
| AlwaysOn     | Dev only                                                |
| AlwaysOff    | Disable tracing entirely                                |
| TraceIdRatio | Head-based: keep N% of traces, decided at the root span |
| ParentBased  | Honor the upstream service's sampling decision          |
| Tail-based   | Keep all errors / slow traces (collector-side)          |

Recommended production setup: `ParentBased(TraceIdRatio(0.05))` at the SDK plus tail-based rules
in the OTel Collector to keep all errors.

## Python — OpenTelemetry SDK

`pyproject.toml`:

```toml
[project]
dependencies = [
  "opentelemetry-api",
  "opentelemetry-sdk",
  "opentelemetry-exporter-otlp",
  "opentelemetry-instrumentation-fastapi",
  "opentelemetry-instrumentation-httpx",
  "opentelemetry-instrumentation-sqlalchemy",
]
```

### Bootstrap

```python
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased


def init_tracing(service: str, otlp_endpoint: str, sample: float = 0.05) -> None:
    resource = Resource.create({
        "service.name": service,
        "service.version": "1.4.2",
        "deployment.environment": "prod",
    })
    provider = TracerProvider(
        resource=resource,
        sampler=ParentBased(TraceIdRatioBased(sample)),
    )
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=otlp_endpoint)))
    trace.set_tracer_provider(provider)
```

### Auto-instrumentation

For HTTP/DB clients, prefer the auto-instrumentation packages:

```python
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

FastAPIInstrumentor.instrument_app(app)
HTTPXClientInstrumentor().instrument()
SQLAlchemyInstrumentor().instrument(engine=engine)
```

### Manual spans

```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)


async def process_order(order_id: str) -> Order:
    with tracer.start_as_current_span("process_order") as span:
        span.set_attribute("order.id", order_id)

        with tracer.start_as_current_span("validate"):
            validate(order_id)

        with tracer.start_as_current_span("charge"):
            charge(order_id)

        span.set_attribute("order.status", "complete")
        return order
```

Record exceptions on spans:

```python
from opentelemetry.trace import Status, StatusCode

try:
    charge(order)
except Exception as exc:
    span.record_exception(exc)
    span.set_status(Status(StatusCode.ERROR, str(exc)))
    raise
```

## Rust — `tracing` + `tracing-opentelemetry`

The `tracing` crate emits spans; `tracing-opentelemetry` ships them via OTLP.

`Cargo.toml`:

```toml
[dependencies]
tracing = "0.1"
tracing-subscriber = { version = "0.3", features = ["env-filter", "json"] }
tracing-opentelemetry = "0.25"
opentelemetry = "0.24"
opentelemetry_sdk = { version = "0.24", features = ["rt-tokio"] }
opentelemetry-otlp = { version = "0.17", features = ["grpc-tonic"] }
```

```rust
use opentelemetry::trace::TracerProvider as _;
use opentelemetry_otlp::WithExportConfig;
use opentelemetry_sdk::{trace, Resource};
use tracing_subscriber::{prelude::*, EnvFilter};

pub fn init_telemetry(service: &str, endpoint: &str) -> anyhow::Result<()> {
    let exporter = opentelemetry_otlp::new_exporter().tonic().with_endpoint(endpoint);

    let provider = opentelemetry_otlp::new_pipeline()
        .tracing()
        .with_exporter(exporter)
        .with_trace_config(
            trace::Config::default()
                .with_sampler(trace::Sampler::ParentBased(Box::new(
                    trace::Sampler::TraceIdRatioBased(0.05),
                )))
                .with_resource(Resource::new(vec![
                    opentelemetry::KeyValue::new("service.name", service.to_string()),
                ])),
        )
        .install_batch(opentelemetry_sdk::runtime::Tokio)?;

    let tracer = provider.tracer(service.to_string());
    let otel_layer = tracing_opentelemetry::layer().with_tracer(tracer);

    tracing_subscriber::registry()
        .with(EnvFilter::from_default_env())
        .with(tracing_subscriber::fmt::layer().json())
        .with(otel_layer)
        .init();

    Ok(())
}
```

Now every `tracing::info_span!` / `#[instrument]` becomes an OTel span exported to the
collector.

### Cross-service propagation (reqwest / axum)

```rust
use opentelemetry::global;
use opentelemetry::propagation::Injector;

struct HeaderInjector<'a>(&'a mut reqwest::header::HeaderMap);

impl Injector for HeaderInjector<'_> {
    fn set(&mut self, key: &str, value: String) {
        if let (Ok(name), Ok(val)) = (
            reqwest::header::HeaderName::from_bytes(key.as_bytes()),
            reqwest::header::HeaderValue::from_str(&value),
        ) {
            self.0.insert(name, val);
        }
    }
}

let mut req = reqwest::Request::new(method, url);
let cx = tracing::Span::current().context();
global::get_text_map_propagator(|p| p.inject_context(&cx, &mut HeaderInjector(req.headers_mut())));
```

## OTel Collector

Run a Collector in front of your backend to handle batching, sampling, redaction, and routing.

```yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318

processors:
  batch:
    timeout: 5s
    send_batch_size: 1024
  tail_sampling:
    decision_wait: 10s
    policies:
      - name: errors
        type: status_code
        status_code: { status_codes: [ERROR] }
      - name: slow
        type: latency
        latency: { threshold_ms: 1000 }
      - name: sample-rest
        type: probabilistic
        probabilistic: { sampling_percentage: 5 }
  attributes/redact:
    actions:
      - key: http.request.header.authorization
        action: delete

exporters:
  otlphttp/tempo:
    endpoint: http://tempo:4318
  prometheus:
    endpoint: 0.0.0.0:8889

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [attributes/redact, tail_sampling, batch]
      exporters: [otlphttp/tempo]
    metrics:
      receivers: [otlp]
      processors: [batch]
      exporters: [prometheus]
```

## Backends

| Backend                        | Strengths                                              |
| ------------------------------ | ------------------------------------------------------ |
| Tempo                          | Cheap object-storage backend, integrates with Grafana  |
| Jaeger                         | Mature UI, good for self-hosted                        |
| Zipkin                         | Lightweight, OK if already in use                      |
| Honeycomb / Datadog / NewRelic | SaaS — pay for retention and high-cardinality querying |

## Span attributes — semantic conventions

Use [OTel semantic conventions](https://opentelemetry.io/docs/specs/semconv/) for attribute
names; tooling depends on them.

| Attribute                    | Example                |
| ---------------------------- | ---------------------- |
| `http.request.method`        | `GET`                  |
| `http.route`                 | `/users/:id`           |
| `http.response.status_code`  | `200`                  |
| `db.system`                  | `postgresql`           |
| `db.statement`               | `SELECT id FROM users` |
| `messaging.system`           | `kafka`                |
| `messaging.destination.name` | `orders`               |
| `rpc.system`                 | `grpc`                 |
| `error.type`                 | Exception class        |

## Anti-patterns

- 100% sampling in prod with no tail filtering — explodes storage cost
- Spans too coarse (only one span per request) — defeats the purpose
- Spans too fine (one span per loop iteration) — drowns the UI
- Logging the trace ID but not propagating `traceparent` to downstream calls — breaks the trace
- Putting PII or large payloads in span attributes — they ship to backend in plaintext
- Forgetting to flush on shutdown — last few spans get dropped (call `provider.shutdown()`)
- Mixing trace SDKs across services — use OTel everywhere for one consistent context
