# cleanup.sh - Script to clean up resources
#!/bin/bash

echo "🧹 Cleaning up resources..."

# Delete Kubernetes resources
kubectl delete namespace claims-ui

# Optionally delete images from ACR
# az acr repository delete --name your-acr-name --repository claims-ui

echo "✅ Cleanup completed!"
