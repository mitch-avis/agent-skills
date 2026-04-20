---
name: sql-database
description: >-
  SQL database design and operations across PostgreSQL, MySQL, and SQLite — covering schema
  modeling, data types, indexing strategy, migrations, query patterns, ORM integration
  (SQLAlchemy, Diesel, SQLx), connection pooling, EXPLAIN analysis, and dialect-specific
  gotchas. Use when designing schemas, writing migrations, choosing indexes, debugging slow
  queries, reviewing SQL for security or correctness, or integrating a relational database
  into a Python or Rust project.
---

# SQL Database

Design, query, and operate relational databases safely and performantly. Multi-dialect (PostgreSQL,
MySQL, SQLite) with explicit guidance per engine where it matters.

## When to Use

- Designing or reviewing schemas, indexes, or constraints
- Writing migrations or evolving a deployed schema safely
- Tuning slow queries or interpreting `EXPLAIN` output
- Choosing between SQL engines for a new service
- Integrating SQLAlchemy, Diesel, SQLx, or another ORM/query builder
- Reviewing SQL for injection risk, N+1 queries, or other anti-patterns

## Related Skills

- **python** — load alongside for SQLAlchemy / asyncpg integration
- **rust** — load alongside for Diesel / SQLx / SeaORM integration
- **security** — load when reviewing access control, RLS, or secrets handling
- **performance-profiling** — load when measuring before/after query changes

## Reference Guides

Load on demand — do not read all files upfront.

| Topic                | File                              | Load When                                       |
| -------------------- | --------------------------------- | ----------------------------------------------- |
| Indexing strategy    | references/indexing.md            | Designing or auditing indexes                   |
| Query patterns       | references/query-patterns.md      | Tuning, pagination, N+1, EXPLAIN deep dives     |
| PostgreSQL specifics | references/postgresql.md          | JSONB, arrays, RLS, MVCC, type quirks           |
| MySQL specifics      | references/mysql.md               | InnoDB, online DDL, isolation, partitioning     |
| SQLite specifics     | references/sqlite.md              | Embedded apps, FTS5, WAL mode, pragmas          |

## Iron Laws

1. **Always parameterize.** Never concatenate or interpolate user input into SQL strings.
2. **Always profile with `EXPLAIN`.** Decisions about indexes and query shape need evidence.
3. **Always migrate.** Every DDL change goes through a versioned migration with a rollback path.
4. **Never `SELECT *` in application code.** Name the columns you need.
5. **Never trust the optimizer for arbitrary input.** Add the indexes that hot paths require.

## Schema Design

### Normalization

Start in 3rd normal form. Denormalize only after measurement proves a join is the bottleneck.
Premature denormalization creates update anomalies and maintenance burden.

### Primary Keys

| Engine     | Recommended PK                              | Notes                                           |
| ---------- | ------------------------------------------- | ----------------------------------------------- |
| PostgreSQL | `BIGINT GENERATED ALWAYS AS IDENTITY`       | Use `uuidv7()` (PG18+) only when needed         |
| MySQL      | `BIGINT UNSIGNED AUTO_INCREMENT`            | InnoDB clusters by PK — keep narrow + monotonic |
| SQLite     | `INTEGER PRIMARY KEY`                       | Aliases `ROWID`; do not use `BIGINT`            |

- Avoid random UUIDs (UUIDv4) as **clustered** PKs — they fragment the heap and bloat indexes.
- If global uniqueness is required, store the UUID in a secondary `UNIQUE` column.
- Sequences and auto-increment counters have **gaps** after rollbacks or crashes — this is expected,
  not a bug. Do not try to make IDs consecutive.

### Foreign Keys

- Always declare FKs at the database level. Application-only referential integrity drifts.
- Specify `ON DELETE` / `ON UPDATE` behavior explicitly (`CASCADE`, `RESTRICT`, `SET NULL`).
- **PostgreSQL and MySQL do not auto-index FK columns.** Add the index manually — without it, joins
  are slow and `DELETE` on the parent acquires a full-table lock.
- **SQLite**: enable FKs explicitly per connection: `PRAGMA foreign_keys = ON;`.

### Naming Conventions

- `snake_case` for tables, columns, constraints, and indexes
- Singular table names (`user`, `order`) — match the row, not the collection
- `_id` suffix for foreign keys (`customer_id`, not `customer`)
- Constraint names: `pk_<table>`, `fk_<table>_<column>`, `uq_<table>_<column>`,
  `idx_<table>_<column>`
