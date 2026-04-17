# Helm Template Patterns

## Template Helpers (\_helpers.tpl)

```yaml
{{/*
Expand the name of the chart.
*/}}
{{- define "myapp.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Fully qualified app name (truncated to 63 chars).
*/}}
{{- define "myapp.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Chart label value.
*/}}
{{- define "myapp.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels.
*/}}
{{- define "myapp.labels" -}}
helm.sh/chart: {{ include "myapp.chart" . }}
{{ include "myapp.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels.
*/}}
{{- define "myapp.selectorLabels" -}}
app.kubernetes.io/name: {{ include "myapp.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
ServiceAccount name.
*/}}
{{- define "myapp.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "myapp.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Image reference helper — centralizes tag/digest logic.
*/}}
{{- define "myapp.image" -}}
{{- if .Values.image.digest }}
{{- printf "%s@%s" .Values.image.repository .Values.image.digest }}
{{- else }}
{{- printf "%s:%s" .Values.image.repository (.Values.image.tag | default .Chart.AppVersion) }}
{{- end }}
{{- end }}
```

## deployment.yaml

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ include "myapp.fullname" . }}
  labels:
    {{- include "myapp.labels" . | nindent 4 }}
spec:
  {{- if not .Values.autoscaling.enabled }}
  replicas: {{ .Values.replicaCount }}
  {{- end }}
  selector:
    matchLabels:
      {{- include "myapp.selectorLabels" . | nindent 6 }}
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  template:
    metadata:
      annotations:
        checksum/config: {{ include (print $.Template.BasePath "/configmap.yaml") . | sha256sum }}
        {{- with .Values.podAnnotations }}
        {{- toYaml . | nindent 8 }}
        {{- end }}
      labels:
        {{- include "myapp.selectorLabels" . | nindent 8 }}
    spec:
      {{- with .Values.imagePullSecrets }}
      imagePullSecrets:
        {{- toYaml . | nindent 8 }}
      {{- end }}
      serviceAccountName: {{ include "myapp.serviceAccountName" . }}
      securityContext:
        {{- toYaml .Values.podSecurityContext | nindent 8 }}
      {{- with .Values.topologySpreadConstraints }}
      topologySpreadConstraints:
        {{- toYaml . | nindent 8 }}
      {{- end }}
      containers:
        - name: {{ .Chart.Name }}
          securityContext:
            {{- toYaml .Values.securityContext | nindent 12 }}
          image: {{ include "myapp.image" . | quote }}
          imagePullPolicy: {{ .Values.image.pullPolicy }}
          ports:
            - name: http
              containerPort: {{ .Values.service.targetPort }}
              protocol: TCP
          {{- if .Values.startupProbe.enabled }}
          startupProbe:
            httpGet:
              path: {{ .Values.startupProbe.path | default "/healthz" }}
              port: http
            failureThreshold: {{ .Values.startupProbe.failureThreshold | default 30 }}
            periodSeconds: {{ .Values.startupProbe.periodSeconds | default 10 }}
          {{- end }}
          livenessProbe:
            httpGet:
              path: {{ .Values.livenessProbe.path | default "/healthz" }}
              port: http
            initialDelaySeconds: {{ .Values.livenessProbe.initialDelaySeconds | default 30 }}
            periodSeconds: {{ .Values.livenessProbe.periodSeconds | default 10 }}
          readinessProbe:
            httpGet:
              path: {{ .Values.readinessProbe.path | default "/ready" }}
              port: http
            initialDelaySeconds: {{ .Values.readinessProbe.initialDelaySeconds | default 10 }}
            periodSeconds: {{ .Values.readinessProbe.periodSeconds | default 5 }}
          {{- with .Values.lifecycle }}
          lifecycle:
            {{- toYaml . | nindent 12 }}
          {{- end }}
          resources:
            {{- toYaml .Values.resources | nindent 12 }}
          {{- with .Values.extraEnvVars }}
          env:
            {{- toYaml . | nindent 12 }}
          {{- end }}
          {{- with .Values.extraVolumeMounts }}
          volumeMounts:
            {{- toYaml . | nindent 12 }}
          {{- end }}
      {{- with .Values.nodeSelector }}
      nodeSelector:
        {{- toYaml . | nindent 8 }}
      {{- end }}
      {{- with .Values.affinity }}
      affinity:
        {{- toYaml . | nindent 8 }}
      {{- end }}
      {{- with .Values.tolerations }}
      tolerations:
        {{- toYaml . | nindent 8 }}
      {{- end }}
      terminationGracePeriodSeconds: {{ .Values.terminationGracePeriodSeconds | default 30 }}
      {{- with .Values.extraVolumes }}
      volumes:
        {{- toYaml . | nindent 8 }}
      {{- end }}
