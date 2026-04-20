# Log Search with Elastic ES|QL

ES|QL is the modern Elasticsearch query language. Use it from Kibana Discover or
`POST /_query` for incident investigation. The workflow mirrors Discover: scope, then **iteratively
exclude noise (NOT)** until a small interesting subset remains.

## Table of Contents

- [Log Search with Elastic ES|QL](#log-search-with-elastic-esql)
  - [Table of Contents](#table-of-contents)
  - [When to use this](#when-to-use-this)
  - [Parameter conventions](#parameter-conventions)
    - [Context minimization](#context-minimization)
  - [The funnel workflow](#the-funnel-workflow)
  - [ES|QL patterns](#esql-patterns)
    - [Five-way FORK with histogram, samples, and categorization](#five-way-fork-with-histogram-samples-and-categorization)
    - [Adding a KQL filter](#adding-a-kql-filter)
    - [Histogram by dimension](#histogram-by-dimension)
  - [Examples](#examples)
    - [Last hour of logs for one service](#last-hour-of-logs-for-one-service)
    - [Iterative funnel (rounds)](#iterative-funnel-rounds)
  - [Pitfalls](#pitfalls)
  - [ECS field reference](#ecs-field-reference)

## When to use this

- Investigating a log spike, error surge, or anomaly in Elastic Observability / Kibana
- Drilling into one service or container during an incident
- Getting trend, total, samples, and pattern categorization in a single query

**Do not use for** metrics or traces — use the dedicated tools for those signals.

## Parameter conventions

When a tool wraps these queries, prefer these parameter names:

| Parameter   | Type   | Description                                                     |
| ----------- | ------ | --------------------------------------------------------------- |
| `start`     | string | Start of range (date math, e.g. `now-1h`)                       |
| `end`       | string | End of range (e.g. `now`)                                       |
| `kqlFilter` | string | KQL string used inside `KQL("...")`. Not `query` or `filter`    |
| `limit`     | number | Max log samples (10–100; cap at 500)                            |
| `groupBy`   | string | Optional histogram dimension (e.g. `log.level`, `service.name`) |

### Context minimization

The query returns **a lot** of structure. Keep the main agent context tiny:

- In the sample branch, **`KEEP` only summary fields** — never return whole documents
- Default sample size 10–20 logs, cap at 500
- Each intermediate query is for choosing the next call; only the final narrowed result is worth
  keeping in context

Recommended `KEEP` list:

```text
message, error.message, service.name, container.name, host.name, container.id,
agent.name, kubernetes.container.name, kubernetes.node.name,
kubernetes.namespace, kubernetes.pod.name
```

Message field fallback (first non-empty): `body.text` (OTel) → `message` → `error.message` →
`event.original` → `exception.message`.

## The funnel workflow

**Iterate. Do not stop after one query.** Add `NOT` clauses for dominant noise patterns; keep all
previous NOTs each round (do not zoom out). Continue until **fewer than ~20 distinct log patterns
remain**.

1. **Round 1 — broad.** Scope filter (e.g. `service.name: orders`) + time range. Get total count,
   histogram, samples, and message categorization.
2. **Inspect.** Use the histogram to spot spikes (narrow the time range around them); use the sample
   messages and pattern categorization to count distinct patterns and pick the loudest noise to
   exclude.
3. **Round 2 — exclude.** Add `NOT message: *Returning*`, `NOT message: *health check*`, etc. Re-run
   with the **full** filter.
4. **Repeat.** Keep adding NOTs until < 20 patterns remain — that residue is the signal.
5. **Pivot.** Once a specific entity (container, pod, host) emerges, run one more query focused on
   it to see its dying words / surrounding context.

Stopping early reports noise, not failures.

## ES|QL patterns

Always use `POST /_query`. Use `FORK` to fan out trend, total, samples, and categorization in **one
round-trip**. Output:

| Branch | Meaning                                               |
| ------ | ----------------------------------------------------- |
| fork1  | Trend (count per time bucket)                         |
| fork2  | Total count                                           |
| fork3  | Sample logs (10–20 docs)                              |
| fork4  | Top message patterns by count (CATEGORIZE, sort DESC) |
| fork5  | Rare message patterns (CATEGORIZE, sort ASC)          |

### Five-way FORK with histogram, samples, and categorization

```json
POST /_query
{
  "query": "FROM logs-* METADATA _id, _index | WHERE @timestamp >= TO_DATETIME(\"2026-04-20T10:00:00.000Z\") AND @timestamp <= TO_DATETIME(\"2026-04-20T11:00:00.000Z\") | FORK (STATS count = COUNT(*) BY bucket = BUCKET(@timestamp, 1m) | SORT bucket) (STATS total = COUNT(*)) (SORT @timestamp DESC | LIMIT 10 | KEEP _id, _index, message, error.message, service.name, container.name, host.name, kubernetes.container.name, kubernetes.node.name, kubernetes.namespace, kubernetes.pod.name) (LIMIT 10000 | STATS COUNT(*) BY CATEGORIZE(message) | SORT `COUNT(*)` DESC | LIMIT 20) (LIMIT 10000 | STATS COUNT(*) BY CATEGORIZE(message) | SORT `COUNT(*)` ASC | LIMIT 20)"
}
```

### Adding a KQL filter

Wrap the KQL string in `\"...\"` inside the JSON. If the KQL itself contains a quoted phrase, escape
those as `\\\"`:

```json
"query": "... | WHERE KQL(\"service.name: checkout AND log.level: error\") | ..."
```

```json
"query": "... | WHERE KQL(\"NOT message: \\\"GET /health\\\" AND NOT kubernetes.namespace: \\\"kube-system\\\"\") | ..."
```

### Histogram by dimension

```text
STATS count = COUNT(*) BY bucket = BUCKET(@timestamp, 1m), log.level
```

Restrict to top-N values to avoid response explosion.

## Examples

### Last hour of logs for one service

```json
POST /_query
{
  "query": "FROM logs-* METADATA _id, _index | WHERE @timestamp >= NOW() - 1 hour AND @timestamp <= NOW() | WHERE KQL(\"service.name: api-gateway\") | SORT @timestamp DESC | LIMIT 20"
}
```

### Iterative funnel (rounds)

**Round 1:** `KQL("service.name: orders")` → 55k logs; samples include `Returning N`, `WARNING ...`,
`received order request`.

**Round 2:** `KQL("service.name: orders AND NOT message: *Returning* AND NOT message: *WARNING*")` →
re-run.

**Round 3:** `KQL("service.name: orders AND NOT message: *Returning* AND NOT message: *WARNING* AND
NOT message: *received order request* AND NOT message: *Cache miss*")` → re-run.

**Round 4+:** Keep going. Stop when fewer than ~20 patterns remain — the residue is the incident
signal.

## Pitfalls

- **`log.level` filtering is unreliable.** Many pipelines lose the level or set everything to
  `info`. Funnel by message content or `error.message` instead; treat `log.level` as a hint.
- **Word-search for "error" / "fail" is noisy.** Matches "no error", "error code 0", and unrelated
  stack traces. Scope by entity, then funnel.
- **Wildcards in quoted phrases do not work.** Use `message: *foo*` (unquoted) or `message: "exact
  phrase"`, not both.
- **JSON escaping** — wrap KQL with `\"`, escape inner quotes with `\\\"`. Misescaped queries fail
  silently or match the wrong thing.
- **Bucket size** — aim for 20–50 buckets across the window (1h → 1m or 2m).

## ECS field reference

Use ECS field names; OTel fields are aliased to ECS in Observability index templates.

| Concern       | ECS field                                                                                                                 |
| ------------- | ------------------------------------------------------------------------------------------------------------------------- |
| Service       | `service.name`, `service.environment`, `service.version`                                                                  |
| Host          | `host.name`, `host.ip`                                                                                                    |
| Container     | `container.id`, `container.name`, `container.image.name`                                                                  |
| Kubernetes    | `kubernetes.namespace`, `kubernetes.pod.name`, `kubernetes.node.name`, `kubernetes.container.name`, `kubernetes.labels.*` |
| Trace context | `trace.id`, `span.id`, `transaction.id`                                                                                   |
| HTTP          | `http.request.method`, `http.response.status_code`, `url.path`                                                            |
| Error         | `error.message`, `error.type`, `error.stack_trace`                                                                        |
| Log           | `log.level`, `log.logger`, `@timestamp`, `message`                                                                        |
