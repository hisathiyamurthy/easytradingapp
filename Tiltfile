# Tiltfile for EasyTradingApp
# Local Kubernetes development with live reload

load('ext://stale_deprecated_api_version', 'v0.4.0', 'starboard')
load('ext://helm', 'v0.3.0')

# Configuration
PROJECT_NAME = 'easytradingapp'
NAMESPACE = 'easytrading'

# Docker compose services to deploy
docker_compose([
    'docker-compose.yml',
])

# Enable hot reload for backend
local_go = local(
    'go version',
    quiet = True,
)

# Kubernetes deployments
k8s_yaml([
    'deploy/k8s/00-namespace.yaml',
    'deploy/k8s/01-configmap-secret.yaml',
    'deploy/k8s/02-backend-deployment.yaml',
    'deploy/k8s/03-worker-deployment.yaml',
    'deploy/k8s/04-frontend-deployment.yaml',
])

# Configure docker build for backend with live reload
docker_build(
    f'{PROJECT_NAME}/backend',
    './backend',
    dockerfile = 'backend/Dockerfile',
    live_update = [
        sync('./backend', '/app'),
    ],
    ignore = [
        '*.pyc',
        '__pycache__',
        '.git',
        'node_modules',
        'venv',
    ],
)

# Configure docker build for frontend with live reload
docker_build(
    f'{PROJECT_NAME}/frontend',
    './frontend',
    dockerfile = 'frontend/Dockerfile',
    live_update = [
        sync('./frontend/src', '/app/src'),
    ],
    ignore = [
        'node_modules',
        '.git',
    ],
)

# Configure docker build for worker
docker_build(
    f'{PROJECT_NAME}/worker',
    './backend',
    dockerfile = 'backend/Dockerfile.worker',
    live_update = [
        sync('./backend', '/app'),
    ],
    ignore = [
        '*.pyc',
        '__pycache__',
        '.git',
    ],
)

# Port forwards for local development
k8s_resource(
    'backend',
    port_forwards = [
        port_forward(8000, '8000', 'API Server'),
        port_forward(8000, '8000', 'Health Check'),
    ],
)

k8s_resource(
    'frontend',
    port_forwards = [
        port_forward(5173, '5173', 'Frontend'),
    ],
)

# Custom labels
k8s_resource(
    'backend',
    labels = {
        'app': 'backend',
        'component': 'api',
    },
)

k8s_resource(
    'frontend',
    labels = {
        'app': 'frontend',
        'component': 'ui',
    },
)

k8s_resource(
    'worker',
    labels = {
        'app': 'worker',
        'component': 'background',
    },
)

# Settings for better DX
settings = {
    'enabled': True,
    'experimental': {
        'live_update_via_annotation': True,
    },
}

# Custom actions
def refresh_backend():
    """Trigger a rolling restart of the backend"""
    k8s_object('deployment', 'backend', namespace=NAMESPACE).rollout()

def refresh_frontend():
    """Trigger a rolling restart of the frontend"""
    k8s_object('deployment', 'frontend', namespace=NAMESPACE).rollout()

def logs_backend():
    """Stream backend logs"""
    local('kubectl logs -l app=backend -n {} --follow'.format(NAMESPACE))

def logs_worker():
    """Stream worker logs"""
    local('kubectl logs -l app=worker -n {} --follow'.format(NAMESPACE))

# Add custom menu
local_resource(
    'logs-backend',
    'kubectl logs -l app=backend -n {} --follow'.format(NAMESPACE),
    serve_path = '.',
    label = 'Logs',
)

local_resource(
    'logs-worker',
    'kubectl logs -l app=worker -n {} --follow'.format(NAMESPACE),
    serve_path = '.',
    label = 'Worker Logs',
)

# Resource group display
k8s_resource(
    'backend',
    resource_deps = ['postgres', 'redis'],
)

k8s_resource(
    'worker',
    resource_deps = ['backend', 'redis'],
)

k8s_resource(
    'frontend',
    resource_deps = ['backend'],
)

# Environment variables for local development
k8s_resource(
    'backend',
    env = {
        'ENVIRONMENT': 'development',
        'DEBUG': 'true',
    },
)

# Auto-detect port changes
trigger_mode(TRIGGER_MODE_AUTO)

# Fallback to manual when saving any file
update_settings(k8s_autoroll_enabled = True)