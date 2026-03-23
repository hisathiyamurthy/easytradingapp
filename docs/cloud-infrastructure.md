# EasyTradingApp - Cloud Infrastructure Design

**Version:** 1.0  
**Date:** March 2026  
**Cloud Provider:** AWS (Primary)  
**Region:** us-east-1 (Primary), us-west-2 (DR)

---

## 1. AWS Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                          AWS GLOBAL                                                 │
├─────────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                     │
│  ┌───────────────────────────────────────────────────────────────────────────────────────────────┐  │
│  │                                    ROUTE 53 DNS                                               │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │  │
│  │  │ easytrade.  │  │ api.        │  │ ws.         │  │ admin.      │  │ docs.       │     │  │
│  │  │ app.com     │  │ easytrade.  │  │ easytrade.  │  │ easytrade.  │  │ easytrade.  │     │  │
│  │  │             │  │ app.com     │  │ app.com     │  │ app.com     │  │ app.com     │     │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘     │  │
│  │       │               │               │               │               │                  │  │
│  │       └───────────────┴───────────────┴───────────────┴───────────────┘                  │  │
│  └───────────────────────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                                     │
│  ┌───────────────────────────────────────────────────────────────────────────────────────────────┐  │
│  │                                    CLOUDFRONT CDN                                              │  │
│  │  ┌─────────────────────────────────────────────────────────────────────────────────────┐    │  │
│  │  │  Static Assets (React Build) | API Documentation | Error Pages                    │    │  │
│  │  └─────────────────────────────────────────────────────────────────────────────────────┘    │  │
│  └───────────────────────────────────────────────────────────────────────────────────────────────┘  │
│                                              │                                                            │
│                                              ▼                                                            │
│  ┌───────────────────────────────────────────────────────────────────────────────────────────────┐  │
│  │                                    WAF V2 (Web ACL)                                           │  │
│  │  - Rate limiting rules                                                                  │    │  │
│  │  - OWASP Top 10 protection                                                               │    │  │
│  │  - IP reputation rules                                                                   │    │  │
│  │  - Geographic blocking (optional)                                                         │    │  │
│  └───────────────────────────────────────────────────────────────────────────────────────────────┘  │
│                                              │                                                            │
└──────────────────────────────────────────────┼────────────────────────────────────────────────────┘
                                               │
                    ┌──────────────────────────┼──────────────────────────┐
                    │                          │                          │
                    ▼                          ▼                          ▼
    ┌───────────────────────────────────────────────┐  ┌───────────────────────────────────────────┐
    │          VPC PRIMARY (us-east-1)              │  │          VPC DR (us-west-2)             │
    │  ┌─────────────────────────────────────────┐  │  │  ┌─────────────────────────────────────┐  │
    │  │  Public Subnets (DMZ) 10.0.1.0/24      │  │  │  │  Public Subnets 10.1.1.0/24        │  │
    │  │  10.0.2.0/24                          │  │  │  │  10.1.2.0/24                        │  │
    │  │  ALB, NAT Gateway, VPN                │  │  │  │  ALB, NAT Gateway                   │  │
    │  └─────────────────────────────────────────┘  │  │  └─────────────────────────────────────┘  │
    │                                             │  │                                           │
    │  ┌─────────────────────────────────────────┐  │  │  ┌─────────────────────────────────────┐  │
    │  │  Private Subnets (App) 10.0.101.0/24  │  │  │  │  Private Subnets 10.1.101.0/24      │  │
    │  │  10.0.102.0/24                        │  │  │  │  10.1.102.0/24                      │  │
    │  │  EKS Cluster Nodes                     │  │  │  │  EKS Cluster Nodes                   │  │
    │  └─────────────────────────────────────────┘  │  │  └─────────────────────────────────────┘  │
    │                                             │  │                                           │
    │  ┌─────────────────────────────────────────┐  │  │  ┌─────────────────────────────────────┐  │
    │  │  Private Subnets (Data) 10.0.201.0/24 │  │  │  │  Private Subnets 10.1.201.0/24      │  │
    │  │  10.0.202.0/24                        │  │  │  │  10.1.202.0/24                      │  │
    │  │  RDS, ElastiCache, MSK                 │  │  │  │  RDS Read Replica, ElastiCache      │  │
    │  └─────────────────────────────────────────┘  │  │  └─────────────────────────────────────┘  │
    └───────────────────────────────────────────────┘  └───────────────────────────────────────────┘
