# Python Configuration — Detailed Patterns

## Fail-Fast Startup

Create the settings object during process startup so missing or invalid configuration breaks early.

```python
from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    api_key: str = Field(alias="API_KEY")
    database_url: str = Field(alias="DATABASE_URL")


try:
    settings = Settings()
except ValidationError as exc:
    msg = f"Configuration error: {exc}"
    raise SystemExit(msg) from exc
```

## Environment-Specific Behavior

Use an explicit environment field rather than scattered string comparisons.

```python
from enum import StrEnum


class Environment(StrEnum):
    LOCAL = "local"
    STAGING = "staging"
    PRODUCTION = "production"
```

- Keep the allowed environment values narrow.
- Derive helper properties such as `is_production` inside the settings layer.

## Nested Settings

Use nested models when a deployable has several configuration groups.

```python
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseModel):
    host: str = "localhost"
    port: int = 5432
    name: str


class RedisSettings(BaseModel):
    url: str = "redis://localhost:6379"


class Settings(BaseSettings):
    database: DatabaseSettings
    redis: RedisSettings

    model_config = SettingsConfigDict(env_nested_delimiter="__")
```

Environment variables then read naturally, such as `DATABASE__HOST`.

## Secrets Files

When the runtime mounts secrets as files, configure a secrets directory instead of reading files
manually at call sites.

```python
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    db_password: str = Field(alias="DB_PASSWORD")

    model_config = SettingsConfigDict(secrets_dir="/run/secrets")
```

## Parsing and Normalization

Normalize values inside the settings type so callers do not reimplement parsing.

```python
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    allowed_hosts: list[str] = Field(default_factory=list, alias="ALLOWED_HOSTS")

    @field_validator("allowed_hosts", mode="before")
    @classmethod
    def parse_allowed_hosts(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [host.strip() for host in value.split(",") if host.strip()]
        return value
```

## Test Overrides

- Inject a settings object directly when code structure allows it.
- Use `monkeypatch.setenv` for thin integration tests.
- Prefer explicit fixtures over hidden global mutation.# python-configuration — detailed worked examples

## Advanced Patterns

### Pattern 5: Type Coercion

Pydantic handles common conversions automatically.

```python
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator

class Settings(BaseSettings):
    # Automatically converts "true", "1", "yes" to True
    debug: bool = False

    # Automatically converts string to int
    max_connections: int = 100

    # Parse comma-separated string to list
    allowed_hosts: list[str] = Field(default_factory=list)

    @field_validator("allowed_hosts", mode="before")
    @classmethod
    def parse_allowed_hosts(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [host.strip() for host in v.split(",") if host.strip()]
        return v
```

Usage:

```bash
ALLOWED_HOSTS=example.com,api.example.com,localhost
MAX_CONNECTIONS=50
DEBUG=true
```

### Pattern 6: Environment-Specific Configuration

Use an environment enum to switch behavior.

```python
from enum import StrEnum
from pydantic_settings import BaseSettings
from pydantic import Field, computed_field

class Environment(StrEnum):
    LOCAL = "local"
    STAGING = "staging"
    PRODUCTION = "production"

class Settings(BaseSettings):
    environment: Environment = Field(
        default=Environment.LOCAL,
        alias="ENVIRONMENT",
    )

    # Settings that vary by environment
    log_level: str = Field(default="DEBUG", alias="LOG_LEVEL")

    @computed_field
    @property
    def is_production(self) -> bool:
        return self.environment == Environment.PRODUCTION

    @computed_field
    @property
    def is_local(self) -> bool:
        return self.environment == Environment.LOCAL

# Usage
if settings.is_production:
    configure_production_logging()
else:
    configure_debug_logging()
```

### Pattern 7: Nested Configuration Groups

Organize related settings into nested models.

```python
from pydantic import BaseModel
from pydantic_settings import BaseSettings

class DatabaseSettings(BaseModel):
    host: str = "localhost"
    port: int = 5432
    name: str
    user: str
    password: str

class RedisSettings(BaseModel):
    url: str = "redis://localhost:6379"
    max_connections: int = 10

class Settings(BaseSettings):
    database: DatabaseSettings
    redis: RedisSettings
    debug: bool = False

    model_config = {
        "env_nested_delimiter": "__",
        "env_file": ".env",
    }
```

Environment variables use double underscore for nesting:

```bash
DATABASE__HOST=db.example.com
DATABASE__PORT=5432
DATABASE__NAME=myapp
DATABASE__USER=admin
DATABASE__PASSWORD=secret
REDIS__URL=redis://redis.example.com:6379
```

### Pattern 8: Secrets from Files

For container environments, read secrets from mounted files.

```python
from pydantic_settings import BaseSettings
from pydantic import Field
from pathlib import Path

class Settings(BaseSettings):
    # Read from environment variable or file
    db_password: str = Field(alias="DB_PASSWORD")

    model_config = {
        "secrets_dir": "/run/secrets",  # Docker secrets location
    }
```

Pydantic will look for `/run/secrets/db_password` if the env var isn't set.

### Pattern 9: Configuration Validation

Add custom validation for complex requirements.

```python
from pydantic_settings import BaseSettings
from pydantic import Field, model_validator

class Settings(BaseSettings):
    db_host: str = Field(alias="DB_HOST")
    db_port: int = Field(alias="DB_PORT")
    read_replica_host: str | None = Field(default=None, alias="READ_REPLICA_HOST")
    read_replica_port: int = Field(default=5432, alias="READ_REPLICA_PORT")

    @model_validator(mode="after")
    def validate_replica_settings(self):
        if (
            self.read_replica_host == self.db_host
            and self.read_replica_port == self.db_port
        ):
            msg = "Read replica cannot be the same as primary database"
            raise ValueError(msg)
        return self
```
