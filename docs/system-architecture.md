# EasyTradingApp - Technical Architecture Specification

**Version:** 2.0  
**Date:** March 2026  
**Author:** System Architect  
**Target:** 10,000 Concurrent Users

---

## 1. Service Architecture

### 1.1 Service Mesh Overview

```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                                      CLIENT LAYER                                           │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐  │
│  │   Web App       │  │   Mobile Web    │  │   Admin Panel   │  │   Trading Dashboard │  │
│  │   (React)       │  │   (React)       │  │   (React)       │  │   (React)           │  │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘  └──────────┬──────────┘  │
└───────────┼────────────────────┼────────────────────┼───────────────────────┼─────────────┘
            │                    │                    │                       │
            └────────────────────┴────────────────────┴───────────────────────┘
                                           │
                                    ┌──────▼──────┐
                                    │ API Gateway │
                                    │  (Kong)     │
                                    └──────┬──────┘
                                           │
            ┌──────────────────────────────┼──────────────────────────────┐
            │                              │                              │
     ┌──────▼──────┐              ┌───────▼───────┐              ┌───────▼───────┐
     │   Ingress   │              │   WebSocket   │              │    gRPC       │
     │   (REST)    │              │   Gateway     │              │   Gateway     │
     └──────┬──────┘              └───────┬───────┘              └───────┬───────┘
            │                              │                              │
            └──────────────────────────────┼──────────────────────────────┘
                                           │
                        ┌──────────────────┼──────────────────┐
                        │                  │                  │
                 ┌──────▼──────┐    ┌───────▼───────┐   ┌───────▼───────┐
                 │   Auth      │    │   Trading     │   │   Analytics   │
                 │   Service   │    │   Service     │   │   Service     │
                 │   (Python)  │    │   (Python)    │   │   (Python)    │
                 └──────┬──────┘    └───────┬───────┘   └───────┬───────┘
                        │                  │                   │
                        │         ┌────────▼────────┐          │
                        │         │  Order Service │          │
                        │         │   (Python)      │          │
                        │         └────────┬────────┘          │
                        │                  │                   │
                 ┌──────▼──────┐    ┌───────▼───────┐   ┌───────▼───────┐
                 │   User      │    │   Broker      │   │   Strategy    │
                 │   Service   │    │   Service     │   │   Service     │
                 │   (Python)  │    │   (Python)    │   │   (Python)    │
                 └──────┬──────┘    └───────┬───────┘   └───────┬───────┘
                        │                  │                   │
                        │                  │                   │
                 ┌──────▼──────┐    ┌───────▼───────┐   ┌───────▼───────┐
                 │  Notification│    │   Position    │   │   Risk        │
                 │  Service     │    │   Service     │   │   Service     │
                 │   (Python)   │    │   (Python)    │   │   (Python)    │
                 └─────────────┘    └───────────────┘   └───────────────┘
```

### 1.2 Service Catalog

| Service | Technology | Description | Replicas |
|---------|------------|-------------|----------|
| API Gateway | Kong | REST/WSS/gRPC ingress | 3 |
| Auth Service | Python/FastAPI | JWT, OAuth2, 2FA | 5 |
| User Service | Python/FastAPI | Profile, broker config | 4 |
| Strategy Service | Python/FastAPI | CRUD, versioning | 4 |
| Order Service | Python/FastAPI | Order lifecycle | 6 |
| Broker Service | Python/FastAPI | Broker abstraction | 5 |
| Position Service | Python/FastAPI | Position tracking | 4 |
| Risk Service | Python/FastAPI | Risk evaluation | 5 |
| Analytics Service | Python/FastAPI | P&L, reporting | 4 |
| Notification Service | Python/FastAPI | Alerts, email | 3 |
| Quant Engine | Python | Strategy execution | 10 |
| Backtest Engine | Python | Historical testing | 8 |
| Market Data Service | Python | Real-time feeds | 5 |

### 1.3 Service Communication Patterns

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        SYNCHRONOUS COMMUNICATION                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   Client          API Gateway           Service                             │
│     │                  │                    │                                │
│     │─── HTTP/REST ────│──── gRPC ──────────▶│                              │
│     │                  │                    │                                │
│     │◄─── Response ────│◄─── gRPC ──────────│                              │
│     │                  │                    │                                │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                        ASYNCHRONOUS COMMUNICATION                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   Service A        Kafka Topic           Service B                          │
│     │                  │                    │                                │
│     │───── Publish ────▶│                    │                                │
│     │                  │───── Consume ──────▶│                                │
│     │                  │                    │                                │
│     │                  │                    │                                │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.4 Inter-Service Communication