- PostgreSQL lowercases unquoted identifiers — never quote a mixed-case name into existence

### Required Columns

Every reference table gets:

- A primary key
- `created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()` (or dialect equivalent)
- `updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()` with a trigger or ORM hook
- Indexes on every FK and every queried column

## Data Types

| Purpose            | PostgreSQL                              | MySQL                              | SQLite                |
| ------------------ | --------------------------------------- | ---------------------------------- | --------------------- |
| Integer ID         | `BIGINT GENERATED ALWAYS AS IDENTITY`   | `BIGINT UNSIGNED AUTO_INCREMENT`   | `INTEGER PRIMARY KEY` |
| Timestamp          | `TIMESTAMPTZ`                           | `DATETIME(6)`                      | `TEXT` (ISO-8601)     |
| Money / decimal    | `NUMERIC(p, s)`                         | `DECIMAL(p, s)`                    | `NUMERIC`             |
| Variable text      | `TEXT`                                  | `VARCHAR(n)` + `utf8mb4`           | `TEXT`                |
| Boolean            | `BOOLEAN`                               | `TINYINT(1)`                       | `INTEGER` 0/1         |
| JSON               | `JSONB` (always — never `JSON`)         | `JSON`                             | `TEXT` + JSON1 ext.   |
| Enum               | `CREATE TYPE foo AS ENUM (...)`         | lookup table (preferred)           | `TEXT` + `CHECK`      |
| UUID               | `UUID`                                  | `BINARY(16)` (use `UUID_TO_BIN`)   | `BLOB` or `TEXT`      |
| Bytes              | `BYTEA`                                 | `VARBINARY(n)` / `BLOB`            | `BLOB`                |

### Universal Type Rules

- **Money is `NUMERIC` / `DECIMAL`, never `FLOAT` or `DOUBLE`.** Floats lose pennies.
- **Timestamps are timezone-aware.** Store UTC; convert at the edge.
- **Use the smallest type that fits** — narrower rows mean more rows per page and better cache
  behavior.
- **`NOT NULL` everywhere it is semantically required.** Provide `DEFAULT` for common values.

### PostgreSQL Type Notes

- Prefer `TEXT` over `VARCHAR(n)` — there is no performance difference and length limits belong in
  `CHECK` constraints.
- Prefer `TIMESTAMPTZ` — never `TIMESTAMP` (no timezone), `TIMETZ`, or `TIMESTAMP(n)`.
- Avoid: `SERIAL` / `BIGSERIAL` (use `IDENTITY`), `MONEY` (use `NUMERIC`), `CHAR(n)`.
- Use `CITEXT` (or an expression index on `LOWER(col)`) for case-insensitive lookups.

### MySQL Type Notes

- Default charset / collation: `utf8mb4` / `utf8mb4_0900_ai_ci`. Plain `utf8` is **not** UTF-8.
- Prefer `DATETIME` over `TIMESTAMP` — `TIMESTAMP` has a 2038 cliff and timezone surprises.
- `ENUM` bakes values into the schema and is hard to evolve — use a lookup table instead.

## Indexing

Quick rules. See [references/indexing.md](references/indexing.md) for full design patterns.

### What to Index

- Columns appearing in `WHERE`, `JOIN`, `ORDER BY`, or `GROUP BY`
- Every foreign key column (manual, not automatic)
- Columns frequently filtered together — as a single composite index

### Composite Index Order

**Leftmost-prefix rule:** equality predicates first, then range, then sort.

```sql
-- Query: WHERE user_id = ? AND status = ? AND created_at > ? ORDER BY created_at
CREATE INDEX idx_orders_user_status_created
  ON orders (user_id, status, created_at DESC);
```

A range predicate (`>`, `<`, `BETWEEN`) stops index usage for columns that follow it.

### Index Types Worth Knowing

- **Covering / `INCLUDE`** — non-key columns added to enable index-only scans.
- **Partial** (PostgreSQL, SQLite) — `... WHERE status = 'active'` shrinks index to hot rows.
- **Expression** — `INDEX ON users (LOWER(email))` for case-insensitive matches.
- **PostgreSQL GIN** — `JSONB`, arrays, full-text search.
- **PostgreSQL GiST** — ranges, geometry, exclusion constraints.
- **MySQL `FULLTEXT`** — text search via `MATCH ... AGAINST`.
- **SQLite FTS5** — virtual table for full-text search.

