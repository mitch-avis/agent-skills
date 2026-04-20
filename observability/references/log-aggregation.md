# Log Aggregation

Centralize logs from many services into one searchable store. Covers shippers (Vector, Fluent Bit,
Filebeat), backends (Loki, ELK/Elastic), Kubernetes integration, and parsing.

## Table of Contents

- [Log Aggregation](#log-aggregation)
  - [Table of Contents](#table-of-contents)
  - [Choosing a stack](#choosing-a-stack)
  - [Collection patterns](#collection-patterns)
  - [Vector](#vector)
  - [Fluent Bit](#fluent-bit)
  - [Loki + Promtail / Grafana Agent](#loki--promtail--grafana-agent)
  - [ELK / Elastic stack](#elk--elastic-stack)
  - [Kubernetes patterns](#kubernetes-patterns)
    - [Sidecar exception](#sidecar-exception)
  - [Retention and cost](#retention-and-cost)

## Choosing a stack

| Stack                                 | Best for                                          | Trade-off                             |                            |
| ------------------------------------- | ------------------------------------------------- | ------------------------------------- | -------------------------- |
| Loki + Grafana                        | Cheap, label-indexed, great with Prometheus/Tempo | Full-text search is slower            |                            |
| Elastic / ELK                         | Rich full-text search, Kibana, ES\                | QL, ML rules                          | Heavier infra, higher cost |
| OpenSearch                            | OSS Elastic alternative                           | Some plugin gaps                      |                            |
| Cloud SaaS (Datadog, Honeycomb, etc.) | No infra to run                                   | Per-GB ingest cost grows fast         |                            |
| Vector → object store (S3, GCS)       | Cheap long-term archive                           | No search; pair with one of the above |                            |

Default recommendation for self-hosted: **Loki for logs, Mimir/Prometheus for metrics, Tempo for
traces, Grafana for everything**.

## Collection patterns

| Pattern              | When to use                                                    |
| -------------------- | -------------------------------------------------------------- |
| Stdout → node agent  | Containers / Kubernetes — agent reads container log files      |
| Sidecar              | When stdout is unavailable or pre-processing per-pod is needed |
| Direct push from app | Serverless / edge — app sends logs to ingest endpoint          |
| Syslog / journald    | VMs and bare metal                                             |

Apps should write **JSON to stdout**. Let the platform deal with shipping. Do not rotate or write
log files from the application itself in containerized environments.

## Vector

Modern, fast, written in Rust. One agent for logs/metrics/traces.

```toml
# /etc/vector/vector.toml

[sources.app_logs]
type = "kubernetes_logs"

[transforms.parse_json]
type = "remap"
inputs = ["app_logs"]
source = '''
parsed, err = parse_json(.message)
if err == null { . = merge(., parsed) }
'''

[transforms.redact]
type = "remap"
inputs = ["parse_json"]
source = '''
if exists(.password)      { .password = "[REDACTED]" }
if exists(.authorization) { .authorization = "[REDACTED]" }
'''

[sinks.loki]
type = "loki"
inputs = ["redact"]
endpoint = "http://loki:3100"
labels.service = "{{ kubernetes.labels.\"app.kubernetes.io/name\" }}"
labels.namespace = "{{ kubernetes.namespace }}"
encoding.codec = "json"

[sinks.s3_archive]
type = "aws_s3"
inputs = ["redact"]
bucket = "logs-archive"
key_prefix = "raw/%Y/%m/%d/"
compression = "gzip"
encoding.codec = "ndjson"
```

## Fluent Bit

Lightweight C agent, ubiquitous in Kubernetes. DaemonSet config:

```yaml
[INPUT]
    Name              tail
    Path              /var/log/containers/*.log
    Parser            cri
    Tag               kube.*
    Refresh_Interval  5

[FILTER]
    Name                kubernetes
    Match               kube.*
    Merge_Log           On
    K8S-Logging.Parser  On

[FILTER]
    Name      modify
    Match     *
    Remove    password
    Remove    token

[OUTPUT]
    Name        loki
    Match       *
    Host        loki
    Port        3100
    Labels      job=fluent-bit, $kubernetes['namespace_name'], $kubernetes['labels']['app']
```

## Loki + Promtail / Grafana Agent

Loki indexes labels, not log content — cheap and fast for label-bounded queries. Use LogQL:

```logql
# All errors from the orders service in the last 15m
{service="orders", environment="prod"} |= "error"

# JSON log filter — pull a field then filter
{service="orders"} | json | status_code >= 500

# Rate of 5xx by route
sum by (route) (
  rate({service="orders"} | json | status_code >= 500 [5m])
)
```

Use a small bounded label set (`service`, `environment`, `level`, `pod`); push everything else into
the JSON payload.

## ELK / Elastic stack

Heavy but rich. Logstash for ETL, Elasticsearch for storage, Kibana for UI.

`docker-compose.yml`:

```yaml
services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.13.0
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
      - ES_JAVA_OPTS=-Xms1g -Xmx1g
    ports: ["9200:9200"]
    volumes: [esdata:/usr/share/elasticsearch/data]

  logstash:
    image: docker.elastic.co/logstash/logstash:8.13.0
    ports: ["5044:5044"]
    volumes:
      - ./logstash.conf:/usr/share/logstash/pipeline/logstash.conf
    depends_on: [elasticsearch]

  kibana:
    image: docker.elastic.co/kibana/kibana:8.13.0
    ports: ["5601:5601"]
    environment:
      ELASTICSEARCH_HOSTS: http://elasticsearch:9200
    depends_on: [elasticsearch]

volumes: { esdata: {} }
```

`logstash.conf`:

```ruby
input {
  beats { port => 5044 }
}

filter {
  json { source => "message" }
  date { match => ["@timestamp", "ISO8601"] }
  mutate {
    remove_field => ["password", "token", "authorization"]
  }
}

output {
  elasticsearch {
    hosts => ["http://elasticsearch:9200"]
    index => "logs-%{[service][name]}-%{+YYYY.MM.dd}"
  }
}
```

For querying once data is in Elastic, see [log-search-esql.md](log-search-esql.md).

## Kubernetes patterns

- Always write to **stdout/stderr** — never to a file inside the container
- Set the container log driver to `json-file` (default) and let the node agent read
  `/var/log/containers/*.log`
- Tag every log line with pod/namespace/container metadata via the agent (Fluent Bit's `kubernetes`
  filter, Vector's `kubernetes_logs` source)
- Apply a per-namespace label budget — limits high-cardinality labels by tenant
- Set ResourceQuotas on the logging namespace so a runaway logger cannot eat the cluster

### Sidecar exception

Use a sidecar only when:

- The app cannot be modified to write JSON to stdout
- You need per-pod buffering before shipping
- Multiple log streams must be split (e.g. access vs error logs from nginx)

## Retention and cost

- Hot tier (queryable, expensive): 7–30 days
- Warm tier (slow query, cheap): 30–90 days
- Cold archive (S3/GCS, restore-only): 1+ years
- Define retention per index/stream by `service.name` × `log.level`
- Drop DEBUG before ingest (filter at the agent)
- Sample high-volume INFO at the agent if needed (see
  [structured-logging.md](structured-logging.md#high-volume-sampling))
- Track `ingest_bytes_total` per service as a metric; alert on sudden 10× growth