```

## service.yaml

```yaml
apiVersion: v1
kind: Service
metadata:
  name: {{ include "myapp.fullname" . }}
  labels:
    {{- include "myapp.labels" . | nindent 4 }}
  {{- with .Values.service.annotations }}
  annotations:
    {{- toYaml . | nindent 4 }}
  {{- end }}
spec:
  type: {{ .Values.service.type }}
  ports:
    - port: {{ .Values.service.port }}
      targetPort: http
      protocol: TCP
      name: http
  selector:
    {{- include "myapp.selectorLabels" . | nindent 4 }}
```

## Headless Service (for StatefulSets)

```yaml
{{- if eq .Values.workloadType "statefulset" -}}
apiVersion: v1
kind: Service
metadata:
  name: {{ include "myapp.fullname" . }}-headless
  labels:
    {{- include "myapp.labels" . | nindent 4 }}
spec:
  type: ClusterIP
  clusterIP: None
  ports:
    - port: {{ .Values.service.port }}
      targetPort: http
      protocol: TCP
      name: http
  selector:
    {{- include "myapp.selectorLabels" . | nindent 4 }}
{{- end }}
```

## ingress.yaml

```yaml
{{- if .Values.ingress.enabled -}}
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: {{ include "myapp.fullname" . }}
  labels:
    {{- include "myapp.labels" . | nindent 4 }}
  {{- with .Values.ingress.annotations }}
  annotations:
    {{- toYaml . | nindent 4 }}
  {{- end }}
spec:
  {{- if .Values.ingress.className }}
  ingressClassName: {{ .Values.ingress.className }}
  {{- end }}
  {{- if .Values.ingress.tls }}
  tls:
    {{- range .Values.ingress.tls }}
    - hosts:
        {{- range .hosts }}
        - {{ . | quote }}
        {{- end }}
      secretName: {{ .secretName }}
    {{- end }}
  {{- end }}
  rules:
    {{- range .Values.ingress.hosts }}
    - host: {{ .host | quote }}
      http:
        paths:
          {{- range .paths }}
          - path: {{ .path }}
            pathType: {{ .pathType }}
            backend:
              service:
                name: {{ include "myapp.fullname" $ }}
                port:
                  number: {{ $.Values.service.port }}
          {{- end }}
    {{- end }}
{{- end }}
```

## configmap.yaml

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: {{ include "myapp.fullname" . }}
  labels:
    {{- include "myapp.labels" . | nindent 4 }}
data:
  {{- range $key, $value := .Values.config }}
  {{ $key }}: {{ $value | quote }}
  {{- end }}
  {{- if .Values.configFiles }}
  {{- range $name, $content := .Values.configFiles }}
  {{ $name }}: |-
    {{ $content | nindent 4 }}
  {{- end }}
  {{- end }}
```

## secret.yaml

```yaml
{{- if .Values.secret.create -}}
apiVersion: v1
kind: Secret
metadata:
  name: {{ include "myapp.fullname" . }}
  labels:
    {{- include "myapp.labels" . | nindent 4 }}
type: {{ .Values.secret.type | default "Opaque" }}
data:
  {{- range $key, $value := .Values.secret.data }}
  {{ $key }}: {{ $value | b64enc | quote }}
  {{- end }}
stringData:
  {{- range $key, $value := .Values.secret.stringData }}
  {{ $key }}: {{ $value | quote }}
  {{- end }}
{{- end }}
```