| From Service | To Service | Protocol | Use Case |
|--------------|------------|----------|----------|
| API Gateway | Auth | gRPC | Token validation |
| API Gateway | Any | gRPC | Request routing |
| Strategy | Quant Engine | Kafka | Strategy execution signals |
| Quant Engine | Order | Kafka | Trade signals |
| Order | Broker | gRPC | Order submission |
| Order | Position | Kafka | Position updates |
| Position | Risk | Kafka | Risk checks |
| Risk | Notification | Kafka | Risk alerts |
| Broker | Market Data | WebSocket | Price streams |
| Analytics | Backtest | Kafka | Backtest requests |

---

## 2. Data Flow Architecture

### 2.1 Trade Execution Flow

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                           TRADE EXECUTION PIPELINE                                       │
└─────────────────────────────────────────────────────────────────────────────────────────┘

     ┌──────────────┐
     │ Market Data  │
     │   (WebSocket)│
     └──────┬───────┘
            │
            │ Real-time price stream
            ▼
     ┌──────────────┐
     │ Market Data   │
     │   Service     │
     └──────┬───────┘
            │
            │ Price cache update
            ▼
     ┌──────────────┐
     │   Redis       │◄────── Price cache (1min candles)
     │   Cache       │
     └──────┬───────┘
            │
            │ Price query
            ▼
     ┌──────────────┐
     │ Quant Engine │
     │  (Per User)  │
     └──────┬───────┘
            │
            │ Strategy evaluation (50ms)
            ▼
     ┌──────────────┐
     │  Signal       │──── Strategy signal (BUY/SELL)
     │  Generator    │
     └──────┬───────┘
            │
            │ Signal event
            ▼
     ┌──────────────┐
     │   Risk       │
     │   Service    │
     └──────┬───────┘
            │
            │ Risk validation
            ▼
     ┌──────────────┐
     │   Order      │
     │   Service    │
     └──────┬───────┘
            │
            │ Order request
            ▼
     ┌──────────────┐
     │   Broker     │
     │   Service    │
     └──────┬───────┘
            │
            │ Broker API call
            ▼
     ┌──────────────┐
     │  External    │
     │  Broker      │
     │  (Alpaca, IB)│
     └──────┬───────┘
            │
            │ Order confirmation
            ▼
     ┌──────────────┐
     │   Position   │
     │   Service    │
     └──────┬───────┘
            │
            │ Position update
            ▼
     ┌──────────────┐
     │  Analytics   │
     │   Service    │
     └──────────────┘
```

### 2.2 Kafka Event Topics

| Topic Name | Partitions | Retention | Producers | Consumers |
|------------|------------|-----------|-----------|-----------|
| trade-signals | 50 | 7 days | Quant Engine | Order Service |
| orders.created | 100 | 30 days | Order Service | Broker, Analytics |
| orders.updated | 100 | 30 days | Broker Service | Position, Analytics |
| positions.updated | 50 | 30 days | Position Service | Analytics, Risk |
| risk.alerts | 20 | 90 days | Risk Service | Notification |
| market-data | 100 | 1 day | Market Data | Quant Engine, Backtest |
| backtest.jobs | 30 | 7 days | Analytics | Backtest Engine |
| backtest.results | 30 | 30 days | Backtest Engine | Analytics |
| notifications | 10 | 7 days | All Services | Notification Service |

### 2.3 Data Synchronization

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           DATA SYNCHRONIZATION LAYER                                │
└─────────────────────────────────────────────────────────────────────────────────────┘

   PostgreSQL                    Redis                        Kafka
  ┌──────────┐                ┌──────────┐               ┌──────────┐
  │  Primary │                │  Cache   │               │  Events  │
  │  (Write) │◄───────────────▶│ (Read)   │◄─────────────▶│ (Stream) │
  │          │   Write-through│          │               │          │
  │          │   + Invalidation│          │               │          │
  └──────────┘                └──────────┘               └──────────┘
        │                           │                           │
        │ PostgreSQL               │ Redis                     │ Kafka
        │ Replication              │ Cluster                   │ MirrorMaker
        │                           │                           │
        ▼                           ▼                           ▼
  ┌──────────┐                ┌──────────┐               ┌──────────┐
  │ Read     │                │ Sentinel │               │  Cross-  │
  │ Replicas │                │ /Cluster │               │  Region  │
  │ (3x)     │                │ (3x)     │               │  (DR)    │
  └──────────┘                └──────────┘               └──────────┘
```

