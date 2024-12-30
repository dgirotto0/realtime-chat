#!/usr/bin/env bash
set -e

# Ajuste as tags de versão conforme desejar.
BACKEND_VERSION="1.1"
FRONTEND_VERSION="1.1"

# 1. Build do BACKEND
echo "===== Building backend image ====="
docker build -t dvgirotto/my-anonymous-chat-backend:${BACKEND_VERSION} ./backend

# 2. Envia para o Docker Hub (ou outro registry)
echo "===== Pushing backend image ====="
docker push dvgirotto/my-anonymous-chat-backend:${BACKEND_VERSION}

# 3. Build do FRONTEND
echo "===== Building frontend image ====="
docker build -t dvgirotto/my-anonymous-chat-frontend:${FRONTEND_VERSION} ./frontend/chat-frontend

# 4. Envia para o Docker Hub
echo "===== Pushing frontend image ====="
docker push dvgirotto/my-anonymous-chat-frontend:${FRONTEND_VERSION}

# 5. Altera a imagem nos Deployments do Kubernetes
echo "===== Updating backend deployment in Kubernetes ====="
kubectl set image deployment/backend-deployment \
  backend=dvgirotto/my-anonymous-chat-backend:${BACKEND_VERSION} \
  --record

echo "===== Updating frontend deployment in Kubernetes ====="
kubectl set image deployment/frontend-deployment \
  frontend=dvgirotto/my-anonymous-chat-frontend:${FRONTEND_VERSION} \
  --record

# 6. Aguarda o rollout completo
echo "===== Waiting for backend deployment rollout ====="
kubectl rollout status deployment/backend-deployment

echo "===== Waiting for frontend deployment rollout ====="
kubectl rollout status deployment/frontend-deployment

echo "===== Done! ====="
