# MySQL Specifics

InnoDB tuning, online DDL, isolation levels, partitioning, and operational gotchas.

## Storage Engine

Use **InnoDB** for everything transactional. MyISAM has no foreign keys, no row-level locking, and
crashes badly. MEMORY tables are for ephemeral compute caches only.

```sql
CREATE TABLE orders (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  ...
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
```

## Charset and Collation

- Always `utf8mb4` (true 4-byte UTF-8 — supports emoji and supplementary planes).
- `utf8` is **not** UTF-8 in MySQL — it's a 3-byte subset. Never use it.
- `utf8mb4_0900_ai_ci` is the modern accent-insensitive, case-insensitive default.
- Use `utf8mb4_bin` only when you need byte-for-byte comparisons.

## Primary Keys and InnoDB Clustering

InnoDB stores rows in B-tree order **by primary key**. The PK is part of every secondary index.

- **Narrow, monotonic PKs** (`BIGINT UNSIGNED AUTO_INCREMENT`) keep inserts sequential and secondary
  indexes small.
- **Random UUIDs as PKs** cause page splits, fragmentation, and bloated secondary indexes.
- If you need a UUID, store it in a `BINARY(16)` secondary `UNIQUE` column with `UUID_TO_BIN`.

```sql
CREATE TABLE users (
  id   BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  uuid BINARY(16) NOT NULL UNIQUE,
  ...
);

INSERT INTO users (uuid, ...) VALUES (UUID_TO_BIN(UUID()), ...);
SELECT * FROM users WHERE uuid = UUID_TO_BIN('550e8400-e29b-41d4-a716-446655440000');
```

## Data Type Choices

| Use                  | Type                               | Notes                                            |
| -------------------- | ---------------------------------- | ------------------------------------------------ |
| Integer ID           | `BIGINT UNSIGNED`                  | `INT` runs out at 2.1B                           |
| Money                | `DECIMAL(p, s)`                    | Never `FLOAT`                                    |
| Time                 | `DATETIME(6)`                      | `TIMESTAMP` has 2038 cliff and TZ surprises      |
| Boolean              | `TINYINT(1)`                       | No native `BOOLEAN`                              |
| Short text           | `VARCHAR(n)` + `utf8mb4`           |                                                  |
| Long text            | `TEXT` / `MEDIUMTEXT` / `LONGTEXT` | Stored off-page                                  |
| Bytes                | `VARBINARY(n)` / `BLOB`            |                                                  |
| Semi-structured data | `JSON` + generated columns         | `JSON` is validated; index via generated columns |

### Avoid

- `ENUM` — values are baked into the schema, slow to evolve. Use a lookup table.
- `BIT(n)` — pre-8.0 oddities; use `TINYINT` or `BOOLEAN`.
- `FLOAT` / `DOUBLE` for money or anything requiring exact arithmetic.

## JSON with Generated Columns

```sql
CREATE TABLE events (
  id          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  data        JSON NOT NULL,
  user_id     BIGINT GENERATED ALWAYS AS (CAST(data->>'$.user_id' AS UNSIGNED)) STORED,
  event_type  VARCHAR(40) GENERATED ALWAYS AS (data->>'$.type') STORED
);

CREATE INDEX idx_events_user_type ON events (user_id, event_type);
```

Index generated columns to make JSON predicates sargable.

## Indexing

- Composite index order: equality → range → sort (leftmost-prefix rule, identical to PostgreSQL).
- Every FK needs an explicit index. MySQL warns at constraint creation but does not enforce it.
- **Prefix indexes** for long string columns: `INDEX (email(20))`.
- **Covering indexes**: include selected columns in the index itself (no `INCLUDE` clause).
- **Functional indexes** (8.0+): `INDEX ((LOWER(email)))`.
- **`FULLTEXT`** indexes for text search; query with `MATCH ... AGAINST`.

## Online DDL

8.0+ supports many `ALTER TABLE` operations without blocking writes.