---

## 3. Trading Engine Design

### 3.1 Quant Engine Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              QUANT ENGINE CLUSTER                                   │
└─────────────────────────────────────────────────────────────────────────────────────┘

                        ┌─────────────────────────┐
                        │   Strategy Scheduler    │
                        │   (Celery Beat)         │
                        └───────────┬─────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    │               │               │
                    ▼               ▼               ▼
          ┌───────────────┐ ┌───────────────┐ ┌───────────────┐
          │ Worker Node 1 │ │ Worker Node 2 │ │ Worker Node N │
          │ (User 1-1000) │ │(User 1001-2000)│ │(User 9001-10k)│
          └───────┬───────┘ └───────┬───────┘ └───────┬───────┘
                  │                 │                 │
                  ▼                 ▼                 ▼
          ┌─────────────────────────────────────────────────────────┐
          │              PER-USER STRATEGY EXECUTOR                  │
          ├─────────────────────────────────────────────────────────┤
          │                                                          │
          │  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
          │  │   Strategy  │───▶│  Indicator  │───▶│    Signal   │  │
          │  │   Instance  │    │   Engine    │    │  Generator  │  │
          │  └─────────────┘    └─────────────┘    └──────┬──────┘  │
          │                                                  │         │
          │  ┌──────────────────────────────────────────────▼──────┐  │
          │  │              Strategy State Machine                  │  │
          │  │  [IDLE] ──▶ [RUNNING] ──▶ [PAUSED] ──▶ [STOPPED]   │  │
          │  └──────────────────────────────────────────────────────┘  │
          │                                                          │
          └──────────────────────────────────────────────────────────┘
```

### 3.2 Strategy Execution Pipeline

```python
# Strategy Evaluation Pipeline (50ms target)
class StrategyExecutor:
    async def evaluate(self, strategy: Strategy, market_data: MarketData) -> Optional[Signal]:
        # Step 1: Load indicators (10ms)
        indicators = await self.indicator_engine.calculate(
            symbols=strategy.watchlist,
            indicators=strategy.required_indicators,
            timeframe=strategy.timeframe
        )
        
        # Step 2: Evaluate conditions (20ms)
        signal = await self.signal_generator.evaluate(
            strategy=strategy,
            indicators=indicators,
            current_prices=market_data.prices
        )
        
        # Step 3: Risk check (10ms)
        if signal:
            risk_result = await self.risk_service.check(signal)
            if not risk_result.approved:
                return None
        
        # Step 4: Generate order (10ms)
        return signal
```

### 3.3 Indicator Library Performance

| Indicator | Computation | Cache TTL | Parallel |
|-----------|-------------|-----------|----------|
| SMA | O(n) | 1s | Yes |
| EMA | O(n) | 1s | Yes |
| RSI | O(n) | 1s | Yes |
| MACD | O(n) | 1s | Yes |
| VWAP | O(n) | 1s | Yes |
| Bollinger | O(n) | 1s | Yes |
| ATR | O(n) | 1s | Yes |

### 3.4 Strategy State Machine

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           STRATEGY STATE MACHINE                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘

                              ┌──────────────┐
                              │    CREATED   │
                              └──────┬───────┘
                                     │ Activate()
                                     ▼
                         ┌──────────────────────┐
                         │    INITIALIZING     │
                         │  (Load indicators)  │
                         └──────────┬───────────┘
                                    │ Ready
                                    ▼
                    ┌────────────────────────────────┐
                    │                                │
           ┌────────▼────────┐              ┌───────▼───────┐
           │     RUNNING     │◀─────────────│    EVALUATING  │
           │                 │   Complete   │               │
           └────────┬────────┘              └───────────────┘
                    │                              ▲
                    │ Pause()                      │
                    ▼                              │
           ┌──────────────┐                        │
           │    PAUSED   │────────────────────────┘
           └──────┬───────┘
                  │
                  │ Stop() or Error
                  ▼
           ┌──────────────┐
           │   STOPPED    │
           └──────────────┘
```

---

## 4. Backtesting Architecture

