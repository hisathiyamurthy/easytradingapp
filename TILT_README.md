# Tilt Development Guide for EasyTradingApp
# ==========================================
# 
# Install Tilt: https://docs.tilt.dev/install.html
#
# Usage:
#   tilt up           # Start development
#   tilt down         # Stop development
#   tilt debug        # Start with debugging enabled
#   tilt adopt        # Adopt existing resources
#
# Features:
# - Live reload for backend (Python) and frontend (React)
# - Automatic Docker builds
# - Port forwarding for API (8000) and Frontend (5173)
# - Logs streaming
# - Resource dependencies

# Quick Start
# ============
# 1. Install Tilt: brew install tilt-dev/tap/tilt
# 2. Ensure Docker is running
# 3. Start Minikube or kind cluster: kind create cluster
# 4. Run: tilt up
#
# The platform will be available at:
# - API: http://localhost:8000
# - Frontend: http://localhost:5173
# - Health: http://localhost:8000/health
#
# Environment Variables (auto-configured)
# =========================================
# The Tiltfile automatically configures:
# - ENVIRONMENT=development
# - DEBUG=true
# - DATABASE_URL (from docker-compose)
# - REDIS_URL (from docker-compose)
#
# Live Reload
# ===========
# Changes to backend/*.py files trigger automatic reload
# Changes to frontend/src/* files trigger automatic rebuild
#
# Custom Commands
# ===============
# In Tilt UI, use the sidebar to:
# - View logs (backend, worker)
# - Restart resources
# - Shell into containers
#
# Troubleshooting
# ==============
# If pods don't start, check:
#   kubectl get pods -n easytrading
#   kubectl describe pod <pod-name> -n easytrading
#
# To reset:
#   tilt down && rm -rf .tiltbuild && tilt up