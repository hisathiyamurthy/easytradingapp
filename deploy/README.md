# Split Deployment Guide

This directory contains the split deployment configuration for the trading application.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    INFRASTRUCTURE LAYER                     │
│  ┌──────────────┐              ┌──────────────┐          │
│  │   PostgreSQL │              │     Redis    │          │
│  │  (Persistent) │              │  (Persistent) │          │
│  └──────────────┘              └──────────────┘          │
│           ▲                            ▲                    │
└───────────│────────────────────────────│───────────────────┘
            │                            │
            ▼                            ▼
┌─────────────────────────────────────────────────────────────┐
│                      APP LAYER                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │   Backend    │  │   Frontend   │  │ Mock Broker  │  │
│  │  (Restart)   │  │  (Restart)   │  │  (Restart)   │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

### 1. Initial Setup

```bash
cd deploy

# Copy and edit environment variables
cp .env.example .env
# Edit .env with your secure passwords

# Create backups directory
mkdir -p backups
```

### 2. Start Infrastructure (One-time / Always Running)

```bash
# Start infrastructure services (db, redis)
docker compose -f docker-compose.infra.yml up -d

# Verify health
docker compose -f docker-compose.infra.yml ps

# Check logs
docker compose -f docker-compose.infra.yml logs -f
```

### 3. Start Application Services

```bash
# Start all application services
docker compose -f docker-compose.app.yml up -d

# Verify
docker compose -f docker-compose.app.yml ps
```

## Managing Services

### Update Application Without Data Loss

```bash
# 1. Backup database first
./backup.sh

# 2. Rebuild application services only
docker compose -f docker-compose.app.yml build backend
docker compose -f docker-compose.app.yml build frontend

# 3. Restart application services (infra stays running)
docker compose -f docker-compose.app.yml up -d --force-recreate backend frontend
```

### Restart Infrastructure Safely

```bash
# Infrastructure uses named volumes - data persists
docker compose -f docker-compose.infra.yml restart db redis
```

### Full Stop (Data Preserved)

```bash
# Stop application only (data safe)
docker compose -f docker-compose.app.yml down

# Stop infrastructure (volumes persist - data safe)
docker compose -f docker-compose.infra.yml down

# Data persists in Docker named volumes
```

### Complete Reset (DATA LOSS!)

```bash
# Only run this if you want to delete ALL data
docker compose -f docker-compose.infra.yml down -v  # -v removes volumes
docker compose -f docker-compose.app.yml down
```

## Useful Commands

```bash
# View all containers
docker compose -f docker-compose.infra.yml -f docker-compose.app.yml ps

# View logs
docker compose -f docker-compose.infra.yml logs db
docker compose -f docker-compose.app.yml logs backend

# Connect to database
docker exec -it trading_db psql -U postgres trading

# Redis CLI
docker exec -it trading_redis redis-cli -a YOUR_PASSWORD

# Backup manually
docker exec trading_db pg_dump -U postgres trading > backup.sql
```

## Service URLs

- Frontend: http://localhost:5300
- Backend API: http://localhost:8000
- Mock Broker: http://localhost:8001
- PostgreSQL: localhost:5432
- Redis: localhost:6379