## serviceaccount.yaml

```yaml
{{- if .Values.serviceAccount.create -}}
apiVersion: v1
kind: ServiceAccount
metadata:
  name: {{ include "myapp.serviceAccountName" . }}
  labels:
    {{- include "myapp.labels" . | nindent 4 }}
  {{- with .Values.serviceAccount.annotations }}
  annotations:
    {{- toYaml . | nindent 4 }}
  {{- end }}
automountServiceAccountToken: {{ .Values.serviceAccount.automount | default false }}
{{- end }}
```

## rbac.yaml

```yaml
{{- if .Values.rbac.create -}}
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: {{ include "myapp.fullname" . }}
  labels:
    {{- include "myapp.labels" . | nindent 4 }}
rules:
  {{- toYaml .Values.rbac.rules | nindent 2 }}
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: {{ include "myapp.fullname" . }}
  labels:
    {{- include "myapp.labels" . | nindent 4 }}
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: {{ include "myapp.fullname" . }}
subjects:
  - kind: ServiceAccount
    name: {{ include "myapp.serviceAccountName" . }}
    namespace: {{ .Release.Namespace }}
{{- end }}
```

## networkpolicy.yaml

```yaml
{{- if .Values.networkPolicy.enabled -}}
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: {{ include "myapp.fullname" . }}
  labels:
    {{- include "myapp.labels" . | nindent 4 }}
spec:
  podSelector:
    matchLabels:
      {{- include "myapp.selectorLabels" . | nindent 6 }}
  policyTypes:
    - Ingress
    - Egress
  ingress:
    # Allow traffic from ingress controller
    {{- if .Values.ingress.enabled }}
    - from:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: {{ .Values.networkPolicy.ingressNamespace | default "ingress-nginx" }}
      ports:
        - protocol: TCP
          port: {{ .Values.service.targetPort }}
    {{- end }}
    # Allow Prometheus scraping
    {{- if .Values.networkPolicy.allowPrometheus }}
    - from:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: {{ .Values.networkPolicy.prometheusNamespace | default "monitoring" }}
      ports:
        - protocol: TCP
          port: {{ .Values.networkPolicy.metricsPort | default 9090 }}
    {{- end }}
    {{- with .Values.networkPolicy.extraIngress }}
    {{- toYaml . | nindent 4 }}
    {{- end }}
  egress:
    # Allow DNS
    - to:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: kube-system
      ports:
        - protocol: UDP
          port: 53
    {{- with .Values.networkPolicy.extraEgress }}
    {{- toYaml . | nindent 4 }}
    {{- end }}
{{- end }}
```

## hpa.yaml

```yaml
{{- if .Values.autoscaling.enabled -}}
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: {{ include "myapp.fullname" . }}
  labels:
    {{- include "myapp.labels" . | nindent 4 }}
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: {{ ternary "StatefulSet" "Deployment" (eq .Values.workloadType "statefulset") }}
    name: {{ include "myapp.fullname" . }}
  minReplicas: {{ .Values.autoscaling.minReplicas }}
  maxReplicas: {{ .Values.autoscaling.maxReplicas }}
  metrics:
    {{- if .Values.autoscaling.targetCPUUtilizationPercentage }}
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: {{ .Values.autoscaling.targetCPUUtilizationPercentage }}
    {{- end }}
    {{- if .Values.autoscaling.targetMemoryUtilizationPercentage }}
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: {{ .Values.autoscaling.targetMemoryUtilizationPercentage }}
    {{- end }}
  {{- with .Values.autoscaling.behavior }}
  behavior:
    {{- toYaml . | nindent 4 }}
  {{- end }}
{{- end }}
```

## pdb.yaml

```yaml
{{- if .Values.podDisruptionBudget.enabled -}}
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: {{ include "myapp.fullname" . }}
  labels:
    {{- include "myapp.labels" . | nindent 4 }}
spec:
  {{- if .Values.podDisruptionBudget.minAvailable }}
  minAvailable: {{ .Values.podDisruptionBudget.minAvailable }}
  {{- else }}
  maxUnavailable: {{ .Values.podDisruptionBudget.maxUnavailable | default 1 }}
  {{- end }}
  selector:
    matchLabels:
      {{- include "myapp.selectorLabels" . | nindent 6 }}
{{- end }}
```