```

---

## 2. Network Architecture

### 2.1 VPC Configuration

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              VPC DETAILS                                             │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  PRIMARY VPC (us-east-1)                                                             │
│  ├── CIDR: 10.0.0.0/16                                                               │
│  ├── Availability Zones: us-east-1a, us-east-1b, us-east-1c                         │
│  ├── DNS: Route 53 private hosted zone                                              │
│  ├── Flow Logs: CloudWatch Logs (retention 30 days)                                 │
│  └── VPN: Site-to-Site (for on-prem backup)                                        │
│                                                                                      │
│  DR VPC (us-west-2)                                                                  │
│  ├── CIDR: 10.1.0.0/16                                                               │
│  ├── Availability Zones: us-west-2a, us-west-2b, us-west-2c                         │
│  └── Peering: Cross-region VPC peering                                              │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Subnet Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              SUBNET DESIGN                                           │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  PUBLIC SUBNETS (DMZ) - 3 AZs                                                       │
│  ┌──────────────────┬─────────────┬─────────────┬────────────────────────────────┐ │
│  │ Subnet           │ AZ         │ CIDR        │ Resources                     │ │
│  ├──────────────────┼─────────────┼─────────────┼────────────────────────────────┤ │
│  │ public-app-1a    │ us-east-1a │ 10.0.1.0/24 │ ALB, NAT Gateway             │ │
│  │ public-app-1b    │ us-east-1b │ 10.0.2.0/24 │ ALB, NAT Gateway             │ │
│  │ public-app-1c    │ us-east-1c │ 10.0.3.0/24 │ ALB, NAT Gateway             │ │
│  └──────────────────┴─────────────┴─────────────┴────────────────────────────────┘ │
│                                                                                      │
│  PRIVATE APP SUBNETS - 3 AZs                                                        │
│  ┌──────────────────┬─────────────┬─────────────┬────────────────────────────────┐ │
│  │ Subnet           │ AZ         │ CIDR        │ Resources                     │ │
│  ├──────────────────┼─────────────┼─────────────┼────────────────────────────────┤ │
│  │ private-app-1a  │ us-east-1a │ 10.0.101.0/24 │ EKS Nodes (API)           │ │
│  │ private-app-1b  │ us-east-1b │ 10.0.102.0/24 │ EKS Nodes (Trading)        │ │
│  │ private-app-1c  │ us-east-1c │ 10.0.103.0/24 │ EKS Nodes (Backtest)       │ │
│  └──────────────────┴─────────────┴─────────────┴────────────────────────────────┘ │
│                                                                                      │
│  PRIVATE DATA SUBNETS - 3 AZs                                                       │
│  ┌──────────────────┬─────────────┬─────────────┬────────────────────────────────┐ │
│  │ Subnet           │ AZ         │ CIDR        │ Resources                     │ │
│  ├──────────────────┼─────────────┼─────────────┼────────────────────────────────┤ │
│  │ private-data-1a │ us-east-1a │ 10.0.201.0/24 │ RDS Primary, ElastiCache   │ │
│  │ private-data-1b │ us-east-1b │ 10.0.202.0/24 │ RDS Replica, ElastiCache   │ │
│  │ private-data-1c │ us-east-1c │ 10.0.203.0/24 │ MSK Kafka                    │ │
│  └──────────────────┴─────────────┴─────────────┴────────────────────────────────┘ │
│                                                                                      │
│  NAT GATEWAY: One per AZ for high availability                                      │
│  EGRESS ONLY INTERNET GATEWAY: For S3, Secrets Manager access                       │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### 2.3 Load Balancers

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           LOAD BALANCERS                                             │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  ┌──────────────────────────────────────────────────────────────────────────────┐   │
│  │  APPLICATION LOAD BALANCER (ALB) - Public                                    │   │
│  │  ┌────────────────────────────────────────────────────────────────────────┐  │   │
│  │  │ Listener: HTTPS (:443) → WAF                                          │  │   │
│  │  │                                                                       │  │   │
│  │  │ Target Groups:                                                        │  │   │
│  │  │  ├── api.easytradingapp.com → K8s Ingress (Kong)                    │  │   │
│  │  │  ├── ws.easytradingapp.com → K8s WSS Service                         │  │   │
│  │  │  ├── admin.easytradingapp.com → K8s Admin Service                   │  │   │
│  │  │  └── docs.easytradingapp.com → S3 Static Website                     │  │   │
│  │  └────────────────────────────────────────────────────────────────────────┘  │   │
│  │  Configuration:                                                              │   │
│  │  - SSL/TLS: AWS Certificate Manager (ACM)                                  │   │
│  │  - Health Checks: /health on all services                                  │   │
│  │  - Cross-zone: Enabled                                                     │   │
│  │  - Deletion Protection: Enabled                                            │   │
│  └──────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                      │
│  ┌──────────────────────────────────────────────────────────────────────────────┐   │
│  │  NETWORK LOAD BALANCER (NLB) - Internal                                     │   │
│  │  ┌────────────────────────────────────────────────────────────────────────┐  │   │
│  │  │ Purpose: gRPC traffic between services                                │  │   │
│  │  │                                                                       │  │   │
│  │  │ Target Groups:                                                         │  │   │
│  │  │  ├── grpc-auth → Auth Service                                          │  │   │
│  │  │  ├── grpc-order → Order Service                                       │  │   │
│  │  │  ├── grpc-broker → Broker Service                                     │  │   │
│  │  │  └── grpc-quant → Quant Engine                                         │  │   │
│  │  └────────────────────────────────────────────────────────────────────────┘  │   │
│  │  Configuration:                                                              │   │
│  │  - Protocol: TLS (gRPC)                                                   │   │
│  │  - Cross-zone: Enabled                                                     │   │
│  │  - Preserve client IP: Enabled                                             │   │
│  └──────────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Compute Architecture (EKS)

### 3.1 EKS Cluster Configuration

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              EKS CLUSTER                                             │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  CLUSTER SPECIFICATION                                                               │
│  ├── Name: easytradingapp-prod                                                      │
│  ├── Version: 1.29                                                                  │
│  ├── Kubernetes: EKS Managed                                                        │
│  ├── VPC: 10.0.0.0/16                                                              │
│  ├── Runtime: Docker, containerd                                                   │
│  ├── CNI: AWS VPC CNI                                                              │
│  ├── CoreDNS: Managed by EKS                                                        │
│  └── Add-ons: ALB Ingress, EBS CSI, External DNS                                   │
│                                                                                      │
│  IAM OIDC PROVIDER                                                                  │
│  ├── Service Account: AWS IRSA (IAM Roles for Service Accounts)                    │
│  ├── Tokens: Web Identity Token Federation                                         │
│  └── Audit: CloudTrail logging enabled                                             │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Node Group Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           NODE GROUPS                                                │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐ │
│  │  SYSTEM NODE GROUP (Always-On)                                               │ │
│  │  ┌────────────────────────────────────────────────────────────────────────┐  │ │
│  │  │ Instance Type: t3.xlarge                                                │  │ │
│  │  │ vCPUs: 4 | Memory: 16GB | Storage: 100GB (gp3)                        │  │ │
│  │  │ Nodes: 3 (1 per AZ)                                                   │  │ │
│  │  │ Min: 3 | Max: 3                                                       │  │ │
│  │  │ Purpose: kube-system, monitoring, logging                            │  │ │
│  │  │ Labels: node.kubernetes.io/role: system                              │  │ │
│  │  └────────────────────────────────────────────────────────────────────────┘  │ │
│  └─────────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐ │
│  │  API NODE GROUP (Scalable)                                                   │ │
│  │  ┌────────────────────────────────────────────────────────────────────────┐  │ │
│  │  │ Instance Type: c5.2xlarge                                              │  │ │
│  │  │ vCPUs: 8 | Memory: 16GB | Storage: 100GB (gp3)                       │  │ │
│  │  │ Nodes: 10 (base)                                                     │  │ │
│  │  │ Min: 5 | Max: 20                                                     │  │ │
│  │  │ Purpose: REST APIs, Auth, User, Strategy, Order, Analytics           │  │ │
│  │  │ Labels: workload: api                                                │  │ │
│  │  │ Scaling: CPU > 70% → scale up                                        │  │ │
│  │  └────────────────────────────────────────────────────────────────────────┘  │ │
│  └─────────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐ │
│  │  TRADING NODE GROUP (Performance Critical)                                    │ │
│  │  ┌────────────────────────────────────────────────────────────────────────┐  │ │
│  │  │ Instance Type: c5.4xlarge                                              │  │ │
│  │  │ vCPUs: 16 | Memory: 32GB | Storage: 200GB (gp3)                       │  │ │
│  │  │ Nodes: 15 (base)                                                     │  │ │
│  │  │ Min: 10 | Max: 30                                                    │  │ │
│  │  │ Purpose: Quant Engine, Broker Service, Real-time Trading           │  │ │
│  │  │ Labels: workload: trading                                           │  │ │
│  │  │ Features: ENI trunking, placement groups                             │  │ │
│  │  │ Scaling: Kafka queue depth > 100 → scale up                          │  │ │
│  │  └────────────────────────────────────────────────────────────────────────┘  │ │
│  └─────────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐ │
│  │  BACKTEST NODE GROUP (GPU-Enabled, On-Demand)                                │ │
│  │  ┌────────────────────────────────────────────────────────────────────────┐  │ │
│  │  │ Instance Type: r5.4xlarge + g4dn.xlarge (GPU)                       │  │ │
│  │  │ vCPUs: 16 | Memory: 128GB | Storage: 500GB (gp3)                     │  │ │
│  │  │ Nodes: 0 (spot) | 8 (on-demand)                                      │  │ │
│  │  │ Min: 0 | Max: 20                                                     │  │ │
│  │  │ Purpose: Backtesting Engine, ML Models                             │  │ │
│  │  │ Labels: workload: backtest                                           │  │ │
│  │  │ Capacity: SPOT (90% savings) + On-Demand (guaranteed)              │  │ │
│  │  │ Scaling: Queue depth > 5 → scale up                                 │  │ │
│  │  └────────────────────────────────────────────────────────────────────────┘  │ │
│  └─────────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐ │
│  │  WEBSOCKET NODE GROUP (Low Latency)                                          │ │
│  │  ┌────────────────────────────────────────────────────────────────────────┐  │ │
│  │  │ Instance Type: c5.4xlarge                                              │  │ │
│  │  │ vCPUs: 16 | Memory: 32GB | Storage: 100GB (gp3)                     │  │ │
│  │  │ Nodes: 5 (base)                                                      │  │ │
│  │  │ Min: 3 | Max: 15                                                     │  │ │
│  │  │ Purpose: WebSocket connections, real-time data                      │  │ │
│  │  │ Labels: workload: websocket                                          │  │ │
│  │  │ Features: Placement group (cluster)                                  │  │ │
│  │  └────────────────────────────────────────────────────────────────────────┘  │ │
│  └─────────────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### 3.3 Kubernetes Resources

```yaml
# Example: Quant Engine Deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: quant-engine
  namespace: trading
