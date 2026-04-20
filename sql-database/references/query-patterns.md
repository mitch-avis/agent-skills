# Query Patterns

Pagination, joins, subquery rewrites, window functions, and EXPLAIN walkthroughs.

## Pagination

### Cursor / Keyset (Recommended)

`OFFSET` re-scans skipped rows on every page request. Use a cursor over a unique, sortable key tuple
— typically `(sort_column, primary_key)` to break ties.

```sql
-- First page
SELECT id, title, created_at
  FROM posts
 ORDER BY created_at DESC, id DESC
 LIMIT 20;

-- Next page: pass the last row's (created_at, id) as the cursor
SELECT id, title, created_at
  FROM posts
 WHERE (created_at, id) < ($1, $2)
 ORDER BY created_at DESC, id DESC
 LIMIT 20;
```

The supporting index: `(created_at DESC, id DESC)`.

### When `OFFSET` Is Acceptable

- Small offsets (< 1000 rows) on small tables
- Admin tooling where latency does not matter
- Datasets where stable ordering across requests is impossible

## Eliminating Correlated Subqueries

```sql
-- BAD: subquery executed once per outer row
SELECT o.id,
       (SELECT SUM(quantity) FROM order_items oi WHERE oi.order_id = o.id) AS items
  FROM orders o;

-- GOOD: aggregate once, join
SELECT o.id, COALESCE(agg.items, 0) AS items
  FROM orders o
  LEFT JOIN (
    SELECT order_id, SUM(quantity) AS items
      FROM order_items
     GROUP BY order_id
  ) agg ON agg.order_id = o.id;
```

## Window Functions

Eliminate self-joins for ranking, running totals, and lag/lead.

```sql
-- Latest order per customer
SELECT customer_id, order_id, total_amount
  FROM (
    SELECT customer_id, id AS order_id, total_amount,
           ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY created_at DESC) AS rn
      FROM orders
     WHERE status = 'completed'
  ) ranked
 WHERE rn = 1;

-- Running total per department
SELECT department_id,
       employee_id,
       salary,
       SUM(salary) OVER (PARTITION BY department_id ORDER BY hired_at) AS running_total,
       RANK()      OVER (PARTITION BY department_id ORDER BY salary DESC)  AS salary_rank
  FROM employees;

-- Compare to previous row
SELECT product_id, sale_date, amount,
       LAG(amount) OVER (PARTITION BY product_id ORDER BY sale_date) AS prev_amount
  FROM sales;
```

## CTEs

Use Common Table Expressions to isolate expensive logic and improve readability.

```sql
WITH active_customers AS (
    SELECT id FROM customers WHERE status = 'active'
),
recent_orders AS (
    SELECT customer_id, COUNT(*) AS order_count, SUM(total) AS revenue
      FROM orders
     WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
       AND customer_id IN (SELECT id FROM active_customers)
     GROUP BY customer_id
)
SELECT c.id, c.name, ro.order_count, ro.revenue
  FROM customers c
  JOIN recent_orders ro ON ro.customer_id = c.id
 ORDER BY ro.revenue DESC
 LIMIT 100;
```

PostgreSQL 12+ inlines simple CTEs; older versions and MySQL materialize them.

## Joins

- **`INNER JOIN`** when both sides must exist.
- **`LEFT JOIN`** when the left side drives the result set.
- **`EXISTS`** over `IN (SELECT ...)` for correlated existence checks — short-circuits.
- Filter early — push `WHERE` into the joined subquery when possible.

```sql
-- BAD: Cartesian product disguised as a join
SELECT u.*, o.* FROM users u, orders o WHERE u.id = o.user_id;

-- GOOD: explicit join
SELECT u.id, u.name, o.id AS order_id, o.total
  FROM users u
  INNER JOIN orders o ON o.user_id = u.id
 WHERE u.status = 'active'
   AND o.created_at >= '2024-01-01';
```

## Batch Operations

```sql
-- Bulk insert
INSERT INTO products (name, price)
VALUES ('A', 1), ('B', 2), ('C', 3);

-- PostgreSQL: very large loads
COPY products (name, price) FROM STDIN WITH (FORMAT csv);

-- MySQL: very large loads
LOAD DATA INFILE '/tmp/products.csv'
  INTO TABLE products
  FIELDS TERMINATED BY ',' ENCLOSED BY '"'
  LINES TERMINATED BY '\n';

-- Upsert (PostgreSQL)
INSERT INTO products (sku, name, price)
VALUES ($1, $2, $3)
ON CONFLICT (sku) DO UPDATE
   SET name = EXCLUDED.name, price = EXCLUDED.price;

-- Upsert (MySQL)
INSERT INTO products (sku, name, price)
VALUES (?, ?, ?)
AS new
ON DUPLICATE KEY UPDATE name = new.name, price = new.price;
```

## EXPLAIN Walkthrough

### PostgreSQL

```sql
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT u.id, u.email, COUNT(o.id) AS orders
  FROM users u
  LEFT JOIN orders o ON o.user_id = u.id
 WHERE u.created_at >= CURRENT_DATE - INTERVAL '30 days'
 GROUP BY u.id, u.email;
```

Read top-down. Look for:

| Symptom                                   | Likely cause / fix                                                       |
| ----------------------------------------- | ------------------------------------------------------------------------ |
| `Seq Scan` on a large table               | Missing index, or the planner thinks scan is cheaper — check selectivity |
| `actual rows ≫ estimated rows`            | Stale statistics — run `ANALYZE table`                                   |
| `Buffers: shared read` ≫ `shared hit`     | Cold cache or missing index — lots of disk reads                         |
| `Sort` followed by `Seq Scan`             | `ORDER BY` cannot use an index                                           |
| `Hash Join` with huge inner relation      | Increase `work_mem` or filter inner side first                           |
| `Nested Loop` with millions of outer rows | Poor join order — usually a missing index                                |

### MySQL

```sql
EXPLAIN ANALYZE SELECT ... ;          -- 8.0.18+
EXPLAIN FORMAT=JSON SELECT ... ;
```

Watch the `type` column:

| `type`            | Meaning                                 |
| ----------------- | --------------------------------------- |
| `system`, `const` | Single-row lookup — best                |
| `eq_ref`          | One row per join — very good            |
| `ref`             | Indexed lookup, multiple matches — good |
| `range`           | Indexed range — acceptable              |
| `index`           | Full index scan — usually bad           |
| `ALL`             | Full table scan — bad on large tables   |

`Extra: Using filesort` or `Using temporary` usually means a missing index for `ORDER BY` or `GROUP
BY`.

### Refresh Statistics

```sql
-- PostgreSQL
ANALYZE orders;
VACUUM ANALYZE orders;

-- MySQL
ANALYZE TABLE orders;
```

## Avoiding N+1 from ORMs

```python
# BAD: 1 + N queries
users = session.scalars(select(User)).all()
for u in users:
    print(u.orders)        # one SELECT per user

# GOOD: 1 + 1 queries
users = session.scalars(
    select(User).options(selectinload(User.orders))
).all()
```

```rust
// Diesel: load with belonging_to + grouped
let users: Vec<User> = users::table.load(&mut conn)?;
let orders: Vec<Vec<Order>> =
    Order::belonging_to(&users).load(&mut conn)?.grouped_by(&users);
```

Always log SQL during development to catch hidden N+1 patterns.