## statefulset.yaml

```yaml
{{- if eq .Values.workloadType "statefulset" -}}
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: {{ include "myapp.fullname" . }}
  labels:
    {{- include "myapp.labels" . | nindent 4 }}
spec:
  serviceName: {{ include "myapp.fullname" . }}-headless
  replicas: {{ .Values.replicaCount }}
  podManagementPolicy: {{ .Values.podManagementPolicy | default "OrderedReady" }}
  updateStrategy:
    type: RollingUpdate
  selector:
    matchLabels:
      {{- include "myapp.selectorLabels" . | nindent 6 }}
  template:
    metadata:
      annotations:
        checksum/config: {{ include (print $.Template.BasePath "/configmap.yaml") . | sha256sum }}
        {{- with .Values.podAnnotations }}
        {{- toYaml . | nindent 8 }}
        {{- end }}
      labels:
        {{- include "myapp.selectorLabels" . | nindent 8 }}
    spec:
      serviceAccountName: {{ include "myapp.serviceAccountName" . }}
      securityContext:
        {{- toYaml .Values.podSecurityContext | nindent 8 }}
      containers:
        - name: {{ .Chart.Name }}
          securityContext:
            {{- toYaml .Values.securityContext | nindent 12 }}
          image: {{ include "myapp.image" . | quote }}
          imagePullPolicy: {{ .Values.image.pullPolicy }}
          ports:
            - name: http
              containerPort: {{ .Values.service.targetPort }}
          livenessProbe:
            httpGet:
              path: {{ .Values.livenessProbe.path | default "/healthz" }}
              port: http
            initialDelaySeconds: {{ .Values.livenessProbe.initialDelaySeconds | default 30 }}
            periodSeconds: {{ .Values.livenessProbe.periodSeconds | default 10 }}
          readinessProbe:
            httpGet:
              path: {{ .Values.readinessProbe.path | default "/ready" }}
              port: http
            initialDelaySeconds: {{ .Values.readinessProbe.initialDelaySeconds | default 10 }}
            periodSeconds: {{ .Values.readinessProbe.periodSeconds | default 5 }}
          resources:
            {{- toYaml .Values.resources | nindent 12 }}
          volumeMounts:
            - name: data
              mountPath: {{ .Values.persistence.mountPath | default "/data" }}
            {{- with .Values.extraVolumeMounts }}
            {{- toYaml . | nindent 12 }}
            {{- end }}
      {{- with .Values.nodeSelector }}
      nodeSelector:
        {{- toYaml . | nindent 8 }}
      {{- end }}
      {{- with .Values.affinity }}
      affinity:
        {{- toYaml . | nindent 8 }}
      {{- end }}
      {{- with .Values.tolerations }}
      tolerations:
        {{- toYaml . | nindent 8 }}
      {{- end }}
      terminationGracePeriodSeconds: {{ .Values.terminationGracePeriodSeconds | default 30 }}
  volumeClaimTemplates:
    - metadata:
        name: data
        labels:
          {{- include "myapp.selectorLabels" . | nindent 10 }}
      spec:
        accessModes: ["ReadWriteOnce"]
        {{- if .Values.persistence.storageClass }}
        storageClassName: {{ .Values.persistence.storageClass }}
        {{- end }}
        resources:
          requests:
            storage: {{ .Values.persistence.size | default "10Gi" }}
{{- end }}
```

## Hooks

### Pre-Install/Upgrade (Database Migration)

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: {{ include "myapp.fullname" . }}-migration
  annotations:
    "helm.sh/hook": pre-install,pre-upgrade
    "helm.sh/hook-weight": "0"
    "helm.sh/hook-delete-policy": before-hook-creation,hook-succeeded
spec:
  backoffLimit: 3
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: migrate
          image: {{ include "myapp.image" . | quote }}
          command: ["/app/migrate", "up"]
          env:
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: {{ include "myapp.fullname" . }}
                  key: database-url
