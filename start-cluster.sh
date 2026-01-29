#!/usr/bin/env bash
set -euo pipefail

dockerd-entrypoint.sh >/var/log/dockerd.log 2>&1 &

echo "Waiting for Docker daemon..."
until docker info >/dev/null 2>&1; do
  sleep 1
done

if ! k3d registry list | grep -q wiki-registry; then
  k3d registry create wiki-registry --port 5000
fi

if ! k3d cluster list | grep -q wiki; then
  k3d cluster create wiki \
    --agents 1 \
    --servers 1 \
    --registry-use k3d-wiki-registry:5000 \
    -p "8080:80@loadbalancer"
fi

export KUBECONFIG=/k3d/kubeconfig.yaml
k3d kubeconfig get wiki > "$KUBECONFIG"

docker build -t wiki-fastapi:latest /app/wiki-service
docker tag wiki-fastapi:latest k3d-wiki-registry:5000/wiki-fastapi:latest
docker push k3d-wiki-registry:5000/wiki-fastapi:latest

helm upgrade --install wiki /app/wiki-chart \
  --set fastapi.image_name=k3d-wiki-registry:5000/wiki-fastapi \
  --set fastapi.image_tag=latest \
  --set ingress.enabled=true \
  --set ingress.className=traefik

kubectl rollout status deployment/wiki-fastapi --timeout=180s
kubectl rollout status deployment/wiki-postgres --timeout=180s
kubectl rollout status deployment/wiki-prometheus --timeout=180s
kubectl rollout status deployment/wiki-grafana --timeout=180s

echo "Cluster ready. Access via http://localhost:8080"
tail -f /dev/null
