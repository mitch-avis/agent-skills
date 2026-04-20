# Common Issue Patterns

Quick bad-vs-good examples for issues that appear in nearly every code review. Cite these when
flagging the issue in a review report.

## N+1 Query

```python
# BAD: query inside loop
for user in users:
    orders = Order.objects.filter(user=user)  # one query per user

# GOOD: prefetch in bulk
users = User.objects.prefetch_related("orders").all()
for user in users:
    orders = user.orders.all()
```

## Magic Number

```python
# BAD
if status == 3:
    notify_shipped()

# GOOD
ORDER_STATUS_SHIPPED = 3
if status == ORDER_STATUS_SHIPPED:
    notify_shipped()
```

## SQL Injection

```python
# BAD: string interpolation
query = f"SELECT * FROM users WHERE email = '{email}'"
db.execute(query)

# GOOD: parameterized
db.execute("SELECT * FROM users WHERE email = ?", (email,))
```

## Swallowed Exception

```python
# BAD: silent failure
try:
    risky()
except Exception:
    pass

# GOOD: handle or surface
try:
    risky()
except SpecificError as e:
    logger.warning("risky() failed: %s", e)
    raise
```

## Missing Null/Empty Check

```python
# BAD: assumes result is non-empty
result = db.query("...")
return result[0]

# GOOD: handle empty case
result = db.query("...")
if not result:
    return None
return result[0]
```

## Unbounded Loop or Query

```python
# BAD: returns every row regardless of size
rows = db.query("SELECT * FROM events")

# GOOD: paginate or limit
rows = db.query("SELECT * FROM events ORDER BY id LIMIT ? OFFSET ?", (page_size, offset))
```

## Race Condition (Check-then-Act)

```python
# BAD: another writer may insert between check and act
if not db.exists(key):
    db.insert(key, value)

# GOOD: atomic upsert / unique constraint + handle conflict
db.execute("INSERT INTO t (key, value) VALUES (?, ?) ON CONFLICT (key) DO NOTHING",
           (key, value))
```

## Hardcoded Secret

```python
# BAD
API_KEY = "sk_live_abc123..."

# GOOD: load from environment / secret manager
import os
API_KEY = os.environ["API_KEY"]
```

## Overly Long Function

If a function spans more than ~50 lines or mixes concerns (validation + business logic + I/O),
suggest extracting cohesive helpers. Cite the specific responsibilities you can see and where the
seams are.

## Premature Abstraction

A single-implementation interface, generic helper used in one place, or "framework" built for
imagined future needs. Recommend inlining until a second concrete use case appears.