### 4.1 Backtest System Design

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                            BACKTESTING ARCHITECTURE                                  │
└─────────────────────────────────────────────────────────────────────────────────────┘

  Client              Analytics             Backtest            Data
  Request             Service               Engine              Store
     │                    │                    │                  │
     │─── Backtest ──────▶│                    │                  │
     │    Request         │                    │                  │
     │                    │─── Job ───────────▶│                  │
     │                    │                    │                  │
     │                    │◄─── Job ID ────────│                  │
     │                    │                    │                  │
     │◄─── Job ID ───────│                    │                  │
     │                    │                    │                  │
     │                    │   ┌────────────────▼────────────────┐
     │                    │   │      BACKTEST EXECUTION          │
     │                    │   ├─────────────────────────────────┤
     │                    │   │                                  │
     │                    │   │  1. Load Historical Data        │
     │                    │   │     (PostgreSQL + Redis cache)  │
     │                    │   │                                  │
     │                    │   │  2. Initialize Strategy         │
     │                    │   │     (Spawn isolated context)    │
     │                    │   │                                  │
     │                    │   │  3. Iterate Time Series         │
     │                    │   │     ┌─────────────────────────┐ │
     │                    │   │     │ For each timestamp:     │ │
     │                    │   │     │  - Update indicators    │ │
     │                    │   │     │  - Evaluate strategy   │ │
     │                    │   │     │  - Generate signals     │ │
     │                    │   │     │  - Simulate orders      │ │
     │                    │   │     │  - Update positions     │ │
     │                    │   │     └─────────────────────────┘ │
     │                    │   │                                  │
     │                    │   │  4. Calculate Metrics           │
     │                    │   │     (Sharpe, Drawdown, etc.)     │
     │                    │   │                                  │
     │                    │   └────────────────┬────────────────┘
     │                    │                    │
     │                    │◄─── Results ───────│
     │                    │                    │
     │◄─── Results ───────│                    │
     │                    │                    │
```

### 4.2 Backtest Data Pipeline

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                         BACKTEST DATA FLOW                                            │
└─────────────────────────────────────────────────────────────────────────────────────┘

  Historical Data Store                    Execution Engine
  ┌─────────────────────┐                ┌─────────────────────┐
  │   PostgreSQL        │                │   Worker Pod        │
  │   (OHLCV data)      │                │   ┌─────────────┐  │
  └──────────┬──────────┘                │   │   Python    │  │
             │                           │   │  Sandbox    │  │
             │                           │   │  (Isolated) │  │
             │ Pull                      │   └──────┬──────┘  │
             │                           │          │         │
             ▼                           │          ▼         │
  ┌─────────────────────┐                │   ┌─────────────┐  │
  │   Redis Cache       │◀───────────────┤   │   Strategy  │  │
  │   (Aggregated)      │   Hot data     │   │   Runner    │  │
  └─────────────────────┘                │   └──────┬──────┘  │
                                          │          │         │
                                          │          ▼         │
                                          │   ┌─────────────┐  │
                                          │   │   Results   │  │
                                          │   │   Writer    │  │
                                          │   └──────┬──────┘  │
                                          └──────────┼─────────┘
                                                     │
                                                     ▼
                                          ┌─────────────────────┐
                                          │   Results Store     │
                                          │   (PostgreSQL)      │
                                          └─────────────────────┘
```

### 4.3 Backtest Performance Targets

| Data Range | Daily Bars | Intraday (1min) | Execution Time |
|------------|------------|-----------------|----------------|
| 1 year     | 252        | 0               | < 5 seconds    |
| 5 years    | 1,260      | 0               | < 30 seconds   |
| 1 year     | 252        | 78,000          | < 60 seconds   |
| 5 years    | 1,260      | 390,000         | < 5 minutes    |

### 4.4 Backtest Worker Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           BACKTEST WORKER POOL                                       │
└─────────────────────────────────────────────────────────────────────────────────────┘

                           ┌─────────────────────┐
                           │   Job Queue        │
                           │   (Kafka)          │
                           └──────────┬──────────┘
                                      │
              ┌───────────────────────┼───────────────────────┐
              │                       │                       │
              ▼                       ▼                       ▼
    ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
    │  Worker Pod 1   │     │  Worker Pod 2   │     │  Worker Pod N   │
    │  (CPU: 4 cores) │     │  (CPU: 4 cores) │     │  (CPU: 4 cores) │
    │  Memory: 16GB   │     │  Memory: 16GB   │     │  Memory: 16GB   │
    └────────┬────────┘     └────────┬────────┘     └────────┬────────┘
             │                       │                       │
             └───────────────────────┼───────────────────────┘
                                     │
                                     ▼
                          ┌─────────────────────┐
                          │   Resource          │
                          │   Manager           │
                          │   (Kubernetes)      │
                          └─────────────────────┘
