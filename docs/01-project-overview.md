# EasyTradingApp - Project Overview

## 1. Project Summary

**Project Name:** EasyTradingApp  
**Type:** Algorithmic Trading Platform (Web Application)  
**Tech Stack:**
- **Frontend:** React + TypeScript + Vite
- **Backend:** Python FastAPI
- **Database:** PostgreSQL
- **Cache:** Redis
- **Container:** Docker

## 2. Core Features

### 2.1 Authentication & Authorization
- User registration with email/password
- JWT-based authentication
- Role-based access control (Admin, Trader)
- Session management
- Password reset flow

### 2.2 Broker Integration
- Multiple broker account connections
- Encrypted API key storage
- Broker connection testing

### 2.3 Strategy Management
- Create, edit, delete trading strategies
- Strategy activation/deactivation
- Strategy cloning
- Strategy parameters configuration
- **Strategy Builder (NLP)** - Natural language to strategy conversion

### 2.4 Trading
- Live trading execution
- Paper trading simulation
- Order management (market, limit, stop-loss)
- Position tracking

### 2.5 Portfolio & Analytics
- Portfolio dashboard
- Position management
- Performance analytics
- Trade history

### 2.6 Risk Management
- Risk rule configuration
- Kill switch (per-strategy and global)
- Daily loss limits

### 2.7 Backtesting
- Historical strategy testing
- Equity curve visualization
- Performance summary

### 2.8 Admin Features
- User management (approve, reject, suspend)
- System monitoring
- Broker status overview

## 3. User Roles

| Role | Permissions |
|------|-------------|
| **Admin** | Full system access, user management, save strategies |
| **Trader** | Create strategies, trade, view portfolio |
| **Pending** | Registration awaiting approval |

## 4. Current Status

- ✅ Authentication system complete
- ✅ Broker integration complete
- ✅ Strategy management complete
- ✅ Strategy Builder (NLP) - Enhanced with EMA parsing
- ✅ Trading execution complete
- ✅ Portfolio tracking complete
- ✅ Risk management complete
- ✅ Backtesting - Partial
- ✅ Admin panel - Complete

## 5. Quick Links

- [API Documentation](./05-api-contract.md)
- [Frontend Structure](./07-frontend-structure.md)
- [Backend Structure](./08-backend-structure.md)
- [Deployment Guide](./11-deployment.md)
- [Development Guidelines](./12-development-guidelines.md)

---

*Last Updated: March 2026*