```

### Post-Install Notification

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: {{ include "myapp.fullname" . }}-notify
  annotations:
    "helm.sh/hook": post-install,post-upgrade
    "helm.sh/hook-weight": "10"
    "helm.sh/hook-delete-policy": before-hook-creation,hook-succeeded
spec:
  backoffLimit: 1
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: notify
          image: curlimages/curl:8.5.0
          command:
            - curl
            - -X
            - POST
            - -H
            - "Content-Type: application/json"
            - -d
            - '{"text":"{{ include "myapp.fullname" . }} deployed to {{ .Release.Namespace }}"}'
            - {{ required "notifications.webhookUrl required" .Values.notifications.webhookUrl }}
```

### Test Hook

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: {{ include "myapp.fullname" . }}-test
  annotations:
    "helm.sh/hook": test
    "helm.sh/hook-delete-policy": before-hook-creation,hook-succeeded
spec:
  restartPolicy: Never
  containers:
    - name: test
      image: curlimages/curl:8.5.0
      command: ["curl", "-f"]
      args:
        - "http://{{ include "myapp.fullname" . }}:{{ .Values.service.port }}/health"
```

## Complete values.yaml Reference

```yaml
replicaCount: 3

image:
  repository: myregistry.io/myapp
  pullPolicy: IfNotPresent
  tag: ""       # Overrides appVersion
  digest: ""    # If set, takes precedence over tag

imagePullSecrets:
  - name: registry-secret

nameOverride: ""
fullnameOverride: ""

serviceAccount:
  create: true
  annotations: {}
  name: ""
  automount: false

podAnnotations:
  prometheus.io/scrape: "true"
  prometheus.io/port: "9090"

podSecurityContext:
  runAsNonRoot: true
  runAsUser: 1000
  fsGroup: 2000
  seccompProfile:
    type: RuntimeDefault

securityContext:
  allowPrivilegeEscalation: false
  readOnlyRootFilesystem: true
  capabilities:
    drop: ["ALL"]

service:
  type: ClusterIP
  port: 80
  targetPort: 8080
  annotations: {}

ingress:
  enabled: true
  className: nginx
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
  hosts:
    - host: myapp.example.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: myapp-tls
      hosts:
        - myapp.example.com

resources:
  requests:
    cpu: 250m
    memory: 256Mi
  limits:
    cpu: 500m
    memory: 512Mi

autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70
  targetMemoryUtilizationPercentage: 80
  behavior: {}

startupProbe:
  enabled: false
  path: /healthz
  failureThreshold: 30
  periodSeconds: 10

livenessProbe:
  path: /healthz
  initialDelaySeconds: 30
  periodSeconds: 10

readinessProbe:
  path: /ready
  initialDelaySeconds: 10
  periodSeconds: 5

lifecycle: {}
# preStop:
#   exec:
#     command: ["/bin/sh", "-c", "sleep 15"]

terminationGracePeriodSeconds: 30

affinity:
  podAntiAffinity:
    preferredDuringSchedulingIgnoredDuringExecution:
      - weight: 100
        podAffinityTerm:
          labelSelector:
            matchExpressions:
              - key: app.kubernetes.io/name
                operator: In
                values: ["myapp"]
          topologyKey: kubernetes.io/hostname

topologySpreadConstraints: []
nodeSelector: {}
tolerations: []

config: {}
configFiles: {}

secret:
  create: false
  type: Opaque
  data: {}
  stringData: {}

networkPolicy:
  enabled: true
  ingressNamespace: ingress-nginx
  allowPrometheus: true
  prometheusNamespace: monitoring
  metricsPort: 9090
  extraIngress: []
  extraEgress: []

rbac:
  create: false
  rules: []

podDisruptionBudget:
  enabled: true
  minAvailable: ""
  maxUnavailable: 1

# StatefulSet mode: set workloadType to "statefulset"
workloadType: deployment
persistence:
  storageClass: ""
  size: 10Gi
  mountPath: /data
podManagementPolicy: OrderedReady

extraEnvVars: []
extraVolumes: []
extraVolumeMounts: []
```