```

---

## 5. Infrastructure Architecture

### 5.1 Kubernetes Cluster Design

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           KUBERNETES CLUSTER (AWS EKS)                               │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           CONTROL PLANE                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                                  │
│  │  API Server │  │   etcd     │  │ Scheduler   │  (Managed by AWS)               │
│  └─────────────┘  └─────────────┘  └─────────────┘                                  │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           NODE GROUPS                                                │
│                                                                                      │
│  ┌───────────────────────────────────────────────────────────────────────────────┐  │
│  │  SYSTEM NODES (t3.xlarge x 3)                                                 │  │
│  │  - kube-system pods                                                           │  │
│  │  - monitoring, logging                                                        │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                      │
│  ┌───────────────────────────────────────────────────────────────────────────────┐  │
│  │  API NODES (c5.2xlarge x 10) - Auto-scaling 5-20                             │  │
│  │  - Auth, User, Strategy, Order services                                       │  │
│  │  - Request: 50K RPM                                                           │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                      │
│  ┌───────────────────────────────────────────────────────────────────────────────┐  │
│  │  TRADING NODES (c5.4xlarge x 15) - Auto-scaling 10-30                        │  │
│  │  - Quant Engine, Broker Service                                                │  │
│  │  - Low latency, real-time                                                     │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                      │
│  ┌───────────────────────────────────────────────────────────────────────────────┐  │
│  │  BACKTEST NODES (r5.4xlarge x 8) - On-demand 0-20                            │  │
│  │  - Backtest Engine                                                            │  │
│  │  - GPU-enabled for ML backtests                                              │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                      │
│  ┌───────────────────────────────────────────────────────────────────────────────┐  │
│  │  DATA NODES (r5.xlarge x 6) - Always-on 6                                     │  │
│  │  - PostgreSQL, Redis, Kafka                                                   │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### 5.2 Database Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              DATABASE LAYER                                          │
└─────────────────────────────────────────────────────────────────────────────────────┘

  PostgreSQL Primary              PostgreSQL Replica          Redis Cluster
  ┌─────────────────┐           ┌─────────────────┐         ┌─────────────────┐
  │  Writer Node    │◄─────────▶│  Reader Node 1  │         │  Master Node   │
  │  (db.r5.xlarge) │  Streaming│  (db.r5.large)  │         │  (cache.r5.xl)  │
  └────────┬────────┘   Replica │        │         │         └────────┬────────┘
           │                    └─────────┼─────────┘                │
           │                              │                         │
           │                    ┌─────────▼─────────┐       ┌─────────▼─────────┐
           │                    │  Reader Node 2    │       │  Replica Node 1  │
           │                    │  (db.r5.large)   │       │  (cache.r5.large)│
           │                    └───────────────────┘       └─────────┬─────────┘
           │                                                      │
           │                                             ┌─────────▼─────────┐
           │                                             │  Replica Node 2   │
           └─────────────────▶ S3 Backup                 │  (cache.r5.large) │
                                    (Daily)              └───────────────────┘

  Tablespaces:
  - users: User data, authentication
  - trading: Orders, positions, strategies
  - analytics: Trade history, performance
  - market_data: OHLCV (partitioned by symbol)
```

### 5.3 Caching Strategy

| Cache Type | Data | TTL | Eviction |
|------------|------|-----|----------|
| Redis | User sessions | 30 min | LRU |
| Redis | Strategy configs | 5 min | LRU |
| Redis | Market prices | 1 sec | Time-based |
| Redis | Indicator values | 1 sec | Time-based |
| Redis | Orderbook | 100 ms | Time-based |
| Local (in-memory) | JWT tokens | Token expiry | Expiry |

