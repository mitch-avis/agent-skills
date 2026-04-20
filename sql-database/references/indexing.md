# Indexing Strategy

Detailed index design patterns and dialect-specific syntax.

## Index Types

| Type     | Best For                                | PostgreSQL         | MySQL         | SQLite        |
| -------- | --------------------------------------- | ------------------ | ------------- | ------------- |
| B-Tree   | Equality, range, sorting (default)      | `USING btree`      | default       | default       |
| Hash     | Equality only                           | `USING hash`       | MEMORY engine | —             |
| GIN      | JSONB, arrays, full-text                | `USING gin`        | —             | —             |
| GiST     | Ranges, geometry, exclusion constraints | `USING gist`       | —             | —             |
| BRIN     | Very large, naturally ordered tables    | `USING brin`       | —             | —             |
| FULLTEXT | Text search                             | (use GIN+tsvector) | `FULLTEXT`    | FTS5 (vtable) |

## Composite Index Design

### Leftmost Prefix Rule

A composite index `(a, b, c)` can serve queries that filter on:

- `a`
- `a, b`
- `a, b, c`
- `a` with `ORDER BY b` or `ORDER BY b, c`

It **cannot** serve queries filtering only on `b`, `c`, or `b, c`.

### Column Order

Order columns by the role they play in the query, not by selectivity alone:

1. **Equality predicates first** (`WHERE a = ?`)
2. **Range predicate next** (`WHERE b > ?`) — stops further index filtering
3. **Sort columns last** (`ORDER BY c`) — only useful if no range above

### Examples

```sql
-- Query: WHERE tenant_id = ? AND status IN (...) ORDER BY created_at DESC
CREATE INDEX idx_orders_tenant_status_created
  ON orders (tenant_id, status, created_at DESC);

-- Query: WHERE customer_id = ? AND order_date BETWEEN ? AND ?
-- Range stops index — putting created_at second is fine here.
CREATE INDEX idx_orders_customer_date
  ON orders (customer_id, order_date);
```

## Covering Indexes

Include non-key columns to enable **index-only scans** — the query is answered without visiting the
table heap.

```sql
-- PostgreSQL 11+
CREATE INDEX idx_users_email_covering
  ON users (email)
  INCLUDE (name, created_at);

-- MySQL 8.0+ — add columns into the index itself
CREATE INDEX idx_users_email_name
  ON users (email, name, created_at);
```

The query must select **only** indexed/included columns to qualify.

## Partial Indexes (PostgreSQL, SQLite)

Index a subset of rows. Smaller, faster to maintain, only matches relevant queries.

```sql
-- Only index active subscriptions
CREATE INDEX idx_subscriptions_active_user
  ON subscriptions (user_id)
  WHERE status = 'active';

-- Soft-delete pattern: only un-deleted rows
CREATE INDEX idx_posts_published_created
  ON posts (created_at DESC)
  WHERE deleted_at IS NULL;
```

The query planner must see the same `WHERE` predicate to use the index.

## Expression Indexes

Index a computed value so functional predicates remain sargable.

```sql
-- Case-insensitive email lookup (PostgreSQL)
CREATE INDEX idx_users_lower_email ON users (LOWER(email));
SELECT * FROM users WHERE LOWER(email) = LOWER($1);

-- MySQL 8.0+ functional index
CREATE INDEX idx_users_lower_email ON users ((LOWER(email)));
```

PostgreSQL alternative: use the `CITEXT` extension type and index the column directly.

## JSONB and Array Indexes (PostgreSQL)

```sql
-- General-purpose JSONB GIN: supports @>, ?, ?|, ?&
CREATE INDEX idx_events_data ON events USING gin (data);

-- Smaller, faster, containment-only
CREATE INDEX idx_events_data ON events USING gin (data jsonb_path_ops);

-- Index a specific JSONB path
CREATE INDEX idx_events_user_id ON events USING btree ((data ->> 'user_id'));

-- Array containment / overlap
CREATE INDEX idx_posts_tags ON posts USING gin (tags);
SELECT * FROM posts WHERE tags @> ARRAY['postgresql'];
SELECT * FROM posts WHERE tags && ARRAY['db', 'sql'];
```

Use `@>` (containment) over `->>` for indexed JSONB queries.

## Full-Text Search

### PostgreSQL

```sql
ALTER TABLE documents ADD COLUMN search_vector tsvector
  GENERATED ALWAYS AS (
    to_tsvector('english', coalesce(title, '') || ' ' || coalesce(body, ''))
  ) STORED;

CREATE INDEX idx_documents_search ON documents USING gin (search_vector);

SELECT id, title,
       ts_rank(search_vector, websearch_to_tsquery('english', $1)) AS rank
  FROM documents
 WHERE search_vector @@ websearch_to_tsquery('english', $1)
 ORDER BY rank DESC
 LIMIT 20;
```

### MySQL

```sql
ALTER TABLE products ADD FULLTEXT INDEX ft_name_desc (name, description);

SELECT * FROM products
 WHERE MATCH(name, description) AGAINST('wireless bluetooth' IN NATURAL LANGUAGE MODE);
```

### SQLite

```sql
CREATE VIRTUAL TABLE documents_fts
  USING fts5(title, body, content='documents', content_rowid='id');

SELECT documents.*
  FROM documents_fts
  JOIN documents ON documents.id = documents_fts.rowid
 WHERE documents_fts MATCH 'sqlite NEAR fts';
```

## Maintenance

### PostgreSQL

```sql
-- Unused indexes
SELECT schemaname, relname, indexrelname, idx_scan, pg_size_pretty(pg_relation_size(indexrelid))
  FROM pg_stat_user_indexes
 WHERE idx_scan = 0
 ORDER BY pg_relation_size(indexrelid) DESC;

-- Bloat — rebuild without locking writes
REINDEX INDEX CONCURRENTLY idx_orders_user_status_created;

-- Refresh statistics after large data changes
ANALYZE orders;
```

### MySQL

```sql
-- Unused indexes (since server start)
SELECT object_schema, object_name, index_name
  FROM performance_schema.table_io_waits_summary_by_index_usage
 WHERE index_name IS NOT NULL
   AND count_star = 0
   AND object_schema NOT IN ('mysql', 'performance_schema');

-- Rebuild
ALTER TABLE orders DROP INDEX idx_x, ADD INDEX idx_x (col1, col2),
  ALGORITHM=INPLACE, LOCK=NONE;
```

## Anti-Patterns

- **Indexing every column individually** — composite indexes serve more queries with less overhead.
- **Indexing low-cardinality columns alone** (e.g., `is_active`) — only useful as part of a
  composite or partial index.
- **Adding indexes without checking `EXPLAIN`** — measure before and after.
- **Forgetting to drop the old index** when replacing it with a wider composite.
- **Indexing very wide columns directly** — use a hash, prefix, or expression index.
