---
name: python-configuration
description: >-
  Use before adding or changing how a Python app reads settings, environment variables, .env or
  secrets files, or CLI defaults, including any new os.getenv() call. Covers typed settings models,
  startup validation, and environment-specific behavior.
---

# Python Configuration

Use typed configuration objects to move environment-specific behavior out of business logic.

## Core Rules

- Load configuration once near process startup.
- Validate required settings immediately and fail fast.
- Keep secrets and environment-specific values out of source code.
- Pass settings inward instead of calling `os.getenv()` throughout the codebase.
- Give local development safe defaults only for non-sensitive settings.

## Default Pattern

Use `pydantic-settings` when the project already depends on Pydantic or needs typed validation.

```python
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    environment: str = Field(default="local", alias="ENVIRONMENT")
    database_url: str = Field(alias="DATABASE_URL")
    redis_url: str = Field(default="redis://localhost:6379", alias="REDIS_URL")
    debug: bool = Field(default=False, alias="DEBUG")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
    )
```

## Design Guidance

- Keep one settings type per deployable unit or process.
- Separate runtime configuration from feature-level business toggles when that boundary matters.
- Namespace environment variables so they are easy to grep and audit.
- Keep parsing and normalization in the settings layer, not at every call site.
- Treat configuration errors as startup failures, not request-time surprises.

## Secrets and Deployment

- Never commit `.env` files with real secrets.
- Prefer secret managers or mounted secret files in production.
- Use `secrets_dir` when deploying to containers or Kubernetes.
- Avoid logging full config objects unless secret fields are redacted.

## Testing

- Override settings through fixtures or dependency injection.
- Use `monkeypatch` or temporary env files in tests.
- Test invalid, missing, and environment-specific values explicitly.

## Detailed Patterns

Detailed nested-settings, environment-selection, secret-file, and validation patterns live in
`references/details.md`.

## Anti-Patterns

- No hardcoded credentials or hostnames.
- No scattered `os.getenv()` calls across the codebase.
- No silently ignored missing settings.
- No config parsing mixed into request handlers or business logic.
- No production behavior controlled by undocumented environment variables.

## Related Skills

- [python](../python/SKILL.md) — core Python standards and project defaults
- [python-web-apis](../python-web-apis/SKILL.md) — injecting settings into API apps and handlers
- [python-resilience](../python-resilience/SKILL.md) — failing fast and exposing configuration
  problems safely
- [python-modernization](../python-modernization/SKILL.md) — upgrading legacy settings patterns
