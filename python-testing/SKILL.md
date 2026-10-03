---
name: python-testing
description: >-
  Use before writing or changing Python tests (test_*.py, conftest.py, pytest config) or when
  coverage falls short. Covers pytest fixtures, mocking, parameterization, async tests, coverage,
  and property-based testing, with arrange-act-assert structure and TDD.
---

# Python Testing

Comprehensive pytest patterns following TDD methodology.

## Preferred Plugins

New projects get the house pytest stack in the `dev` group (add `pytest-asyncio` for async code):

```bash
uv add --group dev pytest pytest-cov pytest-html pytest-metadata pytest-sugar pytest-xdist
```

In an existing repo, use the plugins it already has and ask before adding more.

| Plugin | Purpose |
| --- | --- |
| `pytest-cov` | Coverage reporting (`--cov`, `--cov-report`) |
| `pytest-html`     | HTML test reports (`--html=report.html`)     |
| `pytest-metadata` | Test session metadata for reports            |
| `pytest-sugar`    | Progress bar and instant failure display     |
| `pytest-xdist`    | Parallel test execution (`-n auto`)          |
| `pytest-asyncio`  | Async test support (`@pytest.mark.asyncio`)  |

## TDD Cycle

1. **RED** — Write one failing test, run `.venv/bin/pytest`, confirm failure
2. **GREEN** — Write minimum code to pass
3. **REFACTOR** — Improve structure, keep tests green
4. **Repeat** — Next behavior, next failing test

## Arrange-Act-Assert

Every test uses the three labeled phases; the full rule, including the `# Act & Assert` form and
how to convert an existing file, is in the
[test-driven-development](../test-driven-development/SKILL.md#test-structure-arrange-act-assert)
skill.

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
    # Arrange
    repo = UserRepository(db_session)

    # Act
    user = repo.save(User(name="Alice"))

    # Assert
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
    # Act
    result = parse_int(input_val)

    # Assert
    assert result == expected
```

## Mocking

```python
from unittest.mock import Mock


def test_api_call_retries_on_failure() -> None:
    # Arrange
    client = Mock(spec=HttpClient)
    client.get.side_effect = [
        ConnectionError("timeout"),
        ConnectionError("timeout"),
        Response(status=200, body="ok"),
    ]
    service = DataService(client=client)

    # Act
    result = service.fetch_data()

    # Assert
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
    # Act & Assert
    with pytest.raises(ValueError, match="must be positive"):
        transfer(amount=-100)
```

## Async Tests

```python
import pytest


@pytest.mark.asyncio
async def test_fetch_user_returns_parsed_name() -> None:
    # Arrange
    client = FakeHttpClient(responses={"/users/1": {"name": "Alice"}})

    # Act
    user = await fetch_user(client, user_id=1)

    # Assert
    assert user.name == "Alice"
```

- Use `pytest-asyncio` plugin
- Add it with `uv add --group dev pytest-asyncio`
- Test timeouts with `asyncio.wait_for`

## Monkeypatching

```python
def test_reads_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    monkeypatch.setenv("API_KEY", "test-key")

    # Act
    config = load_config()

    # Assert
    assert config.api_key == "test-key"
```

## Coverage

```bash
.venv/bin/pytest --cov=myproject --cov-report=term-missing
.venv/bin/pytest --cov=myproject --cov-report=html
.venv/bin/pytest --cov=myproject --cov-report=annotate:cov_annotate
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
    # Arrange
    once = sorted(xs)

    # Act
    twice = sorted(once)

    # Assert
    assert twice == once
```

## Time-Dependent Tests (freezegun)

```python
from freezegun import freeze_time


@freeze_time("2025-01-15 12:00:00")
def test_report_uses_current_date() -> None:
    # Act
    report = generate_report()

    # Assert
    assert report.date == date(2025, 1, 15)
```

## Test Markers

```python
@pytest.mark.slow
def test_full_integration() -> None: ...


@pytest.mark.integration
def test_db_roundtrip() -> None: ...
```

Run selectively: `.venv/bin/pytest -m "not slow"`

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
# Warnings fail tests; silence a third-party module only by name, with a reason, e.g.
# "ignore::DeprecationWarning:somelib.*".
filterwarnings = ["error"]
# Only when tests import shared helpers as `tests.*`; src layouts import the installed project.
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

Parallel execution: `.venv/bin/pytest -n auto`

## Anti-Patterns

- **No testing mock behavior** — test real components
- **No test-only methods in production code** — put in test utils
- **No mocking without understanding** — know the real behavior
- **No incomplete mocks** — mirror the real API completely
- **No tests that always pass** — watch each test fail first
- **No unlabeled phases** — every test uses `# Arrange`, `# Act`, `# Assert`

## Related Skills

- [python](../python/SKILL.md) — core Python style and project layout
- [python-type-safety](../python-type-safety/SKILL.md) — stronger contracts for refactors and test
    doubles
- [python-anti-patterns](../python-anti-patterns/SKILL.md) — review checklist for weak tests and
    mocking mistakes
- [test-driven-development](../test-driven-development/SKILL.md) — write the failing test first
- [systematic-debugging](../systematic-debugging/SKILL.md) — reproduce a bug as a failing test
  before fixing