spec:
  replicas: 10
  selector:
    matchLabels:
      app: quant-engine
  template:
    metadata:
      labels:
        app: quant-engine
        workload: trading
    spec:
      nodeSelector:
        workload: trading
      topologySpreadConstraints:
        - maxSkew: 1
          topologyKey: topology.kubernetes.io/zone
          whenUnsatisfiable: DoNotSchedule
          labelSelector:
            matchLabels:
              app: quant-engine
      containers:
        - name: quant-engine
          image: easytradingapp/quant-engine:v1.0.0
          resources:
            requests:
              cpu: "4"
              memory: "16Gi"
            limits:
              cpu: "8"
              memory: "32Gi"
          env:
            - name: KAFKA_BROKERS
              valueFrom:
                configMapKeyRef:
                  name: kafka-config
                  key: brokers
          volumeMounts:
            - name: strategy-cache
              mountPath: /tmp
      volumes:
        - name: strategy-cache
          emptyDir:
            medium: Memory
            sizeLimit: 2Gi
```

---

## 4. Database Architecture

### 4.1 PostgreSQL (RDS)

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                         RDS POSTGRESQL CLUSTER                                      │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  PRIMARY INSTANCE                                                                   │
│  ┌──────────────────────────────────────────────────────────────────────────────┐   │
│  │ Instance: db.r5.4xlarge                                                    │   │
│  │ vCPUs: 16 | Memory: 128GB | Storage: 2TB (gp3)                           │   │
│  │ Multi-AZ: Yes (us-east-1a primary)                                        │   │
│  │ Storage: 3000 IOPS, 125 MB/s throughput                                   │   │
│  │ Encryption: AES-256 (KMS)                                                 │   │
│  │ Performance Insights: Enabled                                              │   │
│  │ Enhanced Monitoring: 1-minute granularity                                 │   │
│  └──────────────────────────────────────────────────────────────────────────────┘   │
│                                           │                                         │
│                    ┌──────────────────────┼──────────────────────┐                │
│                    │                      │                      │                │
│                    ▼                      ▼                      ▼                │
│  READ REPLICA 1               READ REPLICA 2               READ REPLICA 3          │
│  ┌─────────────┐            ┌─────────────┐            ┌─────────────┐            │
│  │ us-east-1b │            │ us-east-1c │            │ us-west-2  │ (DR)       │
│  │ db.r5.2xl  │            │ db.r5.2xl  │            │ db.r5.2xl  │            │
│  │ 8 vCPU     │            │ 8 vCPU     │            │ 8 vCPU     │            │
│  │ 64GB RAM   │            │ 64GB RAM   │            │ 64GB RAM   │            │
│  └─────────────┘            └─────────────┘            └─────────────┘            │
│                                                                                      │
│  BACKUP & RECOVERY                                                                  │
│  ├── Automated Backups: Daily (retention 30 days)                                 │
│  ├── Point-in-Time Recovery: Enabled (retention 7 days)                           │
│  ├── S3 Automated Backup: Cross-region (us-west-2)                                 │
│  └── Failover: Automatic (< 60 seconds)                                           │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### 4.2 PostgreSQL Tablespaces

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           DATABASE TABLESPACES                                       │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐ │
│  │ users_ts (User Data)                                                          │ │
│  │ ├── users                                                                      │ │
│  │ ├── sessions                                                                   │ │
│  │ ├── broker_configs (encrypted API keys)                                       │ │
│  │ └── audit_logs                                                                 │ │
│  │ Partitioning: By user_id                                                      │ │
│  │ Index: email, created_at                                                      │ │
│  └─────────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐ │
│  │ trading_ts (Trading Data)                                                     │ │
│  │ ├── strategies                                                                 │ │
│  │ ├── orders (partitioned by created_at, monthly)                               │ │
│  │ ├── positions                                                                  │ │
│  │ └── risk_limits                                                                │ │
│  │ Index: user_id, strategy_id, created_at                                      │ │
│  └─────────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐ │
│  │ analytics_ts (Historical Data)                                                │ │
│  │ ├── trade_history (partitioned by date)                                       │ │
│  │ ├── backtest_results                                                          │ │
│  │ ├── performance_metrics                                                       │ │
│  │ └── daily_summaries                                                            │ │
│  │ Index: user_id, date, strategy_id                                            │ │
│  └─────────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐ │
│  │ market_data_ts (Time-Series)                                                  │ │
│  │ ├── ohlcv_1m (partitioned by symbol, monthly)                                │ │
│  │ ├── ohlcv_1h                                                                   │ │
│  │ ├── symbols                                                                    │ │
│  │ └── market_hours                                                              │ │
│  │ Index: symbol, timestamp                                                      │ │
│  │ Compression: TimescaleDB                                                       │ │
│  └─────────────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### 4.3 ElastiCache (Redis)

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                         ELASTICACHE REDIS CLUSTER                                    │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  CLUSTER CONFIGURATION                                                               │
│  ├── Type: Redis (Cluster Mode Enabled)                                            │
│  ├── Version: 7.0                                                                   │
│  ├── Shards: 6 (3 primary + 3 replica)                                            │
│  ├── Replicas per Shard: 2                                                         │
│  ├── Node Type: cache.r5.4xlarge                                                  │
│  │   vCPUs: 16 | Memory: 125GB                                                    │
│  ├── Total Memory: 750GB                                                           │
│  ├── Data Persistence: AOF + RDB                                                  │
│  └── Encryption: At-rest (KMS) + In-transit (TLS)                                 │
│                                                                                      │
│  CACHE STRATEGY                                                                    │
│  ┌──────────────────────────────────────────────────────────────────────────────┐  │
│  │ Cache Name          │ Data                    │ TTL        │ Eviction      │  │
│  ├────────────────────┼─────────────────────────┼────────────┼───────────────┤  │
│  │ session            │ User sessions           │ 30 min     │ LRU           │  │
│  │ strategy           │ Strategy configs        │ 5 min      │ LRU           │  │
│  │ market:price       │ Real-time prices        │ 1 sec      │ Time-based    │  │
│  │ market:orderbook   │ Order books             │ 100 ms     │ Time-based    │  │
│  │ indicator          │ Indicator values        │ 1 sec      │ Time-based    │  │
│  │ position           │ Current positions       │ 500 ms     │ LRU           │  │
│  │ orderbook:snapshot │ Aggregated data         │ 1 sec      │ Time-based    │  │
│  └────────────────────┴─────────────────────────┴────────────┴───────────────┘  │
│                                                                                      │
│  HIGH AVAILABILITY                                                                   │
│  ├── Multi-AZ: Yes (3 AZs)                                                          │
│  ├── Auto-Failover: < 30 seconds                                                    │
│  ├── Reader Endpoint: Load-balanced reads                                          │
│  └── Global Datastore: us-east-1 → us-west-2 (DR)                                 │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Message Queue (MSK Kafka)

### 5.1 Kafka Cluster

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                            MSK KAFKA CLUSTER                                         │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  CLUSTER SPECIFICATION                                                              │
│  ├── Broker Nodes: 6 (msk.t3.small) × 3 AZs                                        │
│  ├── Storage per Broker: 1TB (gp3)                                                 │
│  ├── Apache Kafka Version: 3.6                                                     │
│  ├── Encryption: TLS in-flight                                                     │
│  ├── Authentication: SASL/SCRAM                                                   │
│  └── Auto Create Topics: Disabled                                                  │
│                                                                                      │
│  TOPIC CONFIGURATION                                                                 │
│  ┌───────────────────────────────────────────────────────────────────────────────┐ │
│  │ Topic              │ Partitions │ Replication │ Retention    │ Use Case     │ │
│  ├───────────────────┼─────────────┼─────────────┼──────────────┼──────────────┤ │
│  │ trade-signals     │ 50          │ 3           │ 7 days       │ Strategy →  │ │
│  │                   │             │             │              │ Order       │ │
│  │ orders.created    │ 100         │ 3           │ 30 days      │ Order →     │ │
│  │                   │             │             │              │ Broker      │ │
│  │ orders.updated    │ 100         │ 3           │ 30 days      │ Broker →    │ │
│  │                   │             │             │              │ Position    │ │
│  │ positions.updated │ 50          │ 3           │ 30 days      │ Position →  │ │
│  │                   │             │             │              │ Analytics   │ │
│  │ risk.alerts       │ 20          │ 3           │ 90 days      │ Risk →      │ │
│  │                   │             │             │              │ Notification│ │
│  │ market-data       │ 100         │ 3           │ 1 day        │ Market Data │ │
│  │                   │             │             │              │ Stream      │ │
│  │ backtest.jobs     │ 30          │ 3           │ 7 days       │ Analytics → │ │
│  │                   │             │             │              │ Backtest    │ │
│  │ notifications     │ 10          │ 3           │ 7 days       │ All →       │ │
│  │                   │             │             │              │ Notif       │ │
│  └───────────────────┴─────────────┴─────────────┴──────────────┴──────────────┘ │
│                                                                                      │
│  CONNECT                                                                             │
│  ├── Kafka Connect: Debezium CDC for PostgreSQL                                    │
│  ├── Schema Registry: Confluent (AVRO schemas)                                    │
│  └── MirrorMaker: Cross-region replication (DR)                                    │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 6. Storage Architecture

### 6.1 S3 Buckets

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              S3 STORAGE                                              │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────┐    │
│  │ easytradingapp-prod-assets                                                   │    │
│  │ ├── Frontend/ (React build files)                                           │    │
│  │ │   - Static website hosting                                               │    │
│  │ │   - CloudFront distribution                                              │    │
│  │ │   - Gzip/Brotli compression                                              │    │
│  │ │   - Cache: /static/* (1 year)                                           │    │
│  │ │                                                                         │    │
│  │ └── Exports/ (User exports)                                                │    │
│  │     - Backtest reports (PDF, CSV)                                         │    │
│  │     - Analytics reports                                                    │    │
│  │     - Lifecycle: Delete after 30 days                                      │    │
│  │                                                                         │    │
│  │ Configuration:                                                             │    │
│  │ - Versioning: Enabled                                                      │    │
│  │ - Encryption: AES-256                                                      │    │
│  │ - Block Public Access: Enabled                                            │    │
│  │ - Lifecycle Policies: Enabled                                             │    │
│  └─────────────────────────────────────────────────────────────────────────────┘    │
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────┐    │
│  │ easytradingapp-prod-market-data                                             │    │
│  │ ├── Intraday/ (1-minute OHLCV)                                             │    │
│  │ │   - Partitioned: symbol/year/month/day/                                  │    │
│  │ │   - Format: Parquet (Athena)                                            │    │
│  │ │   - Lifecycle: Standard → IA after 90 days → Glacier after 1 year       │    │
│  │ │                                                                         │    │
│  │ └── Daily/ (Daily OHLCV)                                                   │    │
│  │     - Retention: 10 years                                                  │    │
│  │                                                                         │    │
│  │ Configuration:                                                             │    │
│  │ - Versioning: Enabled                                                      │    │
│  │ - Encryption: AWS KMS (aws/s3)                                            │    │
│  │ - Intelligent Tiering: Enabled                                            │    │
│  └─────────────────────────────────────────────────────────────────────────────┘    │
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────┐    │
│  │ easytradingapp-prod-backups                                                 │    │
│  │ ├── Database/ (RDS automated backups)                                      │    │
│  │ │   - Cross-region replication: us-west-2                                 │    │
│  │ │   - Retention: 30 days                                                  │    │
│  │ │                                                                         │    │
│  │ └── Logs/ (Application logs)                                               │    │
│  │     - S3 Select enabled                                                   │    │
│  │     - Lifecycle: Glacier after 90 days                                    │    │
│  │                                                                         │    │
│  │ Configuration:                                                             │    │
│  │ - Versioning: Enabled                                                      │    │
│  │ - Replication: Cross-region (CRR)                                         │    │
│  │ - Lock: Object Lock (WORM, 30 days)                                       │    │
│  └─────────────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 7. Security Architecture

### 7.1 IAM Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              IAM SECURITY                                            │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  IAM ROLES (EKS Service Accounts)                                                   │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                                                                              │   │
│  │  auth-service                                                                │   │
│  │  ├── Policy: secretsmanager:GetSecretValue                                  │   │
│  │  │         (auth-credentials)                                                │   │
│  │  └── Trust: EKS namespace trading                                           │   │
│  │                                                                              │   │
│  │  broker-service                                                              │   │
│  │  ├── Policy: secretsmanager:GetSecretValue                                  │   │
│  │  │         (broker-api-keys)                                                │   │
│  │  │         sqs:SendMessage (broker-orders-queue)                           │   │
│  │  └── Trust: EKS namespace trading                                           │   │
│  │                                                                              │   │
│  │  quant-engine                                                                │   │
│  │  ├── Policy: dynamodb:GetItem,PutItem (strategy-cache)                     │   │
│  │  │         kinesis:PutRecord (signals-stream)                               │   │
│  │  └── Trust: EKS namespace trading                                           │   │
│  │                                                                              │   │
│  │  analytics-service                                                          │   │
│  │  ├── Policy: s3:PutObject (reports-bucket)                                 │   │
│  │  │         athena:StartQueryExecution                                       │   │
│  │  └── Trust: EKS namespace trading                                           │   │
│  │                                                                              │   │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                      │
│  USER ACCESS (Cognito)                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │  User Pool: easytradingapp-users                                             │   │
│  │  ├── Sign-in: Email + Password                                              │   │
│  │  ├── MFA: TOTP (optional)                                                   │   │
│  │  ├── Password Policy: 8+ chars, uppercase, lowercase, number              │   │
│  │  └── Attribute: email, sub (UUID), custom:role                            │   │
│  │                                                                              │   │
│  │  Identity Pool: easytradingapp-identity                                     │   │
│  │  ├── Authenticated: JWT → IAM Role                                          │   │
│  │  └── Unauthenticated: Not allowed                                           │   │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### 7.2 Secrets Management

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                         SECRETS MANAGER                                              │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │  DATABASE_SECRETS                                                            │   │
│  │  ├── Key: easytradingapp-prod/db-credentials                               │   │
│  │  ├── Value: {"username": "app_user", "password": "***"}                   │   │
│  │  └── Rotation: 30 days (Lambda)                                            │   │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │  BROKER_API_KEYS                                                            │   │
│  │  ├── Key: easytradingapp-prod/broker-keys/{user_id}/{broker}               │   │
│  │  ├── Value: {"api_key": "enc(***)", "api_secret": "enc(***)",             │   │
│  │  │           "encryption_key_id": "alias/aws/secretsmanager"}              │   │
│  │  ├── Encryption: AWS KMS (customer managed key)                           │   │
│  │  └── Access: Per-user (via IAM policy condition)                           │   │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │  JWT_SECRETS                                                                 │   │
│  │  ├── Key: easytradingapp-prod/jwt-secret                                    │   │
│  │  ├── Value: {"access_token_secret": "***", "refresh_token_secret": "***"}│   │
│  │  └── Rotation: 90 days                                                      │   │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │  EXTERNAL_APIS                                                               │   │
│  │  ├── Polygon.io API Key                                                     │   │
│  │  ├── SendGrid API Key                                                       │   │
│  │  ├── Twilio API Key                                                         │   │
│  │  └── PagerDuty API Key                                                      │   │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                      │
│  ENCRYPTION KEYS (KMS)                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │  easytradingapp-prod-key (Symmetric)                                        │   │
│  │  ├── Key Usage: ENCRYPT_DECRYPT                                             │   │
│  │  ├── Rotation: Yearly                                                        │   │
│  │  └── Alias: alias/easytradingapp-prod                                       │   │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 8. Monitoring & Observability

### 8.1 CloudWatch Integration

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           MONITORING STACK                                           │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │  CLOUDWATCH METRICS                                                         │   │
│  │  ┌─────────────────────────────────────────────────────────────────────┐  │   │
│  │  │  Namespace: EasyTradingApp/Trading                                   │  │   │
│  │  │  ├── OrdersSubmitted (Count)                                        │  │   │
│  │  │  ├── OrdersFilled (Count)                                           │  │   │
│  │  │  ├── OrderLatency (Milliseconds)                                    │  │   │
│  │  │  ├── StrategySignals (Count)                                        │  │   │
│  │  │  ├── RiskBreaches (Count)                                            │  │   │
│  │  │  ├── ActivePositions (Gauge)                                         │  │   │
│  │  │  ├── DailyPnL (Dollars)                                             │  │   │
│  │  │  └── BacktestDuration (Seconds)                                     │  │   │
│  │  └─────────────────────────────────────────────────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │  CLOUDWATCH LOGS                                                            │   │
│  │  ┌─────────────────────────────────────────────────────────────────────┐  │   │
│  │  │  Log Groups:                                                        │  │   │
│  │  │  ├── /aws/eks/easytradingapp-prod/cluster (Audit)                   │  │   │
│  │  │  ├── /easytradingapp/auth (Structured JSON)                         │  │   │
│  │  │  ├── /easytradingapp/trading (Structured JSON)                     │  │   │
│  │  │  ├── /easytradingapp/orders (Structured JSON)                      │  │   │
│  │  │  └── /easytradingapp/analytics (Structured JSON)                   │  │   │
│  │  │                                                                    │  │   │
│  │  │  Retention: 30 days (trading), 90 days (audit)                    │  │   │
│  │  │  Encryption: KMS (customer managed)                                 │  │   │
│  │  └─────────────────────────────────────────────────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │  X-RAY DISTRIBUTED TRACING                                                 │   │
│  │  ┌─────────────────────────────────────────────────────────────────────┐  │   │
│  │  │  Sampling: 10% (adjustable)                                        │  │   │
│  │  │  Annotations: user_id, strategy_id, order_id                       │  │   │
│  │  │  Error Segmentation: Captured                                       │  │   │
│  │  └─────────────────────────────────────────────────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### 8.2 Alerting Rules

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              ALERTING RULES                                         │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  CRITICAL ALERMS (PagerDuty)                                                         │
│  ┌───────────────────────────────────────────────────────────────────────────────┐ │
│  │ Alert Name                    │ Condition              │ Action              │ │
│  ├────────────────────────────────┼───────────────────────┼─────────────────────┤ │
│  │ HighErrorRate                 │ ErrorRate > 5%         │ Page on-call       │ │
│  │ DatabaseFailover              │ Primary → Replica     │ Page on-call       │ │
│  │ KafkaBrokerDown               │ Broker count < 5      │ Page on-call       │ │
│  │ DailyLossLimitBreached        │ PnL < -$X             │ Page on-call       │ │
│  │ UnusualTradingVolume          │ Volume > 10x normal   │ Page on-call       │ │
│  │ CriticalServiceDown           │ Pod crashloop        │ Page on-call       │ │
│  └────────────────────────────────┴───────────────────────┴─────────────────────┘ │
│                                                                                      │
│  WARNING ALERMS (Slack + Email)                                                      │
│  ┌───────────────────────────────────────────────────────────────────────────────┐ │
│  │ Alert Name                    │ Condition              │ Action              │ │
│  ├────────────────────────────────┼───────────────────────┼─────────────────────┤ │
│  │ HighLatency                   │ P99 > 2s               │ Slack channel      │ │
│  │ HighCPU                       │ CPU > 80%              │ Slack channel      │ │
│  │ DiskPressure                 │ Disk > 85%             │ Slack channel      │ │
│  │ PodRestart                    │ Restarts > 3/hr       │ Slack channel      │ │
│  │ RiskLimitWarning             │ PnL < -80% of limit   │ Email + Slack      │ │
│  │ BacklogGrowing               │ Queue depth > 500     │ Slack channel      │ │
│  └────────────────────────────────┴───────────────────────┴─────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 9. Disaster Recovery

### 9.1 DR Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                         DISASTER RECOVERY ARCHITECTURE                               │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  RPO & RTO TARGETS                                                                   │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │ Component           │ RPO           │ RTO        │ Strategy                  │   │
│  ├─────────────────────┼────────────────┼────────────┼──────────────────────────┤   │
│  │ Database            │ 1 minute       │ 5 minutes  │ Multi-AZ + PITR          │   │
│  │ Cache               │ 0 seconds     │ 1 minute   │ Multi-AZ cluster          │   │
│  │ Kafka               │ 1 minute      │ 10 minutes │ MirrorMaker               │   │
│  │ Application         │ 0             │ 3 minutes  │ Blue-green deployment    │   │
│  │ S3                  │ 0             │ 1 minute   │ Cross-region replication  │   │
│  │ Secrets             │ 0             │ 0          │ Multi-region              │   │
│  └─────────────────────┴────────────────┴────────────┴──────────────────────────┘   │
│                                                                                      │
│  REGIONAL FAILOVER FLOW                                                              │
│                                                                                      │
│  us-east-1 (Primary)                                                          │
│       │                                                                           │
│       │ Auto-failover (for RDS, ElastiCache)                                       │
│       │ Cross-region replication (S3, Kafka)                                       │
│       │                                                                           │
│       ▼                                                                           │
│  ┌───────────────────────────────────────────────────────────────────────────┐    │
│  │                        FAILOVER DETECTION                                  │    │
│  │  - Route 53 health checks (30-second intervals)                          │    │
│  │  - CloudWatch composite alarms                                             │    │
│  │  - Automatic DNS failover                                                   │    │
│  └───────────────────────────────────────────────────────────────────────────┘    │
│       │                                                                           │
│       ▼                                                                           │
│  us-west-2 (DR)                                                                   │
│       │                                                                           │
│       │ 1. Promote RDS read replica to primary                                  │
│       │ 2. Scale EKS nodes to capacity                                          │
│       │ 3. Update Route 53 alias records                                      │
│       │ 4. Resume Kafka consumer groups                                         │
│       │                                                                           │
│       ▼                                                                           │
│  Recovery Complete (< 15 minutes for full stack)                                  │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 10. Cost Estimation

### 10.1 Monthly Cost Breakdown

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                         MONTHLY COST ESTIMATION                                     │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  COMPUTE (EKS + EC2)                                                                │
│  ┌───────────────────────────────────────────────────────────────────────────────┐   │
│  │ Resource                    │ Quantity │ Unit Price │ Monthly             │   │
│  ├─────────────────────────────┼──────────┼────────────┼─────────────────────┤   │
│  │ EKS Cluster                 │ 1        │ $730       │ $730                │   │
│  │ System Nodes (t3.xlarge)   │ 3        │ $307       │ $921                │   │
│  │ API Nodes (c5.2xlarge)     │ 10       │ $612       │ $6,120              │   │
│  │ Trading Nodes (c5.4xlarge)│ 15       │ $1,224     │ $18,360             │   │
│  │ Backtest On-Demand         │ 8        │ $1,836     │ $14,688             │   │
│  │ Backtest Spot (8x)         │ 8        │ $550       │ $4,400              │   │
│  │ WebSocket Nodes (c5.4xlarge│ 5        │ $612       │ $3,060              │   │
│  │ EBS Storage                 │ 50TB     │ $125       │ $6,250              │   │
│  │ NAT Gateway                 │ 3        │ $90        │ $270                │   │
│  └─────────────────────────────┴──────────┴────────────┴─────────────────────┘   │
│  Compute Subtotal: $50,799                                                          │
│                                                                                      │
│  DATABASE                                                                           │
│  ┌───────────────────────────────────────────────────────────────────────────────┐   │
│  │ Resource                    │ Quantity │ Unit Price │ Monthly             │   │
│  ├─────────────────────────────┼──────────┼────────────┼─────────────────────┤   │
│  │ RDS Primary (r5.4xlarge)   │ 1        │ $1,200     │ $1,200              │   │
│  │ RDS Replicas (r5.2xlarge)  │ 3        │ $610       │ $1,830              │   │
│  │ RDS Storage (2TB gp3)      │ 2TB      │ $250       │ $500                │   │
│  │ ElastiCache (r5.4xlarge x 6)│ 6        │ $510       │ $3,060              │   │
│  └─────────────────────────────┴──────────┴────────────┴─────────────────────┘   │
│  Database Subtotal: $6,590                                                          │
│                                                                                      │
│  MESSAGING                                                                           │
│  ┌───────────────────────────────────────────────────────────────────────────────┐   │
│  │ Resource                    │ Quantity │ Unit Price │ Monthly             │   │
│  ├─────────────────────────────┼──────────┼────────────┼─────────────────────┤   │
│  │ MSK Broker (t3.small)      │ 6        │ $150       │ $900                │   │
│  │ MSK Storage (6TB)          │ 6TB      │ $180       │ $1,080              │   │
│  └─────────────────────────────┴──────────┴────────────┴─────────────────────┘   │
│  Messaging Subtotal: $1,980                                                         │
│                                                                                      │
│  NETWORKING                                                                         │
│  ┌───────────────────────────────────────────────────────────────────────────────┐   │
│  │ Resource                    │ Quantity │ Unit Price │ Monthly             │   │
│  ├─────────────────────────────┼──────────┼────────────┼─────────────────────┤   │
│  │ ALB (Application)           │ 3        │ $50        │ $150                │   │
│  │ NLB (Network)               │ 1        │ $60        │ $60                 │   │
│  │ CloudFront (100GB)         │ 100GB    │ $85        │ $85                 │   │
│  │ Route 53 (1M queries)      │ 1M       │ $40        │ $40                 │   │
│  │ Data Transfer (est.)       │ 10TB     │ $90        │ $90                 │   │
│  └─────────────────────────────┴──────────┴────────────┴─────────────────────┘   │
│  Networking Subtotal: $425                                                          │
│                                                                                      │
│  STORAGE                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────────────┐   │
│  │ Resource                    │ Quantity │ Unit Price │ Monthly             │   │
│  ├─────────────────────────────┼──────────┼────────────┼─────────────────────┤   │
│  │ S3 (Standard)               │ 10TB     │ $23        │ $230                │   │
│  │ S3 (IA)                     │ 50TB     │ $12.50     │ $625                │   │
│  │ S3 (Glacier)                │ 100TB    │ $4         │ $400                │   │
│  │ S3 (Data Transfer out)      │ 10TB     │ $90        │ $900                │   │
│  └─────────────────────────────┴──────────┴────────────┴─────────────────────┘   │
│  Storage Subtotal: $2,155                                                           │
│                                                                                      │
│  SECURITY & COMPLIANCE                                                               │
│  ┌───────────────────────────────────────────────────────────────────────────────┐   │
│  │ Resource                    │ Quantity │ Unit Price │ Monthly             │   │
│  ├─────────────────────────────┼──────────┼────────────┼─────────────────────┤   │
│  │ WAF (Basic)                 │ 1        │ $60        │ $60                 │   │
│  │ Shield Standard             │ 1        │ $3,000     │ $3,000              │   │
│  │ Secrets Manager             │ 50       │ $2         │ $100                │   │
│  │ CloudHSM (optional)         │ 1        │ $1,500     │ $1,500              │   │
│  └─────────────────────────────┴──────────┴────────────┴─────────────────────┘   │
│  Security Subtotal: $4,660                                                          │
│                                                                                      │
│  MONITORING                                                                          │
│  ┌───────────────────────────────────────────────────────────────────────────────┐   │
│  │ Resource                    │ Quantity │ Unit Price │ Monthly             │   │
│  ├─────────────────────────────┼──────────┼────────────┼─────────────────────┤   │
│  │ CloudWatch (metrics + logs) │ ~50GB    │ $3/GB      │ $150                │   │
│  │ DataDog (APM + Logs)        │ 50 hosts │ $23/host   │ $1,150              │   │
│  │ PagerDuty                   │ 1        │ $75        │ $75                 │   │
│  └─────────────────────────────┴──────────┴────────────┴─────────────────────┘   │
│  Monitoring Subtotal: $1,375                                                         │
│                                                                                      │
│  ┌───────────────────────────────────────────────────────────────────────────────┐   │
│  │                                    TOTAL MONTHLY COST                         │   │
│  │  Compute:         $50,799                                                    │   │
│  │  Database:        $6,590                                                     │   │
│  │  Messaging:       $1,980                                                     │   │
│  │  Networking:      $425                                                       │   │
│  │  Storage:         $2,155                                                     │   │
│  │  Security:        $4,660                                                     │   │
│  │  Monitoring:      $1,375                                                    │   │
│  │  ────────────────────────────────────────────────────────                   │   │
│  │  TOTAL:           $67,984 / month                                            │   │
│  └───────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                      │
│  OPTIMIZATION NOTES                                                                  │
│  ├── Use SPOT instances for backtest nodes (90% savings)                         │
│  ├── Right-size RDS based on actual usage                                         │
│  ├── Enable S3 Intelligent-Tiering                                                 │
│  ├── Use CloudFront for all static content                                         │
│  └── Reserved Instances for always-on workloads (30% savings)                     │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 11. Deployment Pipeline

### 11.1 CI/CD Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           CI/CD PIPELINE (GitHub Actions)                            │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  ┌───────────────────────────────────────────────────────────────────────────────┐  │
│  │  GitHub Repository: easytradingapp/easytradingapp                           │  │
│  │                                                                               │  │
│  │  Branch Strategy:                                                            │  │
│  │  ├── main ──▶ Production (protected, requires approval)                     │  │
│  │  ├── staging ──▶ Staging (auto-deploy)                                     │  │
│  │  └── feature/* ──▶ Preview environments                                     │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                      │
│  BUILD STAGE                                                                        │
│  ┌───────────────────────────────────────────────────────────────────────────────┐  │
│  │  1. Checkout code                                                            │  │
│  │  2. Install dependencies (npm, pip)                                        │  │
│  │  3. Lint (ESLint, Ruff)                                                      │  │
│  │  4. Type check (TypeScript, mypy)                                           │  │
│  │  5. Unit tests (Jest, pytest)                                               │  │
│  │  6. Build (React, Python)                                                   │  │
│  │  7. Build Docker images                                                     │  │
│  │  8. Scan images (Trivy)                                                     │  │
│  │  9. Push to ECR                                                             │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                      │
│  TEST STAGE                                                                         │
│  ┌───────────────────────────────────────────────────────────────────────────────┐  │
│  │  1. Integration tests (FastAPI + React)                                    │  │
│  │  2. Contract tests (Pact)                                                   │  │
│  │  3. Load tests (k6)                                                         │  │
│  │  4. Security scans (OWASP ZAP)                                              │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                      │
│  DEPLOY STAGE                                                                       │
│  ┌───────────────────────────────────────────────────────────────────────────────┐  │
│  │  STAGING (Auto-deploy on merge to staging)                                  │  │
│  │  ├── Update k8s manifests                                                   │  │
│  │  ├── kubectl apply (namespace staging)                                      │  │
│  │  ├── Run smoke tests                                                        │  │
│  │  └── Notify Slack                                                           │  │
│  │                                                                               │  │
│  │  PRODUCTION (Manual approval required)                                      │  │
│  │  ├── Blue-green deployment                                                   │  │
│  │  ├── Deploy to green environment                                            │  │
│  │  ├── Run smoke tests                                                        │  │
│  │  ├── Canary traffic (10%)                                                  │  │
│  │  ├── Promote to blue                                                        │  │
│  │  ├── Update Route 53                                                        │  │
│  │  └── Notify Slack + PagerDuty                                               │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                      │
│  ROLLBACK                                                                           │
│  ┌───────────────────────────────────────────────────────────────────────────────┐  │
│  │  Automatic: If health check fails                                           │  │
│  │  Manual: kubectl rollout undo (GitHub Actions)                             │  │
│  │  Preserves last 10 deployments                                              │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

*Document Version: 1.0*  
*Last Updated: March 7, 2026*  
*Classification: Internal Use Only*
