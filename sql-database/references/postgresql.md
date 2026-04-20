# PostgreSQL Specifics

PostgreSQL-specific features, types, and gotchas.

## Type Discipline

### Always Use

- `BIGINT GENERATED ALWAYS AS IDENTITY` for auto-incrementing PKs (replaces `BIGSERIAL`)
- `TIMESTAMPTZ` for any time value (stores UTC, formats per session timezone)
- `TEXT` for variable-length strings (no performance penalty vs `VARCHAR(n)`)
- `NUMERIC(p, s)` for money and exact decimals
- `JSONB` for JSON (binary, indexable; never plain `JSON`)
- `UUID` (with `gen_random_uuid()` or `uuidv7()` in PG18+) for opaque external IDs

### Never Use

| Avoid                  | Use instead                             | Why                                           |
| ---------------------- | --------------------------------------- | --------------------------------------------- |
| `SERIAL` / `BIGSERIAL` | `... GENERATED ALWAYS AS IDENTITY`      | Identity columns are SQL standard, safer      |
| `TIMESTAMP`            | `TIMESTAMPTZ`                           | Loses timezone information                    |
| `TIMETZ`               | `TIMESTAMPTZ` or `TIME` + separate date | Quirky semantics                              |
| `MONEY`                | `NUMERIC(p, s)`                         | Locale-dependent, single currency only        |
| `CHAR(n)`              | `TEXT` + `CHECK (length(col) = n)`      | Pads with spaces                              |
| `VARCHAR(n)`           | `TEXT` + `CHECK (length(col) <= n)`     | No performance benefit; constraint is clearer |
| `JSON`                 | `JSONB`                                 | Plain `JSON` cannot be indexed efficiently    |

## JSONB

### Indexed Queries

Use containment (`@>`) for indexable lookups, not field extraction (`->>`).

```sql
CREATE INDEX idx_events_data_gin ON events USING gin (data);
-- or smaller, containment-only:
CREATE INDEX idx_events_data_gin ON events USING gin (data jsonb_path_ops);

-- INDEXED — uses GIN
SELECT * FROM events WHERE data @> '{"type": "login"}';
SELECT * FROM events WHERE data @> '{"user": {"role": "admin"}}';

-- NOT INDEXED — sequential scan
SELECT * FROM events WHERE data ->> 'type' = 'login';

-- Index a single hot path with a btree on the extracted field
CREATE INDEX idx_events_user_id ON events ((data ->> 'user_id'));
```

### Validation

Constrain JSONB to known shapes:

```sql
ALTER TABLE orders
  ADD CONSTRAINT valid_status
  CHECK (data ->> 'status' IN ('pending', 'shipped', 'delivered', 'cancelled'));
```

## Arrays

```sql
CREATE TABLE posts (
  id    BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  title TEXT NOT NULL,
  tags  TEXT[] NOT NULL DEFAULT '{}'
);

CREATE INDEX idx_posts_tags ON posts USING gin (tags);

SELECT * FROM posts WHERE tags @> ARRAY['postgresql'];   -- contains
SELECT * FROM posts WHERE tags && ARRAY['db', 'sql'];    -- overlaps
SELECT * FROM posts WHERE 'postgresql' = ANY(tags);      -- works but no GIN
```

Prefer arrays for true unordered sets (tags, role lists). For ordered, queryable collections, use a
child table.

## Generated Columns

Computed, indexable, kept in sync automatically.

```sql
CREATE TABLE products (
  id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  price_cents BIGINT NOT NULL,
  tax_cents   BIGINT NOT NULL,
  total_cents BIGINT GENERATED ALWAYS AS (price_cents + tax_cents) STORED
);

CREATE INDEX idx_products_total ON products (total_cents);
```

## Custom Types

```sql
-- Enums
CREATE TYPE order_status AS ENUM ('pending', 'shipped', 'delivered', 'cancelled');

-- Domain (constrained type)
CREATE DOMAIN positive_amount AS NUMERIC(10, 2) CHECK (VALUE > 0);

CREATE TABLE orders (
  id     BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  amount positive_amount NOT NULL,
  status order_status NOT NULL DEFAULT 'pending'
);
```

Adding enum values requires `ALTER TYPE ... ADD VALUE` — plan ahead, since values cannot be removed.

## Row Level Security (RLS)

Enforce per-tenant or per-user filtering at the database, not just the application.

```sql
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;

CREATE POLICY documents_tenant_isolation ON documents
  USING (tenant_id = current_setting('app.tenant_id')::bigint);

-- Application sets the tenant per session/transaction
SET LOCAL app.tenant_id = '42';
```

Combine with role grants — the policy applies after table-level `GRANT`s.

## MVCC and Vacuum

PostgreSQL uses Multi-Version Concurrency Control. `UPDATE` and `DELETE` mark old row versions dead;
`VACUUM` reclaims them.

- **Hot updates** that don't change indexed columns are cheap and can stay in-page.
- **Wide-row churn** (frequent updates to large rows) causes bloat — split tables vertically.
- **Long-running transactions** prevent vacuum — keep transactions short.
- **`autovacuum`** runs by default; tune `autovacuum_vacuum_scale_factor` for hot tables.

## `UNIQUE` and NULLs

By default, multiple `NULL` values are allowed in a `UNIQUE` column:

```sql
-- PG14 and earlier — multiple NULLs allowed
CREATE UNIQUE INDEX idx_users_email ON users (email);

-- PG15+ — at most one NULL
CREATE UNIQUE INDEX idx_users_email ON users (email) NULLS NOT DISTINCT;
```

## Identifier Casing

Unquoted identifiers are folded to lowercase. Mixed-case quoted identifiers are a foot-gun:

```sql
CREATE TABLE "Users" (id INT);    -- table is literally "Users"
SELECT * FROM Users;              -- ERROR — looks for "users"
SELECT * FROM "Users";            -- only this works
```

Stick to `snake_case` and never quote identifiers.

## Useful Diagnostics

```sql
-- Slow queries
SELECT query, calls, total_exec_time, mean_exec_time, rows
  FROM pg_stat_statements
 ORDER BY total_exec_time DESC
 LIMIT 10;

-- Table size including indexes and toast
SELECT pg_size_pretty(pg_total_relation_size('orders'));

-- Lock contention
SELECT blocked.pid AS blocked_pid, blocking.pid AS blocking_pid,
       blocked.query AS blocked_query, blocking.query AS blocking_query
  FROM pg_stat_activity blocked
  JOIN pg_stat_activity blocking ON blocking.pid = ANY(pg_blocking_pids(blocked.pid));
```

## Connection Pooling with pgbouncer

| Mode        | Use when                                           | Caveats                          |
| ----------- | -------------------------------------------------- | -------------------------------- |
| Session     | App relies on `SET`, prepared statements, `LISTEN` | Lower throughput                 |
| Transaction | Default — short-lived statements                   | No session-level state survives  |
| Statement   | Auto-commit only                                   | Rare — most apps use transaction |

For prepared statements behind transaction pooling, use server-side protocol-level prepared
statements (PG14+ `pgbouncer 1.21+`).