### 5.4 Network Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              NETWORK ARCHITECTURE                                    │
└─────────────────────────────────────────────────────────────────────────────────────┘

                          ┌─────────────────────────┐
                          │      AWS Route 53       │
                          │    (DNS + Health)       │
                          └───────────┬─────────────┘
                                      │
                          ┌───────────▼─────────────┐
                          │    CloudFront CDN      │
                          │   (Static assets)      │
                          └───────────┬─────────────┘
                                      │
                          ┌───────────▼─────────────┐
                          │     Application LB      │
                          │   (ALB - HTTPS/TLS)    │
                          └───────────┬─────────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    │                 │                 │
           ┌────────▼────────┐ ┌─────▼─────┐ ┌────────▼────────┐
           │  EKS Ingress    │ │  EKS      │ │  WebSocket     │
           │  (Kong)         │ │  Internal │ │  ALB            │
           │  :443           │ │  NLB      │ │  :443           │
           └────────┬────────┘ └─────┬─────┘ └────────┬────────┘
                    │                │                │
                    ▼                ▼                ▼
           ┌─────────────────────────────────────────────────────────┐
           │                 VPC (10.0.0.0/16)                      │
           │                                                          │
           │  ┌──────────────────────────────────────────────────┐  │
           │  │  Private Subnets (App Tier)                     │  │
           │  │  10.0.1.0/24 | 10.0.2.0/24 | 10.0.3.0/24        │  │
           │  │  - EKS Nodes                                     │  │
           │  │  - Services                                     │  │
           │  └──────────────────────────────────────────────────┘  │
           │                                                          │
           │  ┌──────────────────────────────────────────────────┐  │
           │  │  Data Subnets (Database Tier)                    │  │
           │  │  10.0.101.0/24 | 10.0.102.0/24 | 10.0.103.0/24  │  │
           │  │  - RDS PostgreSQL                                │  │
           │  │  - ElastiCache Redis                            │  │
           │  │  - MSK Kafka                                    │  │
           │  └──────────────────────────────────────────────────┘  │
           │                                                          │
           └─────────────────────────────────────────────────────────┘
                          │                │                │
                          ▼                ▼                ▼
                   External          External          External
                   Brokers           Market Data       Email/SMS
                   (Alpaca, IB)      (Polygon)         (SendGrid)
```

### 5.5 Disaster Recovery

| Component | RPO | RTO | Strategy |
|-----------|-----|-----|----------|
| PostgreSQL | 1 min | 5 min | Multi-AZ, Point-in-time recovery |
| Redis | 0 | 5 min | Multi-AZ cluster with auto-failover |
| Kafka | 1 min | 10 min | MSK multi-AZ replication |
| Application | 0 | 3 min | Blue-green deployment |
| S3 Data | 0 | 1 min | Cross-region replication |

### 5.6 Autoscaling Configuration

| Service | Metric | Scale Up | Scale Down |
|---------|--------|----------|------------|
| API | CPU > 70% | +2 pods | -2 pods |
| API | Request latency P99 > 500ms | +4 pods | -2 pods |
| Quant Engine | Queue depth > 100 | +5 workers | -2 workers |
| Backtest | Queue depth > 50 | +10 workers | -5 workers |
| WebSocket | Connections > 5000 | +3 pods | -2 pods |

---

## 6. Security Architecture

### 6.1 Zero Trust Security Model

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                            SECURITY LAYERS                                          │
└─────────────────────────────────────────────────────────────────────────────────────┘

  Layer 1: Edge Security
  ┌─────────────────────────────────────────────────────────────────────────────────┐
  │  - WAF (AWS WAF) - SQL injection, XSS, OWASP Top 10                            │
  │  - DDoS Protection (AWS Shield)                                                │
  │  - Rate Limiting (Kong) - 100 req/min per user                                 │
  │  - IP Reputation Filtering                                                     │
  └─────────────────────────────────────────────────────────────────────────────────┘
                                      │
  Layer 2: Application Security
  ┌─────────────────────────────────────────────────────────────────────────────────┐
  │  - mTLS between services (Istio)                                               │
  │  - JWT validation on every request                                            │
  │  - API Key rotation (30 days)                                                  │
  │  - Input validation (Pydantic)                                                 │
  │  - CSRF protection                                                              │
  └─────────────────────────────────────────────────────────────────────────────────┘
                                      │
  Layer 3: Data Security
  ┌─────────────────────────────────────────────────────────────────────────────────┐
  │  - Encryption at rest (AES-256)                                                │
  │  - Encryption in transit (TLS 1.3)                                            │
  │  - Secrets in Vault (AWS Secrets Manager)                                      │
  │  - API key encryption (AES-256-GCM)                                           │
  │  - Database column-level encryption for sensitive data                         │
  └─────────────────────────────────────────────────────────────────────────────────┘
                                      │
  Layer 4: Trading Security
  ┌─────────────────────────────────────────────────────────────────────────────────┐
  │  - Risk limits enforced before every order                                     │
  │  - Daily loss auto-pause                                                       │
  │  - Kill switch (instant global stop)                                          │
  │  - Position size limits                                                        │
  │  - Audit logging for all trade actions                                         │
  └─────────────────────────────────────────────────────────────────────────────────┘
```

