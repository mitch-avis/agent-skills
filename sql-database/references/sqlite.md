# SQLite Specifics

Embedded-database patterns: pragmas, WAL mode, FTS5, type affinity, and concurrency limits.

## Required Pragmas

SQLite ships with safe defaults disabled for legacy reasons. Set these on every connection:

```sql
PRAGMA foreign_keys = ON;        -- enforce FK constraints (default OFF)
PRAGMA journal_mode = WAL;       -- write-ahead log; concurrent readers allowed
PRAGMA synchronous = NORMAL;     -- safe with WAL; faster than FULL
PRAGMA busy_timeout = 5000;      -- wait 5s on lock contention before erroring
PRAGMA cache_size = -64000;      -- 64 MB page cache (negative = KiB)
PRAGMA temp_store = MEMORY;      -- temp tables in RAM
```

`journal_mode = WAL` is set per database file and persists. The others are per-connection and must
be set after every `open()`.

## Type Affinity

SQLite uses **type affinity**, not strict typing. Any column can hold any type unless you add
explicit `CHECK` constraints.

| Declared type             | Affinity | Storage class          |
| ------------------------- | -------- | ---------------------- |
| `INT`, `INTEGER`          | INTEGER  | INTEGER                |
| `TEXT`, `VARCHAR`, `CHAR` | TEXT     | TEXT                   |
| `BLOB`, no type           | BLOB     | BLOB                   |
| `REAL`, `FLOAT`           | REAL     | REAL                   |
| `NUMERIC`, `DECIMAL`      | NUMERIC  | INTEGER, REAL, or TEXT |

### Recommended Types

```sql
CREATE TABLE users (
  id         INTEGER PRIMARY KEY,                    -- aliases ROWID
  email      TEXT    NOT NULL UNIQUE,
  created_at TEXT    NOT NULL DEFAULT (datetime('now')),  -- ISO-8601 UTC
  metadata   TEXT    CHECK (json_valid(metadata)),         -- JSON in TEXT
  balance    NUMERIC NOT NULL DEFAULT 0
);
```

- **`INTEGER PRIMARY KEY`** is special — it aliases `ROWID` and is the most efficient PK form. Do
  not use `BIGINT` (no benefit) or `AUTOINCREMENT` unless you specifically need monotonic IDs that
  never reuse deleted values.
- **Timestamps**: store as ISO-8601 `TEXT` (`'2024-04-01T12:30:45.000Z'`) or as Unix epoch
  `INTEGER`. Use the SQLite date/time functions consistently.
- **Booleans**: `INTEGER` 0/1 with `CHECK (col IN (0, 1))`.
- **JSON**: `TEXT` with `CHECK (json_valid(col))`. Use the JSON1 extension functions for queries.

## Concurrency

SQLite supports **concurrent readers** but **only one writer at a time**.

- WAL mode allows readers to work uninterrupted while a write is in progress.
- A long-running write transaction blocks all other writes. Keep writes short.
- `PRAGMA busy_timeout` waits for the lock to clear before erroring with `SQLITE_BUSY`.
- For multi-process write workloads, switch to a server-based database (PostgreSQL/MySQL).

## Transactions

```sql
BEGIN IMMEDIATE;   -- acquire the write lock now (avoids upgrade deadlocks)
-- ... statements ...
COMMIT;
```

- Use `BEGIN IMMEDIATE` instead of `BEGIN` (the default `DEFERRED`) when you know the transaction
  will write — it acquires the write lock up front instead of upgrading later.
- Wrap related operations in a transaction. Bare `INSERT`s are individual transactions and are
  dramatically slower than batched ones.

## Migrations

SQLite has limited `ALTER TABLE` — adding columns is fine, but renaming, dropping, or changing
column types requires the **12-step recreation procedure**:

1. Create the new table with the desired schema (different name).
2. Copy data with `INSERT INTO new SELECT ... FROM old`.
3. Drop the old table.
4. Rename the new table.
5. Recreate indexes, triggers, views, FK references in other tables.

Track applied migrations in a `schema_migrations(version, name, applied_at)` table, same as other
dialects.

## Full-Text Search (FTS5)

```sql
CREATE VIRTUAL TABLE notes_fts USING fts5(
  title, body,
  content='notes',          -- contentless mode tied to base table
  content_rowid='id',
  tokenize='porter unicode61'
);

-- Keep the FTS table in sync with triggers
CREATE TRIGGER notes_ai AFTER INSERT ON notes BEGIN
  INSERT INTO notes_fts(rowid, title, body) VALUES (new.id, new.title, new.body);
END;
CREATE TRIGGER notes_ad AFTER DELETE ON notes BEGIN
  INSERT INTO notes_fts(notes_fts, rowid, title, body)
    VALUES ('delete', old.id, old.title, old.body);
END;
CREATE TRIGGER notes_au AFTER UPDATE ON notes BEGIN
  INSERT INTO notes_fts(notes_fts, rowid, title, body)
    VALUES ('delete', old.id, old.title, old.body);
  INSERT INTO notes_fts(rowid, title, body) VALUES (new.id, new.title, new.body);
END;

-- Query
SELECT n.* FROM notes n
  JOIN notes_fts f ON f.rowid = n.id
 WHERE notes_fts MATCH 'sqlite NEAR fts';
```

## Parameterization (rusqlite)

```rust
use rusqlite::{params, Connection};

let conn = Connection::open("app.db")?;
conn.pragma_update(None, "foreign_keys", "ON")?;
conn.pragma_update(None, "journal_mode", "WAL")?;

// Positional parameters
conn.execute(
    "INSERT INTO users (email, name) VALUES (?1, ?2)",
    params![email, name],
)?;

// Named parameters
let mut stmt = conn.prepare(
    "SELECT id, email FROM users WHERE email = :email",
)?;
let row = stmt.query_row(&[(":email", &email)], |r| {
    Ok(User { id: r.get(0)?, email: r.get(1)? })
})?;
```

Never `format!` or concatenate user input into SQL.

## Testing

In-memory databases are perfect for fast, isolated tests.

```rust
let conn = Connection::open_in_memory()?;
conn.execute_batch(include_str!("../migrations/0001_init.sql"))?;
```

```python
# Python
import sqlite3
conn = sqlite3.connect(":memory:")
```

## Backup

```sql
-- Online backup, safe while the database is in use
.backup main 'backup.db'
```

Or use the `sqlite3_backup_*` C API exposed by your driver. Plain file copy is unsafe while the
database is open.

## When SQLite Is the Wrong Choice

- High-concurrency multi-writer workloads
- Multi-host access (no network protocol)
- Datasets larger than a few hundred GB
- Anything requiring online schema changes without table rewrites
- Workloads needing fine-grained access control (no users/roles in SQLite)
