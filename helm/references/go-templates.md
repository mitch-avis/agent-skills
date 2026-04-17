# Go Template Reference

All template functions come from the **Sprig library** plus Helm built-ins (`include`, `required`,
`tpl`, `toYaml`, `lookup`). Full Sprig reference: <https://masterminds.github.io/sprig/>.

## Built-in Objects

| Object              | Description                                    |
| ------------------- | ---------------------------------------------- |
| `.Release.Name`     | Release name                                   |
| `.Release.Namespace`| Namespace the release is deployed to           |
| `.Release.IsInstall`| `true` on install, `false` on upgrade          |
| `.Release.IsUpgrade`| `true` on upgrade, `false` on install          |
| `.Release.Revision` | Revision number (starts at 1)                  |
| `.Release.Service`  | Rendering service (always "Helm")              |
| `.Chart.Name`       | Chart name from Chart.yaml                     |
| `.Chart.Version`    | Chart version from Chart.yaml                  |
| `.Chart.AppVersion` | Application version from Chart.yaml            |
| `.Values`           | Merged values (defaults + overrides)           |
| `.Template.Name`    | Current template file path                     |
| `.Template.BasePath`| Base directory of templates                    |
| `.Files`            | Access non-template files in the chart         |
| `.Capabilities`     | Cluster capabilities (API versions, K8s ver.)  |

## Flow Control

### if / else if / else

```yaml
{{- if .Values.ingress.enabled }}
  ingressClassName: {{ .Values.ingress.className }}
{{- else if .Values.gateway.enabled }}
  gatewayClassName: {{ .Values.gateway.className }}
{{- else }}
  # neither Ingress nor Gateway
{{- end }}
```

Falsy values in Go templates: `false`, `0`, `""`, `nil`, empty collections (`[]`, `{}`).

### with (scope narrowing)

`with` re-scopes `.` to a sub-object. Use `$` to access root scope inside a `with` block:

```yaml
{{- with .Values.podSecurityContext }}
securityContext:
  {{- toYaml . | nindent 2 }}
{{- end }}

# Accessing root scope inside with
{{- with .Values.ingress }}
  name: {{ $.Release.Name }}-ingress
{{- end }}
```

### range (lists)

```yaml
{{- range .Values.extraEnvVars }}
- name: {{ .name }}
  value: {{ .value | quote }}
{{- end }}
```

### range (maps with key/value)

```yaml
{{- range $key, $value := .Values.annotations }}
{{ $key }}: {{ $value | quote }}
{{- end }}
```

### range with index

```yaml
{{- range $index, $host := .Values.ingress.hosts }}
# Host {{ $index }}: {{ $host.host }}
{{- end }}
```

## Variables

Variables capture values for use in inner scopes where `.` is rebound:

```yaml
{{- $fullname := include "myapp.fullname" . -}}
{{- range .Values.ingress.hosts }}
# Inside range, "." is rebound to the current list item
# Use $fullname to access the captured value
- host: {{ .host }}
  serviceName: {{ $fullname }}
{{- end }}
```

## include vs template

Always use `include` — it captures output as a string so it can be piped. `template` writes directly
and cannot be piped:

```yaml
# CORRECT — pipeable
{{- include "myapp.labels" . | nindent 4 }}

# WRONG — cannot pipe, breaks indentation
{{- template "myapp.labels" . }}
```

## Helm Built-in Functions

### required

Fail with a clear message when a value is missing:

```yaml
image: "{{ required ".Values.image.repository is required" .Values.image.repository }}"
```

### tpl

Render a string value as a Go template (lets users pass templates in values):

```yaml
# values.yaml:  annotation: "app-{{ .Release.Name }}"
{{- if .Values.annotation }}
custom: {{ tpl .Values.annotation . }}
{{- end }}
```

### toYaml / toJson / toToml

```yaml
securityContext:
  {{- toYaml .Values.securityContext | nindent 2 }}

# JSON annotation value
annotations:
  config: {{ toJson .Values.sidecar | quote }}
```

### lookup

