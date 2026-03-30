---
name: python-infrastructure
description: Python infrastructure patterns covering packaging (pyproject.toml, PyPI), performance optimization (profiling, caching), background jobs (Celery, task queues), and deployment workflows. Use when packaging libraries, optimizing performance, or building async task processing systems.
---

# Python Infrastructure

Packaging, performance, background jobs, and deployment patterns.

## Packaging

### Project Layout (Source Layout)

```text
src/
  mypackage/
    __init__.py
    py.typed
    core.py
pyproject.toml
README.md
LICENSE
tests/
```

### pyproject.toml

```toml
[build-system]
requires = ["setuptools>=68.0"]
build-backend = "setuptools.backends._legacy:_Backend"

[project]
name = "mypackage"
version = "0.1.0"
description = "What it does"
requires-python = ">=3.12"
license = {text = "MIT"}
dependencies = ["pydantic>=2.0"]

[project.optional-dependencies]
dev = ["pytest", "ruff", "mypy"]

[project.scripts]
mycli = "mypackage.cli:main"

[tool.setuptools.packages.find]
where = ["src"]
```

- Include `py.typed` for type hint discovery
- Use `[project.scripts]` for CLI entry points
- Build: `python -m build`
- Publish: test on TestPyPI first, then `twine upload dist/*`

## Performance Optimization

### Profiling (always profile first)

```bash
python -m cProfile -o output.prof script.py   # CPU
kernprof -l -v script.py                       # line-by-line
python -m memory_profiler script.py             # memory
py-spy record -o profile.svg -- python script.py  # production
```

### Key Optimization Patterns

- **List comprehensions** beat loops by 10–50%
- **Generators** for large datasets — constant memory
- **`"".join(parts)`** not `result += item` — O(n) vs O(n²)
- **Dict lookups** are O(1) vs list search O(n)
- **Local variables** are 5–10% faster than globals in tight loops
- **`@lru_cache`** for expensive pure computations
- **`__slots__`** reduces per-instance memory for many objects
- **NumPy vectorization** beats Python loops by 100–1000× for numerical work

### Concurrency Strategy

- I/O-bound → `asyncio`
- CPU-bound → `multiprocessing.Pool`
- Mixed → `asyncio.to_thread()` for blocking calls

### Database

- Batch operations: single commit beats 1000 individual commits
- Use connection pooling (SQLAlchemy pool, asyncpg pool)

## Background Jobs

### When to Use

Return a job ID immediately for operations exceeding a few seconds. Process asynchronously via task
queue.

### Celery Setup

```python
from celery import Celery

app = Celery("tasks", broker="redis://localhost:6379/0")
app.conf.update(
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
)

@app.task(
    bind=True,
    max_retries=3,
    soft_time_limit=3000,
    time_limit=3600,
)
def process_order(self, order_id: str) -> None:
    try:
        do_work(order_id)
    except TransientError as exc:
        raise self.retry(
            exc=exc,
            countdown=2 ** self.request.retries * 60,
        )
```

### Key Principles

- **Idempotency:** Retries must be safe — check state before acting, use idempotency keys with
  external services
- **Job states:** `pending → running → succeeded | failed`
- **Only retry transient failures** — validation errors and bad credentials fail permanently
- **Exponential backoff:** `2^attempt * base_delay`, capped
- **Dead letter queue:** Move permanently failed tasks to DLQ after max retries for manual
  inspection
- **Status polling:** Expose a `GET /jobs/{id}` endpoint for clients to check progress

### Task Composition

```python
from celery import chain, group, chord

# Sequential
chain(step1.s(), step2.s(), step3.s())()

# Parallel
group(task.s(item) for item in items)()

# Parallel + callback
chord(group(task.s(i) for i in items))(summarize.s())
```

### Alternatives

| Queue    | Best For                         |
| -------- | -------------------------------- |
| Celery   | Full-featured, complex workflows |
| RQ       | Simple Redis-backed queues       |
| Dramatiq | Celery alternative, simpler API  |
| AWS SQS  | Cloud-native, serverless         |
