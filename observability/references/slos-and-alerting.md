# SLOs and Alerting

Service Level Objectives turn metrics into a contract with users. Burn-rate alerting on SLOs gives
high-precision pages without the noise of threshold alerts.

## Vocabulary

| Term         | Meaning                                                          |
| ------------ | ---------------------------------------------------------------- |
| SLI          | Indicator — a measurement (e.g. ratio of good requests to total) |
| SLO          | Objective — target for the SLI (e.g. 99.9% over 30 days)         |
| Error budget | `1 − SLO` — how much unreliability is allowed                    |
| Burn rate    | Rate at which the budget is being consumed (1× = on track)       |
| Page         | Wakes a human; reserved for fast-burn or critical SLO breach     |
| Ticket       | Records work; for slow-burn or low-severity issues               |

## Choosing SLIs

Pick SLIs from the user's perspective. For a request-driven service, the usual two:

| SLI          | Definition                                  |
| ------------ | ------------------------------------------- |
| Availability | `successful_requests / total_requests`      |
| Latency      | `requests_under_threshold / total_requests` |

For a queue / batch worker:

| SLI         | Definition                                          |
| ----------- | --------------------------------------------------- |
| Freshness   | `messages_processed_within_target / total_messages` |
| Correctness | `successful_outputs / total_outputs`                |

Avoid CPU/memory as SLIs — they are causes, not symptoms.

## Defining an SLO

Three numbers: **target**, **window**, **threshold** (for latency).

> 99.9% of `POST /orders` requests return non-5xx within 300 ms over a rolling 30 days.

Error budget:

```text
budget = (1 − 0.999) × 30 days × 24 h × 60 min = 43.2 minutes / 30 days
```

## Recording rules

Pre-aggregate SLI numerators/denominators so alerts and dashboards stay cheap.

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata: { name: orders-sli, namespace: monitoring }
spec:
  groups:
    - name: orders.sli
      interval: 30s
      rules:
        - record: sli:orders_availability:ratio_rate5m
          expr: |
            sum(rate(http_requests_total{service="orders", status!~"5.."}[5m]))
            / sum(rate(http_requests_total{service="orders"}[5m]))
        - record: sli:orders_latency:ratio_rate5m
          expr: |
            sum(rate(http_request_duration_seconds_bucket{service="orders", le="0.3"}[5m]))
            / sum(rate(http_request_duration_seconds_count{service="orders"}[5m]))
```

Repeat at 30m, 1h, 6h windows for burn-rate calculations.

## Multi-window multi-burn-rate alerts

The Google SRE workbook recipe — alerts on **fast** and **slow** burns simultaneously to balance
precision and recall.

```yaml
- alert: OrdersAvailabilityFastBurn
  expr: |
    (
      1 - sli:orders_availability:ratio_rate5m  > (14.4 * (1 - 0.999))
    )
    and
    (
      1 - sli:orders_availability:ratio_rate1h  > (14.4 * (1 - 0.999))
    )
  for: 2m
  labels: { severity: page }
  annotations:
    summary: "Orders availability burning budget 14.4× (2% of monthly budget in 1h)"
    runbook: "https://runbooks/orders-availability"

- alert: OrdersAvailabilitySlowBurn
  expr: |
    (
      1 - sli:orders_availability:ratio_rate30m > (6 * (1 - 0.999))
    )
    and
    (
      1 - sli:orders_availability:ratio_rate6h  > (6 * (1 - 0.999))
    )
  for: 15m
  labels: { severity: ticket }
  annotations:
    summary: "Orders availability burning budget 6× (5% of monthly budget in 6h)"
    runbook: "https://runbooks/orders-availability"
```

Burn-rate factors map to budget-consumption percentages:

| Burn rate | Time to exhaust 30-day budget | Page or ticket |
| --------- | ----------------------------- | -------------- |
| 14.4      | 2 days                        | Page (fast)    |
| 6         | 5 days                        | Ticket (slow)  |
| 3         | 10 days                       | Ticket         |
| 1         | 30 days                       | None           |

## Alert hygiene

- **Alert on symptoms, not causes.** "5xx error rate > X" pages; "CPU > 80%" does not.
- **Every alert has a runbook.** Linked in `annotations.runbook`. No runbook → no alert.
- **Severity:**
  - `page` — wake someone, SLO at risk
  - `ticket` — needs work this week, no immediate user impact
  - `info` — for dashboards only
- **No flapping.** Use `for:` to require sustained breach before firing.
- **Regular review.** Delete or tune alerts that fire often without action — they cause alert
  fatigue and people start ignoring real ones.
- **Silence during planned maintenance** via Alertmanager silences.

## Runbooks

A good runbook answers, in order:

1. **What does this mean?** (Plain language description of the SLO and what's burning)
2. **Likely causes** (recent deploys, dependency outages, traffic spikes)
3. **Diagnostic queries** — direct links to dashboards, log searches (e.g. ES|QL funnel
   templates from [log-search-esql.md](log-search-esql.md)), trace explorer
4. **Mitigations** in priority order (rollback, scale up, drain traffic, feature flag off)
5. **Escalation** path with on-call rotations

Store runbooks in version control next to the alert definitions; they are code.

## Notification routing

Alertmanager `route` example:

```yaml
route:
  receiver: default
  group_by: [alertname, service]
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
  routes:
    - matchers: [severity="page"]
      receiver: pagerduty
    - matchers: [severity="ticket"]
      receiver: slack-tickets
    - matchers: [severity="info"]
      receiver: "null"   # discard

receivers:
  - name: pagerduty
    pagerduty_configs:
      - service_key: <secret>
  - name: slack-tickets
    slack_configs:
      - channel: "#orders-alerts"
        send_resolved: true
  - name: "null"
```

## Validation

- Open the SLO dashboard; confirm error budget remaining is plotted
- Trigger a synthetic failure and verify the fast-burn alert fires within 2–5 minutes
- Verify each alert links to a working runbook URL
- Run a quarterly review: archive any alert that fired > 5 times with no follow-up action