Query live cluster state. Returns empty dict during `--dry-run` or `helm template`:

```yaml
{{- $secret := lookup "v1" "Secret" .Release.Namespace "existing-secret" }}
{{- if $secret }}
# Reuse existing secret
{{- else }}
# Create new secret
{{- end }}

# List all ConfigMaps in namespace
{{- $cms := lookup "v1" "ConfigMap" .Release.Namespace "" }}
{{- range $cm := $cms.items }}
# {{ $cm.metadata.name }}
{{- end }}
```

### .Capabilities

Conditionally render based on cluster API versions:

```yaml
{{- if .Capabilities.APIVersions.Has "networking.k8s.io/v1" }}
apiVersion: networking.k8s.io/v1
{{- else }}
apiVersion: networking.k8s.io/v1beta1
{{- end }}

# Kubernetes version check
{{- if semverCompare ">=1.28-0" .Capabilities.KubeVersion.Version }}
# Use features available in 1.28+
{{- end }}
```

## Sprig Functions (Most Used)

### String Functions

```yaml
{{ .Values.name | upper }}              # MYAPP
{{ .Values.name | lower }}              # myapp
{{ .Values.name | title }}              # Myapp
{{ .Values.name | trim }}               # trim whitespace
{{ .Values.name | trimPrefix "v" }}     # strip prefix
{{ .Values.name | trimSuffix "-" }}     # strip suffix
{{ .Values.name | trunc 63 }}           # truncate to length
{{ .Values.name | quote }}              # wrap in double quotes
{{ .Values.name | squote }}             # wrap in single quotes
{{ .Values.name | replace "." "-" }}    # string replacement
{{ .Values.name | contains "api" }}     # boolean test
{{ .Values.name | hasPrefix "v" }}      # boolean test
{{ .Values.name | hasSuffix "-svc" }}   # boolean test
{{ printf "%s-%s" .Release.Name "app" }}# formatted string
{{ nospace .Values.name }}              # remove all whitespace
{{ repeat 3 "ha" }}                     # hahaha
{{ regexMatch "^v[0-9]" .Values.tag }}  # regex match
```

### Type Conversion

```yaml
{{ .Values.port | int }}                # to int
{{ .Values.port | toString }}           # to string
{{ .Values.flag | ternary "yes" "no" }} # conditional value
{{ atoi "42" }}                         # string to int
{{ int64 .Values.count }}               # to int64
```

### Default / Coalesce / Empty

```yaml
{{ .Values.name | default "myapp" }}
{{ coalesce .Values.name .Chart.Name "fallback" }}  # first non-empty
{{- if empty .Values.name }}
# .Values.name is falsy
{{- end }}
```

### Lists

```yaml
{{ list "a" "b" "c" }}                  # create list
{{ first .Values.hosts }}               # first element
{{ last .Values.hosts }}                # last element
{{ rest .Values.hosts }}                # all but first
{{ initial .Values.hosts }}             # all but last
{{ has "nginx" .Values.tags }}          # contains check
{{ without .Values.list "removed" }}    # remove element
{{ compact .Values.list }}              # remove empty values
{{ uniq .Values.list }}                 # deduplicate
{{ sortAlpha .Values.list }}            # alphabetical sort
{{ join "," .Values.list }}             # join to string
```

### Dictionaries

```yaml
{{- $labels := dict "app" .Chart.Name "release" .Release.Name }}
{{- $labels = merge $labels .Values.extraLabels }}
{{- $copy := deepCopy .Values.someMap }}
{{ get $labels "app" }}                 # get a key
{{ hasKey $labels "app" }}              # check key existence
{{ keys $labels | sortAlpha }}          # sorted key list
{{ values $labels }}                    # all values
{{ omit $labels "release" }}            # remove a key
{{ pick $labels "app" }}                # keep only these keys
```

### Encoding

```yaml
{{ .Values.password | b64enc }}         # Base64 encode
{{ .Values.encoded | b64dec }}          # Base64 decode
{{ .Values.data | sha256sum }}          # SHA-256 hash
{{ randAlphaNum 32 }}                   # random string
{{ genSignedCert "myapp" nil nil 365 (genCA "myca" 365) }}  # self-signed cert
```