### Avoid Over-Indexing

Every index slows writes and consumes storage. Audit periodically:

```sql
-- PostgreSQL: indexes that have never been read
SELECT schemaname, relname, indexrelname, idx_scan
  FROM pg_stat_user_indexes
 WHERE idx_scan = 0;

-- MySQL 8.0+
SELECT object_schema, object_name, index_name
  FROM performance_schema.table_io_waits_summary_by_index_usage
 WHERE index_name IS NOT NULL AND count_star = 0;
```

## Query Patterns

See [references/query-patterns.md](references/query-patterns.md) for the full cookbook (pagination
styles, EXPLAIN walkthroughs, window functions, CTEs).

### Anti-Patterns to Avoid

| Anti-pattern              | Why it hurts                                 | Fix                                              |
| ------------------------- | -------------------------------------------- | ------------------------------------------------ |
| `SELECT *`                | Wastes I/O; breaks index-only scans          | Name the columns                                 |
| Function in `WHERE`       | `WHERE YEAR(created_at) = 2024` skips index  | `created_at >= '2024-01-01' AND <  '2025-01-01'` |
| `OFFSET` pagination       | `OFFSET 100000` re-scans skipped rows        | Cursor / keyset pagination                       |
| Correlated subquery       | Runs once per outer row                      | Convert to `JOIN` + `GROUP BY`, or window fn     |
| `DISTINCT` to fix joins   | Hides a missing or wrong join condition      | Fix the join; aggregate intentionally            |
| N+1 queries from ORM      | One query per parent row                     | Eager-load, batch-load, or join                  |
| Implicit `CROSS JOIN`     | Comma-separated `FROM` without `ON`          | Use explicit `INNER JOIN ... ON`                 |

### Cursor (Keyset) Pagination

```sql
-- BAD: OFFSET cost grows with offset
SELECT id, title, created_at
  FROM posts
 ORDER BY created_at DESC, id DESC
 LIMIT 20 OFFSET 100000;

-- GOOD: O(log n) lookup using the previous page's last (created_at, id)
SELECT id, title, created_at
  FROM posts
 WHERE (created_at, id) < ($1, $2)
 ORDER BY created_at DESC, id DESC
 LIMIT 20;
```

### Batch Writes

```sql
-- BAD: one round-trip per row
INSERT INTO products (name, price) VALUES ('A', 1);
INSERT INTO products (name, price) VALUES ('B', 2);

-- GOOD: one round-trip
INSERT INTO products (name, price) VALUES ('A', 1), ('B', 2), ('C', 3);

-- Better when many rows: COPY (PostgreSQL) or LOAD DATA INFILE (MySQL)
```

### `EXPLAIN` Quick Read

```sql
-- PostgreSQL
EXPLAIN (ANALYZE, BUFFERS) SELECT ... ;

-- MySQL 8.0+
EXPLAIN ANALYZE SELECT ... ;
EXPLAIN FORMAT=JSON SELECT ... ;
```

Red flags:

- **`Seq Scan` / `type: ALL`** on a large table — missing or unusable index
- **`Using filesort` / `Using temporary`** — `ORDER BY` or `GROUP BY` cannot use an index
- **Estimated rows ≪ actual rows** — run `ANALYZE <table>` to refresh statistics
- **Buffers: read** ≫ **shared hit** — cold cache or missing index, lots of disk I/O

## Migrations

### Versioning

- Track applied migrations in a `schema_migrations(version, name, applied_at)` table.
- Name migrations with a sequence and a verb: `0001_create_users.sql`, `0042_add_email_index.sql`.
- Each migration: one logical change. Never mix schema and large data backfills in one file.
- Provide an `up` and `down` (rollback) script for every migration.
- Never edit a deployed migration — write a new one that supersedes it.

### Safe Schema Evolution

- **Adding a column**: nullable + default `NULL` is instant. `NOT NULL` with a volatile default
  (`NOW()`, `gen_random_uuid()`) requires a full rewrite — backfill in batches first, then add the
  constraint.
- **Renaming a column**: do it in three deploys — add new, dual-write, drop old.
- **Adding indexes online**:
  - PostgreSQL: `CREATE INDEX CONCURRENTLY` (cannot run inside a transaction).
  - MySQL: `ALTER TABLE ... ADD INDEX, ALGORITHM=INPLACE, LOCK=NONE`.
