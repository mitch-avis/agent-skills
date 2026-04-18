---
name: python-testing
description: >-
  Python testing with pytest, fixtures, mocking, parameterization, async tests, coverage, and
  property-based testing. Follows TDD methodology with arrange-act-assert pattern. Use when writing
  Python tests, setting up test infrastructure, or improving code coverage.
---

# Python Testing

Comprehensive pytest patterns following TDD methodology.

## Preferred Plugins

Install the standard pytest stack for all projects:

```bash
uv pip install pytest pytest-cov pytest-html pytest-metadata pytest-sugar pytest-xdist
```

| Plugin            | Purpose                                      |
| ----------------- | -------------------------------------------- |
| `pytest-cov`      | Coverage reporting (`--cov`, `--cov-report`) |
| `pytest-html`     | HTML test reports (`--html=report.html`)     |
| `pytest-metadata` | Test session metadata for reports            |
| `pytest-sugar`    | Progress bar and instant failure display     |
| `pytest-xdist`    | Parallel test execution (`-n auto`)          |
| `pytest-asyncio`  | Async test support (`@pytest.mark.asyncio`)  |

## TDD Cycle

1. **RED** — Write one failing test, run `pytest`, confirm failure
2. **GREEN** — Write minimum code to pass
3. **REFACTOR** — Improve structure, keep tests green
4. **Repeat** — Next behavior, next failing test

## Arrange-Act-Assert

```python
def test_user_creation_sends_welcome_email() -> None:
    # Arrange
    notifier = Mock(spec=Notifier)
    service = UserService(notifier=notifier)

    # Act
    user = service.create(name="Alice", email="a@b.com")

    # Assert
    assert user.name == "Alice"
    notifier.send_welcome.assert_called_once_with(user)
```

## Test Naming

`test_<unit>_<scenario>_<expected>`:

- `test_parse_valid_json_returns_dict`
- `test_transfer_negative_amount_raises_value_error`
- `test_cache_full_evicts_oldest_entry`

## Fixtures

```python
@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    session = create_session()
    yield session
    session.rollback()
    session.close()

def test_save_user(db_session: Session) -> None:
    repo = UserRepository(db_session)
    user = repo.save(User(name="Alice"))
    assert user.id is not None
```

- `scope="function"` (default) — per test
- `scope="module"` — per test file
- `scope="session"` — once per test run
- Place shared fixtures in `conftest.py`

## Parameterized Tests

```python
@pytest.mark.parametrize(
    ("input_val", "expected"),
    [
        ("42", 42),
        ("-1", -1),
        ("0", 0),
    ],
)
def test_parse_int(input_val: str, expected: int) -> None:
    assert parse_int(input_val) == expected
```

## Mocking

```python
from unittest.mock import Mock, patch

def test_api_call_retries_on_failure() -> None:
    client = Mock(spec=HttpClient)
    client.get.side_effect = [
        ConnectionError("timeout"),
        ConnectionError("timeout"),
        Response(status=200, body="ok"),
    ]
    service = DataService(client=client)

    result = service.fetch_data()

    assert result == "ok"
    assert client.get.call_count == 3
```

- Mock at the boundary, not deep internals
- Use `spec=RealClass` to catch API changes
- Use `side_effect` for sequences of return values
- Prefer dependency injection over `patch` where possible

## Exception Testing

```python
def test_invalid_amount_raises() -> None:
    with pytest.raises(ValueError, match="must be positive"):
        transfer(amount=-100)
```

## Async Tests

```python
import pytest

@pytest.mark.asyncio
async def test_fetch_returns_data() -> None:
    result = await fetch("https://example.com")
    assert "Example" in result
```

- Use `pytest-asyncio` plugin
- Test timeouts with `asyncio.wait_for`

## Monkeypatching

```python
def test_reads_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("API_KEY", "test-key")
    config = load_config()
    assert config.api_key == "test-key"
```

## Coverage

```bash
pytest --cov=myproject --cov-report=term-missing
pytest --cov=myproject --cov-report=html
pytest --cov=myproject --cov-report=annotate:cov_annotate
```

- Lines starting with `!` in annotated files are uncovered
- Write tests to cover marked lines incrementally
- Target 100% coverage wherever achievable

## Property-Based Testing (Hypothesis)

```python
from hypothesis import given
from hypothesis import strategies as st

@given(st.lists(st.integers()))
def test_sort_is_idempotent(xs: list[int]) -> None:
    assert sorted(sorted(xs)) == sorted(xs)
```

## Time-Dependent Tests (freezegun)

```python
from freezegun import freeze_time

@freeze_time("2025-01-15 12:00:00")
def test_report_uses_current_date() -> None:
    report = generate_report()
    assert report.date == date(2025, 1, 15)
```

## Test Markers

```python
@pytest.mark.slow
def test_full_integration() -> None: ...

@pytest.mark.integration
def test_db_roundtrip() -> None: ...
```

Run selectively: `pytest -m "not slow"`

## CI Configuration

```toml
[tool.pytest.ini_options]
minversion = "7.0"
testpaths = ["tests"]
addopts = [
    "-ra",
    "--strict-markers",
    "--cov=myproject",
    "--cov-report=term-missing",
]
filterwarnings = ["ignore::DeprecationWarning"]
pythonpath = ["."]
markers = [
    "slow: marks tests as slow",
    "integration: marks integration tests",
]

[tool.coverage.run]
branch = true
source = ["myproject"]

[tool.coverage.report]
show_missing = true
skip_empty = true
exclude_lines = ["pragma: no cover", "if __name__ == \"__main__\":"]
```

Run selectively: `pytest -m "not slow"`

Parallel execution: `pytest -n auto`

## Anti-Patterns

- **No testing mock behavior** — test real components
- **No test-only methods in production code** — put in test utils
- **No mocking without understanding** — know the real behavior
- **No incomplete mocks** — mirror the real API completely
- **No tests that always pass** — watch each test fail first