```sql
ALTER TABLE orders
  ADD INDEX idx_status_created (status, created_at),
  ALGORITHM=INPLACE, LOCK=NONE;
```

| Algorithm   | Effect                                                           |
| ----------- | ---------------------------------------------------------------- |
| `INSTANT`   | Metadata-only (8.0.12+) — adding nullable columns at the end     |
| `INPLACE`   | Rebuilds in place; allows concurrent DML with `LOCK=NONE`        |
| `COPY`      | Full table copy with table lock — last resort                    |

For multi-TB tables, use **gh-ost** or **pt-online-schema-change** instead of native ALTER.

## Transactions and Isolation

Default isolation: `REPEATABLE READ`. Uses gap locks to prevent phantom reads — can deadlock under
high contention.

| Level              | Notes                                                                    |
| ------------------ | ------------------------------------------------------------------------ |
| `READ UNCOMMITTED` | Dirty reads. Almost never appropriate.                                   |
| `READ COMMITTED`   | Recommended for high-concurrency OLTP. No gap locks. Closer to Postgres. |
| `REPEATABLE READ`  | Default. Watch for deadlocks from gap locks.                             |
| `SERIALIZABLE`     | Implicit `LOCK IN SHARE MODE` on every read. Very low throughput.        |

Set per session:

```sql
SET SESSION TRANSACTION ISOLATION LEVEL READ COMMITTED;
```

## Deadlocks

Use `SHOW ENGINE INNODB STATUS` (`LATEST DETECTED DEADLOCK` section) to inspect. Mitigations:

- Acquire locks in a consistent order across transactions.
- Keep transactions short.
- Switch to `READ COMMITTED` to drop gap locks.
- Retry on deadlock errors (`ER_LOCK_DEADLOCK`, code 1213) at the application layer.

## Partitioning

Partition large tables (>100M rows) or time-series data by date range. **Plan early** — adding
partitioning later requires a full rebuild.

```sql
CREATE TABLE events (
  id         BIGINT UNSIGNED AUTO_INCREMENT,
  created_at DATETIME(6) NOT NULL,
  ...,
  PRIMARY KEY (id, created_at)
) ENGINE=InnoDB
PARTITION BY RANGE (TO_DAYS(created_at)) (
  PARTITION p2024_q1 VALUES LESS THAN (TO_DAYS('2024-04-01')),
  PARTITION p2024_q2 VALUES LESS THAN (TO_DAYS('2024-07-01')),
  PARTITION p_future VALUES LESS THAN MAXVALUE
);
```

Rules:

- The partition column must be part of every `PRIMARY KEY` and `UNIQUE` constraint.
- Always include a `MAXVALUE` catch-all to avoid insert errors.
- Drop old partitions to delete time-series data instantly: `ALTER TABLE ... DROP PARTITION`.

## Connection Management

- Set `max_connections` to what the database can actually serve, not what apps want.
- Always pool in the application (HikariCP, r2d2, sqlx pool).
- Set `wait_timeout` and `interactive_timeout` to drop idle connections.
- For high-fanout services, front MySQL with **ProxySQL** or **Vitess** (PlanetScale).

## Replication and Reads

- Use a read replica for reporting and analytical queries.
- Replication is asynchronous by default — read-after-write may be stale. Route reads that require
  freshness back to the primary.
- Monitor `Seconds_Behind_Master` (or `replication_lag` in MySQL 8.0+).

## Useful Diagnostics

```sql
-- Slow queries (requires slow_query_log = ON)
SELECT * FROM mysql.slow_log ORDER BY query_time DESC LIMIT 20;

-- Long-running transactions
SELECT * FROM information_schema.innodb_trx
 ORDER BY trx_started ASC;

-- Lock waits
SELECT * FROM performance_schema.data_lock_waits;

-- Index usage
SELECT object_schema, object_name, index_name, count_star
  FROM performance_schema.table_io_waits_summary_by_index_usage
 WHERE object_schema = DATABASE()
 ORDER BY count_star DESC;
```