### Date

```yaml
{{ now | date "2006-01-02" }}           # current date
{{ now | unixEpoch }}                   # Unix timestamp
```

## Whitespace Control

`{{-` trims whitespace **before** the tag, `-}}` trims **after**:

```yaml
metadata:
  labels:
    {{- include "myapp.labels" . | nindent 4 }}
    # Without {{- there would be a blank line above labels
```

Common pitfall — double trimming removes too much:

```yaml
# WRONG — eats the preceding newline AND the colon
name:{{- "value" }}  # produces "name:value" (no space)

# CORRECT
name: {{- " value" }}  # or just
name: {{ "value" }}
```

## nindent vs indent

- `nindent N` — inserts a newline **then** indents N spaces (most common)
- `indent N` — indents without a leading newline

```yaml
# nindent (adds newline first — use for block output from toYaml)
spec:
  {{- toYaml .Values.resources | nindent 2 }}

# indent (inline continuation — rare)
data: {{ .Values.data | indent 2 }}
```

## Pipeline Chaining

```yaml
# Multiple transforms chained left-to-right
{{ .Values.name | upper | trunc 63 | trimSuffix "-" | quote }}
```

## .Files

### .Files.Get (single file)

```yaml
data:
  nginx.conf: |-
    {{ .Files.Get "files/nginx.conf" | nindent 4 }}
```

### .Files.Glob (multiple files)

```yaml
data:
  {{- range $path, $content := .Files.Glob "config/*.yaml" }}
  {{ base $path }}: |-
    {{ $content | nindent 4 }}
  {{- end }}
```

### .Files.AsSecrets / .Files.AsConfig

```yaml
# Encode all matching files as base64 (for Secrets)
data:
  {{- (.Files.Glob "certs/*").AsSecrets | nindent 2 }}

# As plain strings (for ConfigMaps)
data:
  {{- (.Files.Glob "config/*").AsConfig | nindent 2 }}
```

## Global and Subchart Values

### Global values (shared across all subcharts)

```yaml
# Parent values.yaml
global:
  domain: example.com
  registry: myregistry.io

# In any template (parent or subchart)
image: "{{ .Values.global.registry }}/myapp:{{ .Chart.AppVersion }}"
```

### Subchart value overrides

```yaml
# Parent values.yaml — keys match the subchart name
postgresql:
  auth:
    username: myuser
    database: mydb
  primary:
    resources:
      requests:
        cpu: 250m
        memory: 256Mi
```

## Common Patterns

### Conditional block with default

```yaml
{{- with .Values.extraAnnotations | default dict }}
annotations:
  {{- toYaml . | nindent 4 }}
{{- end }}
```

### Generate a random secret once (persist across upgrades)

```yaml
{{- $secret := lookup "v1" "Secret" .Release.Namespace (include "myapp.fullname" .) }}
{{- $password := "" }}
{{- if $secret }}
{{- $password = index $secret.data "password" | b64dec }}
{{- else }}
{{- $password = randAlphaNum 32 }}
{{- end }}
data:
  password: {{ $password | b64enc | quote }}
```

### Multi-line YAML from a named template

```yaml
{{- define "myapp.envVars" -}}
- name: APP_NAME
  value: {{ include "myapp.fullname" . | quote }}
- name: APP_VERSION
  value: {{ .Chart.AppVersion | quote }}
{{- end }}

# Usage:
env:
  {{- include "myapp.envVars" . | nindent 2 }}
```

## Debugging Templates

```bash
# Render all templates to stdout
helm template myapp ./myapp --debug

# Render specific template
helm template myapp ./myapp -s templates/deployment.yaml

# Show computed values
helm template myapp ./myapp --show-only templates/deployment.yaml \
  -f values-prod.yaml --set image.tag=v2.0

# Validate syntax without cluster access
helm lint ./myapp

# Dry-run against cluster (validates API resources exist)
helm install myapp ./myapp --dry-run --debug
```