- **DDL transactionality**: PostgreSQL wraps DDL in transactions; MySQL does not for most DDL.
- **Test on a production-shaped dataset** before deploying.

## ORM Integration

### SQLAlchemy (Python)

```python
from sqlalchemy import ForeignKey, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, selectinload


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "user"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(unique=True, index=True)
    orders: Mapped[list["Order"]] = relationship(back_populates="user")


class Order(Base):
    __tablename__ = "order"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True)
    user: Mapped[User] = relationship(back_populates="orders")


# N+1 prevention — eager-load with a single extra query.
stmt = select(User).options(selectinload(User.orders))
```

### SQLx (Rust)

```rust
#[derive(sqlx::FromRow)]
struct User {
    id: i64,
    email: String,
}

let user = sqlx::query_as::<_, User>(
    r#"SELECT id, email FROM "user" WHERE id = $1"#,
)
.bind(user_id)
.fetch_one(&pool)
.await?;
```

### Universal ORM Rules

- ORMs handle parameterization — never f-string or `format!` user input into SQL.
- Watch the wire: log generated SQL during development. ORMs hide N+1 queries by default.
- Eager-load explicitly when you know you will iterate child relations.
- Drop to raw SQL for analytical queries the ORM cannot express efficiently.

## Connection Pooling

- **Always pool.** Opening a connection per request exhausts file descriptors and wastes time.
- **Pool size**: start at `2 * CPU cores` for the database server; tune from there. More connections
  than the DB can usefully run causes contention, not throughput.
- **Set timeouts**: `acquire_timeout`, `idle_timeout`, `max_lifetime`.
- **PostgreSQL at scale**: front the database with `pgbouncer` (transaction pooling mode for
  short-lived statements; session pooling if you use prepared statements or `SET LOCAL`).
- **MySQL**: use a pool in the application (HikariCP, r2d2, sqlx pool). Match `max_connections` on
  the server.
- **Serverless / Lambda**: use a connection proxy (RDS Proxy, pgbouncer, PlanetScale). Direct pools
  do not survive cold starts well.

## Security

### Parameterized Queries (Mandatory)

```python
# BAD — SQL injection
cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")

# GOOD — parameter binding
cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
```

```rust
// BAD
let q = format!("SELECT * FROM users WHERE id = {user_id}");

// GOOD
sqlx::query("SELECT * FROM users WHERE id = $1").bind(user_id);
```

Placeholder syntax: PostgreSQL `$1`, MySQL `?`, SQLite `?` or `:name`.

### Access Control

- Grant the minimum privileges needed. Application roles get `SELECT`, `INSERT`, `UPDATE`, `DELETE`
  on specific tables — never `ALL PRIVILEGES`, never `SUPERUSER`.
- Separate read-only and read-write credentials; route reads to replicas with the read role.
- For multi-tenant systems, enforce isolation in the database, not just the application — PostgreSQL
  Row Level Security is the gold standard. See [references/postgresql.md](references/postgresql.md).

### Secrets

- Never commit credentials. Read from environment, secret manager, or mounted secrets file.
- Rotate credentials regularly. Application code must re-read credentials, not cache them.

## Choosing a Dialect

| Need                                                | Pick                                                                       |
| --------------------------------------------------- | -------------------------------------------------------------------------- |
| OLTP with rich types, JSONB, RLS, advanced indexing | PostgreSQL                                                                 |
| OLTP at very high write throughput, mature tooling  | MySQL (InnoDB) — consider PlanetScale for managed Vitess                   |
| Embedded, single-writer, zero-config                | SQLite                                                                     |
| Analytics over warehoused data                      | Use a warehouse (Snowflake, BigQuery, Databricks) — not a transactional DB |

## Anti-Patterns Recap

- `SELECT *` in production code
- Missing index on a foreign key column
- `OFFSET`-based pagination on large datasets
- Function calls or implicit casts on indexed columns in `WHERE`
- Random UUIDv4 as a clustered primary key
- Schema changes outside the migration system
- Business logic in stored procedures (keep it in application code)
- Multiple databases sharing a schema across services (use one owner per schema)
- Trusting the ORM to be efficient without inspecting generated SQL
- Storing money in `FLOAT` or timestamps without a timezone