### 6.2 Secrets Management

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                         SECRETS MANAGEMENT                                          │
└─────────────────────────────────────────────────────────────────────────────────────┘

                    ┌─────────────────────────┐
                    │   AWS Secrets Manager   │
                    │   (Primary Vault)       │
                    └───────────┬─────────────┘
                                │
          ┌─────────────────────┼─────────────────────┐
          │                     │                     │
          ▼                     ▼                     ▼
   ┌─────────────┐       ┌─────────────┐       ┌─────────────┐
   │  Database   │       │  Broker API  │       │  JWT        │
   │  Credentials│       │  Keys        │       │  Secrets    │
   └─────────────┘       └─────────────┘       └─────────────┘
```

---

## 7. Observability Architecture

### 7.1 Monitoring Stack

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           OBSERVABILITY LAYER                                       │
└─────────────────────────────────────────────────────────────────────────────────────┘

  Application Logs           Metrics                   Traces
        │                         │                        │
        ▼                         ▼                        ▼
  ┌─────────────┐           ┌─────────────┐         ┌─────────────┐
  │  Fluent Bit │           │ Prometheus  │         │ Jaeger      │
  │  (Collector)│           │ (Metrics)   │         │ (Tracing)   │
  └──────┬──────┘           └──────┬──────┘         └──────┬──────┘
         │                         │                        │
         └─────────────────────────┼────────────────────────┘
                                   │
                                   ▼
                          ┌─────────────────┐
                          │  Grafana        │
                          │  (Dashboards)   │
                          └─────────────────┘
                                   │
                                   ▼
                          ┌─────────────────┐
                          │  PagerDuty      │
                          │  (Alerting)     │
                          └─────────────────┘
```

### 7.2 Key Metrics Dashboard

| Category | Metrics | Alert Threshold |
|----------|---------|-----------------|
| Trading | Order fill rate | < 99.9% |
| Trading | Order latency P99 | > 500ms |
| Trading | Strategy signals/sec | < expected |
| System | API response time P99 | > 2s |
| System | Error rate | > 1% |
| System | Pod restarts | > 5/hour |
| Business | Active users | < expected |
| Business | Daily trade volume | < expected |

---

## 8. Capacity Planning (10K Users)

### 8.1 Resource Calculations

| Resource | Calculation | Target | Provisioned |
|----------|--------------|--------|-------------|
| API Requests | 10K users × 60 req/hr | 600K/hr | 1M/hr |
| Concurrent WebSocket | 10K users × 20% | 2K | 5K |
| Active Strategies | 10K users × 2 avg | 20K | 30K |
| Orders/day | 10K users × 10 avg | 100K/day | 500K/day |
| Backtests/day | 10K users × 1 avg | 10K/day | 50K/day |
| Data Storage | 10K × 1GB/year | 10TB | 50TB |

### 8.2 Cost Estimation (Monthly)

| Component | Instance | Quantity | Monthly Cost |
|-----------|----------|----------|--------------|
| EKS Control Plane | Managed | 1 | $730 |
| EKS Nodes (API) | c5.2xlarge | 10 | $3,060 |
| EKS Nodes (Trading) | c5.4xlarge | 15 | $7,650 |
| EKS Nodes (Backtest) | r5.4xlarge | 8 | $4,080 |
| RDS PostgreSQL | db.r5.4xlarge | 1 | $1,200 |
| RDS Read Replica | db.r5.2xlarge | 2 | $1,220 |
| ElastiCache | cache.r5.4xlarge | 3 | $1,530 |
| MSK Kafka | kafka.t3.small | 6 | $900 |
| ALB | Application | 3 | $50 |
| CloudFront | 100GB/mo | 1 | $100 |
| S3 | 10TB | 1 | $250 |
| **Total** | | | **$20,770** |

---

*Document Version: 2.0*  
*Last Updated: March 7, 2026*  
*Classification: Internal Use Only*
