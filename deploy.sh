#!/bin/bash

# Load .env if exists
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Variables
IMAGE="$ACR_NAME.azurecr.io/$IMAGE_NAME:$IMAGE_TAG"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting deployment to Azure AKS...${NC}"

# Build and push Docker image
echo -e "${YELLOW}📦 Building and pushing Docker image for linux/amd64...${NC}"
echo "docker buildx build --platform linux/amd64 -t $IMAGE --push ."
docker buildx build --platform linux/amd64 -t $IMAGE --push .

# Login to ACR (optional because --push works with Docker's ACR auth)
echo -e "${YELLOW}🔑 Logging into Azure Container Registry...${NC}"
echo "az acr login --name $ACR_NAME"
az acr login --name $ACR_NAME

# Get AKS credentials
echo -e "${YELLOW}🔧 Getting AKS credentials...${NC}"
az aks get-credentials --resource-group $RESOURCE_GROUP --name $AKS_CLUSTER --overwrite-existing

# Deploy to Kubernetes
echo -e "${YELLOW}☸️ Deploying to Kubernetes...${NC}"
kubectl apply -f kubernetes/namespace.yaml
kubectl apply -f kubernetes/secret.yaml
kubectl apply -f kubernetes/configmap.yaml
kubectl apply -f kubernetes/deployment.yaml
kubectl apply -f kubernetes/service.yaml
kubectl apply -f kubernetes/ingress.yaml

echo -e "${GREEN}✅ Deployment completed!${NC}"

# Show deployment status
kubectl get pods -n claims-ui
kubectl get services -n claims-ui
