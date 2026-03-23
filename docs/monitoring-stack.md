# EasyTradingApp Monitoring Stack

## Kubernetes Manifests

```
k8s/
├── monitoring/
│   ├── namespace.yaml
│   ├── prometheus/
│   │   ├── prometheus-rbac.yaml
│   │   ├── prometheus-config.yaml
│   │   ├── prometheus-deployment.yaml
│   │   └── prometheus-service.yaml
│   ├── grafana/
│   │   ├── grafana-config.yaml
│   │   ├── grafana-datasources.yaml
│   │   ├── grafana-dashboards.yaml
│   │   ├── grafana-deployment.yaml
│   │   └── grafana-service.yaml
│   └── elk/
│       ├── elasticsearch/
│       │   ├── es-statefulset.yaml
│       │   └── es-service.yaml
│       ├── kibana/
│       │   ├── kibana-deployment.yaml
│       │   └── kibana-service.yaml
│       └── logstash/
│           ├── logstash-configmap.yaml
│           └── logstash-deployment.yaml
```

## prometheus-rbac.yaml

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: monitoring
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: prometheus
  namespace: monitoring
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: prometheus
rules:
  - apiGroups: [""]
    resources:
      - nodes
      - nodes/proxy
      - services
      - endpoints
      - pods
    verbs: ["get", "list", "watch"]
  - apiGroups: [""]
    resources:
      - configmaps
    verbs: ["get"]
  - nonResourceURLs: ["/metrics"]
    verbs: ["get"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: prometheus
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: prometheus
subjects:
  - kind: ServiceAccount
    name: prometheus
    namespace: monitoring
```

## prometheus-config.yaml

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-config
  namespace: monitoring
data:
  prometheus.yml: |
    global:
      scrape_interval: 15s
      evaluation_interval: 15s

    scrape_configs:
      - job_name: 'kubernetes-apiservers'
        kubernetes_sd_configs:
          - role: endpoints
        scheme: https
        tls_config:
          ca_file: /var/run/secrets/kubernetes.io/serviceaccount/ca.crt
        bearer_token_file: /var/run/secrets/kubernetes.io/serviceaccount/token

      - job_name: 'kubernetes-nodes'
        kubernetes_sd_configs:
          - role: node
        scheme: https
        tls_config:
          ca_file: /var/run/secrets/kubernetes.io/serviceaccount/ca.crt
        bearer_token_file: /var/run/secrets/kubernetes.io/serviceaccount/token

      - job_name: 'kubernetes-pods'
        kubernetes_sd_configs:
          - role: pod
        relabel_configs:
          - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
            action: keep
            regex: true

      # Backend Application Metrics
      - job_name: 'backend'
        kubernetes_sd_configs:
          - role: pod
            namespaces:
              names:
                - easytradingapp
        relabel_configs:
          - source_labels: [__meta_kubernetes_pod_label_app]
            action: keep
            regex: backend
          - source_labels: [__meta_kubernetes_pod_name]
            action: replace
            target_label: pod
          - source_labels: [__meta_kubernetes_namespace]
            action: replace
            target_label: namespace

      # Frontend Application Metrics
      - job_name: 'frontend'
        kubernetes_sd_configs:
          - role: pod
            namespaces:
              names:
                - easytradingapp
        relabel_configs:
          - source_labels: [__meta_kubernetes_pod_label_app]
            action: keep
            regex: frontend

      # Worker Metrics
      - job_name: 'worker'
        kubernetes_sd_configs:
          - role: pod
            namespaces:
              names:
                - easytradingapp
        relabel_configs:
          - source_labels: [__meta_kubernetes_pod_label_app]
            action: keep
            regex: worker

    alerting:
      alertmanagers:
        - static_configs:
            - targets: []

    rule_files:
      - '/etc/prometheus/rules/*.yml'
```

## prometheus-deployment.yaml

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: prometheus
  namespace: monitoring
spec:
  replicas: 1
  selector:
    matchLabels:
      app: prometheus
  template:
    metadata:
      labels:
        app: prometheus
    spec:
      serviceAccountName: prometheus
      containers:
        - name: prometheus
          image: prom/prometheus:v2.47.0
          args:
            - '--config.file=/etc/prometheus/prometheus.yml'
            - '--storage.tsdb.path=/prometheus'
            - '--storage.tsdb.retention.time=30d'
            - '--web.console.libraries=/etc/prometheus/console_libraries'
            - '--web.console.templates=/etc/prometheus/consoles'
            - '--web.enable-lifecycle'
          ports:
            - containerPort: 9090
              name: http
          volumeMounts:
            - name: config
              mountPath: /etc/prometheus
            - name: storage
              mountPath: /prometheus
          resources:
            requests:
              cpu: 500m
              memory: 1Gi
            limits:
              cpu: 2
              memory: 4Gi
          livenessProbe:
            httpGet:
              path: /-/healthy
              port: 9090
            initialDelaySeconds: 30
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /-/ready
              port: 9090
            initialDelaySeconds: 5
            periodSeconds: 5
      volumes:
        - name: config
          configMap:
            name: prometheus-config
        - name: storage
          emptyDir: {}
```

## prometheus-service.yaml

```yaml
apiVersion: v1
kind: Service
metadata:
  name: prometheus
  namespace: monitoring
spec:
  type: ClusterIP
  ports:
    - port: 9090
      targetPort: 9090
      name: http
  selector:
    app: prometheus
```

## grafana-deployment.yaml

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: grafana-datasources
  namespace: monitoring
data:
  datasources.yml: |
    apiVersion: 1
    datasources:
      - name: Prometheus
        type: prometheus
        access: proxy
        url: http://prometheus:9090
        isDefault: true
        editable: true
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: grafana-dashboards
  namespace: monitoring
data:
  dashboard.yml: |
    apiVersion: 1
    providers:
      - name: 'EasyTradingApp'
        orgId: 1
        folder: ''
        type: file
        disableDeletion: false
        updateIntervalSeconds: 10
        allowUiUpdates: true
        options:
          path: /var/lib/grafana/dashboards
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: grafana
  namespace: monitoring
spec:
  replicas: 1
  selector:
    matchLabels:
      app: grafana
  template:
    metadata:
      labels:
        app: grafana
    spec:
      securityContext:
        runAsNonRoot: true
        runAsUser: 472
        fsGroup: 472
      containers:
        - name: grafana
          image: grafana/grafana:10.1.0
          ports:
            - containerPort: 3000
              name: http
          env:
            - name: GF_SECURITY_ADMIN_USER
              valueFrom:
                secretKeyRef:
                  name: grafana-credentials
                  key: admin-user
            - name: GF_SECURITY_ADMIN_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: grafana-credentials
                  key: admin-password
            - name: GF_INSTALL_PLUGINS
              value: grafana-piechart-panel
          volumeMounts:
            - name: datasources
              mountPath: /etc/grafana/provisioning/datasources
            - name: dashboards
              mountPath: /etc/grafana/provisioning/dashboards
            - name: storage
              mountPath: /var/lib/grafana
          resources:
            requests:
              cpu: 100m
              memory: 256Mi
            limits:
              cpu: 500m
              memory: 1Gi
      volumes:
        - name: datasources
          configMap:
            name: grafana-datasources
        - name: dashboards
          configMap:
            name: grafana-dashboards
        - name: storage
          emptyDir: {}
```

## elasticsearch-statefulset.yaml

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: elasticsearch
  namespace: monitoring
spec:
  serviceName: elasticsearch
  replicas: 3
  selector:
    matchLabels:
      app: elasticsearch
  template:
    metadata:
      labels:
        app: elasticsearch
    spec:
      initContainers:
        - name: fix-permissions
          image: busybox:1.36
          command:
            - sh
            - -c
            - |
              chown -R 1000:1000 /usr/share/elasticsearch/data
          securityContext:
            privileged: true
          volumeMounts:
            - name: data
              mountPath: /usr/share/elasticsearch/data
      containers:
        - name: elasticsearch
          image: docker.elastic.co/elasticsearch/elasticsearch:8.10.0
          env:
            - name: cluster.name
              value: easytradingapp-logs
            - name: discovery.seed_hosts
              value: elasticsearch-0.elasticsearch,elasticsearch-1.elasticsearch,elasticsearch-2.elasticsearch
            - name: xpack.security.enabled
              value: "true"
            - name: xpack.security.authc.anonymous.enabled
              value: "true"
            - name: ES_JAVA_OPTS
              value: -Xms2g -Xmx2g -XX:+UseG1GC
          ports:
            - containerPort: 9200
              name: http
            - containerPort: 9300
              name: transport
          volumeMounts:
            - name: data
              mountPath: /usr/share/elasticsearch/data
          resources:
            requests:
              cpu: 500m
              memory: 4Gi
            limits:
              cpu: 2
              memory: 8Gi
          readinessProbe:
            httpGet:
              path: /_cluster/health
              port: 9200
            initialDelaySeconds: 30
            periodSeconds: 10
          livenessProbe:
            httpGet:
              path: /_cluster/health
              port: 9200
            initialDelaySeconds: 60
            periodSeconds: 10
  volumeClaimTemplates:
    - metadata:
        name: data
      spec:
        accessModes: ["ReadWriteOnce"]
        storageClassName: standard
        resources:
          requests:
            storage: 50Gi
```

## logstash-configmap.yaml

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: logstash-config
  namespace: monitoring
data:
  logstash.yml: |
    http.host: 0.0.0.0
    xpack.monitoring.enabled: true
    xpack.monitoring.elasticsearch.hosts: ["http://elasticsearch:9200"]
  pipeline.conf: |
    input {
      beats {
        port => 5044
      }
      tcp {
        port => 5000
      }
    }
    filter {
      if [fields][service] == "backend" {
        json {
          source => "message"
          remove_field => "message"
        }
      }
      mutate {
        add_field => { "index_name" => "easytradingapp-%{+YYYY.MM.dd}" }
      }
    }
    output {
      elasticsearch {
        hosts => ["http://elasticsearch:9200"]
        index => "%{index_name}"
      }
    }
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: logstash
  namespace: monitoring
spec:
  replicas: 2
  selector:
    matchLabels:
      app: logstash
  template:
    metadata:
      labels:
        app: logstash
    spec:
      containers:
        - name: logstash
          image: docker.elastic.co/logstash/logstash:8.10.0
          ports:
            - containerPort: 5044
              name: beats
            - containerPort: 5000
              name: tcp
          volumeMounts:
            - name: config
              mountPath: /usr/share/logstash/pipeline
              readOnly: true
          resources:
            requests:
              cpu: 200m
              memory: 1Gi
            limits:
              cpu: 1000m
              memory: 2Gi
      volumes:
        - name: config
          configMap:
            name: logstash-config
```

## fluentd-daemonset.yaml

```yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: fluentd
  namespace: monitoring
spec:
  selector:
    matchLabels:
      app: fluentd
  template:
    metadata:
      labels:
        app: fluentd
    spec:
      serviceAccountName: fluentd
      containers:
        - name: fluentd
          image: fluent/fluentd:v1.16-1
          env:
            - name: FLUENT_ELASTICSEARCH_HOST
              value: elasticsearch
            - name: FLUENT_ELASTICSEARCH_PORT
              value: "9200"
          ports:
            - containerPort: 24224
              name: forward
          volumeMounts:
            - name: varlog
              mountPath: /var/log
            - name: varlibdockercontainers
              mountPath: /var/lib/docker/containers
            - name: config
              mountPath: /etc/fluent/config.d
          resources:
            requests:
              cpu: 100m
              memory: 200Mi
            limits:
              cpu: 500m
              memory: 1Gi
      volumes:
        - name: varlog
          hostPath:
            path: /var/log
        - name: varlibdockercontainers
          hostPath:
            path: /var/lib/docker/containers
        - name: config
          configMap:
            name: fluentd-config
```

## Dashboard Examples

### Trading Dashboard (Grafana JSON)

```json
{
  "dashboard": {
    "title": "EasyTradingApp - Trading Overview",
    "tags": ["trading", "production"],
    "timezone": "browser",
    "panels": [
      {
        "id": 1,
        "title": "Orders Per Second",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(orders_submitted_total[1m])",
            "legendFormat": "Orders/sec"
          }
        ],
        "gridPos": {"x": 0, "y": 0, "w": 12, "h": 8}
      },
      {
        "id": 2,
        "title": "Order Latency (P99)",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.99, rate(order_latency_seconds_bucket[5m]))",
            "legendFormat": "P99 Latency"
          }
        ],
        "gridPos": {"x": 12, "y": 0, "w": 12, "h": 8}
      },
      {
        "id": 3,
        "title": "Active Strategies",
        "type": "stat",
        "targets": [
          {
            "expr": "strategies_running_total",
            "legendFormat": "Running"
          }
        ],
        "gridPos": {"x": 0, "y": 8, "w": 6, "h": 4}
      },
      {
        "id": 4,
        "title": "Daily P&L",
        "type": "graph",
        "targets": [
          {
            "expr": "sum by (date) (daily_pnl)",
            "legendFormat": "{{date}}"
          }
        ],
        "gridPos": {"x": 6, "y": 8, "w": 18, "h": 8}
      },
      {
        "id": 5,
        "title": "Error Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(errors_total[5m])",
            "legendFormat": "Errors/sec"
          }
        ],
        "gridPos": {"x": 0, "y": 16, "w": 12, "h": 8}
      },
      {
        "id": 6,
        "title": "System Resources",
        "type": "graph",
        "targets": [
          {
            "expr": "container_cpu_usage_seconds_total{pod=~\"backend-.*\"}",
            "legendFormat": "CPU - {{pod}}"
          },
          {
            "expr": "container_memory_usage_bytes{pod=~\"backend-.*\"}",
            "legendFormat": "Memory - {{pod}}"
          }
        ],
        "gridPos": {"x": 12, "y": 16, "w": 12, "h": 8}
      }
    ]
  }
}
```

## Alert Rules

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-alerts
  namespace: monitoring
data:
  alerts.yml: |
    groups:
      - name: trading_rules
        interval: 30s
        rules:
          - alert: HighErrorRate
            expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
            for: 2m
            labels:
              severity: critical
            annotations:
              summary: "High error rate detected"
              description: "Error rate is {{ $value | humanizePercentage }}"

          - alert: OrderExecutionFailure
            expr: rate(orders_failed_total[5m]) > 0.01
            for: 1m
            labels:
              severity: warning
            annotations:
              summary: "Order execution failures"

          - alert: DailyLossLimit
            expr: daily_pnl < -1000
            for: 0m
            labels:
              severity: critical
            annotations:
              summary: "Daily loss limit breached"

          - alert: HighLatency
            expr: histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m])) > 2
            for: 5m
            labels:
              severity: warning
            annotations:
              summary: "High API latency detected"

          - alert: PodNotReady
            expr: kube_pod_status_ready{namespace="easytradingapp",condition="true"} == 0
            for: 5m
            labels:
              severity: warning
            annotations:
              summary: "Pod not ready"

          - alert: PodCrashLooping
            expr: rate(kube_pod_container_status_restarts_total[15m]) > 0.1
            for: 2m
            labels:
              severity: critical
            annotations:
              summary: "Pod is crash looping"

          - alert: DatabaseConnectionErrors
            expr: rate(database_connections_errors_total[5m]) > 0
            for: 1m
            labels:
              severity: warning
            annotations:
              summary: "Database connection errors"

          - alert: HighMemoryUsage
            expr: (container_memory_usage_bytes / container_spec_memory_limit_bytes) > 0.9
            for: 5m
            labels:
              severity: warning
            annotations:
              summary: "High memory usage"
```
