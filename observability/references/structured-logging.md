# Structured Logging (Python and Rust)

Production logs must be machine-parseable JSON with consistent fields. This guide covers
configuration, level semantics, contextual fields, correlation IDs, PII redaction, and sampling.

## Table of Contents

- [Python: structlog](#python-structlog)
- [Python: standard logging fallback](#python-standard-logging-fallback)
- [Rust: tracing](#rust-tracing)
- [Correlation IDs](#correlation-ids)
- [PII and secret redaction](#pii-and-secret-redaction)
- [High-volume sampling](#high-volume-sampling)
- [Anti-patterns](#anti-patterns)

## Python: structlog

`structlog` is the recommended Python logger. JSON in prod, key=value in dev.

### Configuration

```python
import logging
import sys

import structlog


def configure_logging(level: str = "INFO", json: bool = True) -> None:
    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=True)

    shared_processors: list = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        timestamper,
    ]

    renderer = (
        structlog.processors.JSONRenderer()
        if json
        else structlog.dev.ConsoleRenderer(colors=sys.stderr.isatty())
    )

    structlog.configure(
        processors=[*shared_processors, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(getattr(logging, level)),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
```

### Usage

```python
log = structlog.get_logger()

log.info("order_created", order_id=order.id, user_id=user.id, total=order.total)

try:
    charge(order)
except PaymentError as exc:
    log.error("payment_failed", order_id=order.id, error_type=type(exc).__name__, exc_info=exc)
    raise
```

### Bind context across a request

```python
log = structlog.get_logger().bind(request_id=req.id, user_id=req.user.id)
log.info("request_received", method=req.method, route=req.route)
# Subsequent calls inherit request_id and user_id automatically.
```

## Python: standard logging fallback

When a dependency forces `logging`, configure a JSON formatter so output stays uniform.

```python
import json
import logging
from datetime import datetime, timezone


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "@timestamp": datetime.now(timezone.utc).isoformat(),
            "log.level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["error.stack_trace"] = self.formatException(record.exc_info)
        for key, value in record.__dict__.get("extra", {}).items():
            payload[key] = value
        return json.dumps(payload, default=str)


handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())
logging.basicConfig(level=logging.INFO, handlers=[handler])
```

## Rust: tracing

The `tracing` crate is the de-facto Rust observability backbone. It unifies logs and spans and
integrates with OpenTelemetry, Tokio, and `tower`.

### Setup

`Cargo.toml`:

```toml
[dependencies]
tracing = "0.1"
tracing-subscriber = { version = "0.3", features = ["env-filter", "json", "fmt"] }
```

`main.rs`:

```rust
use tracing_subscriber::{fmt, prelude::*, EnvFilter};

fn init_telemetry() {
    let filter = EnvFilter::try_from_default_env().unwrap_or_else(|_| EnvFilter::new("info"));

    tracing_subscriber::registry()
        .with(filter)
        .with(fmt::layer().json().with_current_span(true).with_span_list(false))
        .init();
}
```

Set `RUST_LOG=info,my_crate=debug` to control levels at runtime.

### Events

```rust
use tracing::{debug, error, info, warn};

info!(order_id = %order.id, user_id = %user.id, total = order.total, "order_created");

if let Err(err) = charge(&order) {
    error!(order_id = %order.id, error = ?err, "payment_failed");
    return Err(err);
}
```

Use `%value` for `Display`, `?value` for `Debug`, plain `field = expr` for primitives.

### Spans (mandatory for async)

Spans give every event request-scoped context. Use `#[tracing::instrument]` on hot functions:

```rust
#[tracing::instrument(skip(db), fields(user_id = %user.id))]
async fn create_order(db: &Database, user: &User, items: &[Item]) -> Result<Order, Error> {
    tracing::info!(item_count = items.len(), "creating order");
    let order = db.insert_order(user.id, items).await?;
    tracing::info!(order_id = %order.id, "order persisted");
    Ok(order)
}
```

`#[instrument]` automatically opens a span, records arguments (use `skip` for non-`Debug` types
like DB pools), and attaches every event inside the function to that span.

## Correlation IDs

A correlation ID (or trace ID) connects every log line for one request across services.

### Python (FastAPI middleware + contextvars)

```python
import uuid
from contextvars import ContextVar

import structlog
from fastapi import Request

correlation_id: ContextVar[str] = ContextVar("correlation_id", default="")


async def correlation_middleware(request: Request, call_next):
    cid = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
    correlation_id.set(cid)
    structlog.contextvars.bind_contextvars(correlation_id=cid)
    try:
        response = await call_next(request)
    finally:
        structlog.contextvars.clear_contextvars()
    response.headers["X-Correlation-ID"] = cid
    return response
```

Propagate to outbound HTTP:

```python
import httpx

async def call_downstream(url: str, payload: dict) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            url,
            json=payload,
            headers={"X-Correlation-ID": correlation_id.get()},
        )
        resp.raise_for_status()
        return resp.json()
```

### Rust (axum middleware)

```rust
use axum::{extract::Request, middleware::Next, response::Response};
use tracing::Instrument;
use uuid::Uuid;

pub async fn correlation(mut req: Request, next: Next) -> Response {
    let cid = req
        .headers()
        .get("x-correlation-id")
        .and_then(|h| h.to_str().ok())
        .map(String::from)
        .unwrap_or_else(|| Uuid::new_v4().to_string());

    let span = tracing::info_span!("http_request", correlation_id = %cid);
    req.headers_mut().insert("x-correlation-id", cid.parse().unwrap());

    next.run(req).instrument(span).await
}
```

Prefer the W3C standard `traceparent` header when integrating with OpenTelemetry — see
[tracing.md](tracing.md).

## PII and secret redaction

Redact at the **logger boundary** so sensitive values never enter the pipeline. After-the-fact
scrubbing always misses things.

### Field denylist (Python)

```python
SENSITIVE = {"password", "token", "secret", "api_key", "authorization", "ssn", "credit_card"}


def redact_processor(logger, method_name, event_dict):
    for key in list(event_dict):
        lk = key.lower()
        if any(s in lk for s in SENSITIVE):
            event_dict[key] = "[REDACTED]"
    return event_dict


structlog.configure(
    processors=[
        redact_processor,  # add before JSONRenderer
        structlog.processors.JSONRenderer(),
    ],
)
```

### Masking helpers

```python
def mask_email(email: str) -> str:
    local, _, domain = email.partition("@")
    if len(local) <= 2:
        return f"*@{domain}"
    return f"{local[0]}{'*' * (len(local) - 2)}{local[-1]}@{domain}"


def mask_card(pan: str) -> str:
    digits = "".join(c for c in pan if c.isdigit())
    return "*" * (len(digits) - 4) + digits[-4:]
```

### Rust — `tracing` field redaction

Wrap sensitive types in a newtype with a custom `Debug`/`Display`:

```rust
pub struct Redacted<T>(pub T);

impl<T> std::fmt::Debug for Redacted<T> {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "[REDACTED]")
    }
}

impl<T> std::fmt::Display for Redacted<T> {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "[REDACTED]")
    }
}

// usage
let token = Redacted(api_token);
tracing::info!(?token, "auth_attempt");  // logs token = [REDACTED]
```

## High-volume sampling

For services emitting > ~1k INFO logs/sec, sample to control cost. Always keep WARN/ERROR.

### Python — random sample wrapper

```python
import random
import structlog

_log = structlog.get_logger()


class SampledLogger:
    def __init__(self, rate: float = 0.1) -> None:
        self.rate = rate

    def info(self, event: str, **fields) -> None:
        if random.random() < self.rate:
            _log.info(event, sampled=True, sample_rate=self.rate, **fields)

    def warning(self, event: str, **fields) -> None:
        _log.warning(event, **fields)

    def error(self, event: str, **fields) -> None:
        _log.error(event, **fields)
```

### Consistent (per-user) sampling

Hash the user/correlation ID so a given user is either always or never sampled:

```python
import hashlib

def is_sampled(key: str, rate: float) -> bool:
    digest = hashlib.blake2s(key.encode(), digest_size=4).digest()
    bucket = int.from_bytes(digest, "big") % 100
    return bucket < rate * 100
```

### Rust — `tracing-subscriber` sampling layer

```rust
use tracing::{Event, Subscriber};
use tracing_subscriber::{layer::Context, Layer};

pub struct SamplingLayer { rate: f64 }

impl<S: Subscriber> Layer<S> for SamplingLayer {
    fn event_enabled(&self, event: &Event<'_>, _ctx: Context<'_, S>) -> bool {
        if event.metadata().level() <= &tracing::Level::WARN {
            return true;  // always keep WARN/ERROR
        }
        rand::random::<f64>() < self.rate
    }
}
```

## Anti-patterns

- `print(...)` / `println!(...)` in library or service code — bypasses formatters and routing
- `logger.info(f"user {id}")` — string interpolation kills structured search
- Logging entire request/response bodies — leaks PII and balloons cost
- Logging the same error at multiple layers — one log per failure, at the boundary that handled it
- Blocking I/O in the logging path on a hot request — buffer or use a background appender
- DEBUG logs left enabled in production by default
