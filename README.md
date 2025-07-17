# Claims UI Deployment on Azure AKS

This repository contains the configuration and deployment scripts for hosting a **Streamlit-based UI** on **Azure Kubernetes Service (AKS)** with integration to backend services in the same cluster.

---

## **Architecture Overview**

- **Frontend**: Streamlit app (Claims UI)
- **Backend**: Decision Service (REST API) deployed in another namespace within the same AKS cluster
- **Ingress**: NGINX Ingress Controller with TLS termination (cert-manager + Let’s Encrypt)
- **Container Registry**: Azure Container Registry (ACR)
- **Namespace**: `claims-ui`
- **Components**:
  - **Deployment** (`deployment.yaml`): Streamlit container with environment variables from Secret & ConfigMap
  - **Service** (`service.yaml`): ClusterIP for internal routing
  - **Ingress** (`ingress.yaml`): Public endpoint via HTTPS
  - **ConfigMap**: API endpoint configuration
  - **Secrets**: API credentials and ACR authentication
- **Domain**: `https://<your-domain>.cloudapp.azure.com`

---

## **Setup Instructions**

### **1. Build and Push Docker Image**

We use `docker buildx` for multi-platform support (important for AKS nodes running on Linux):

```bash
docker buildx build --platform linux/amd64 -t <ACR_NAME>.azurecr.io/claims-ui:<TAG> .
az acr login --name <ACR_NAME>
docker push <ACR_NAME>.azurecr.io/claims-ui:<TAG>
```

**Why `buildx`?**  
If you build on a Mac (Apple Silicon), Docker defaults to `arm64`. AKS nodes typically run `amd64`. Pushing an ARM image results in:

```
no match for platform in manifest
```

---

### **2. Attach ACR to AKS**

```bash
az aks update   --name <AKS_CLUSTER_NAME>   --resource-group <RESOURCE_GROUP>   --attach-acr <ACR_NAME>
```

This avoids manual creation of `imagePullSecrets`.

---

### **3. Deploy to Kubernetes**

```bash
./deploy.sh
```

What it applies:
- Namespace (`claims-ui`)
- ConfigMap, Secrets
- Deployment & Service
- Ingress with TLS
- Optional HPA

---

### **4. TLS with Let’s Encrypt**

- Ensure `cert-manager` and `ClusterIssuer` are installed.
- Ingress must include:
  ```yaml
  cert-manager.io/cluster-issuer: letsencrypt-prod
  ```
- TLS secret will be created automatically by cert-manager.

---

### **5. Access Application**

```
https://<your-domain>.cloudapp.azure.com
```

---

## **Internal API Calls**

Backend services in other namespaces should be called using **Kubernetes DNS**:

```
http://<service-name>.<namespace>.svc.cluster.local:<port>/<path>
```

Example:
```
http://decision-service.decision.svc.cluster.local/rest/v1/ClaimsAdj/1.0/dateCheck/1.16
```

**If this fails:**
- Verify the **Service type** of the backend (should be ClusterIP or higher).
- Check **NetworkPolicy** (if applied).
- Confirm DNS resolution:
  ```bash
  kubectl exec -it <claims-ui-pod> -- nslookup decision-service.decision.svc.cluster.local
  ```
- Ensure the backend Service port is correctly exposed.

---

## **Lessons Learned**

### ✅ 1. Multi-Arch Image Builds Are Critical
- **Problem:** Image pull errors (`no match for platform`) on AKS when building on Mac.
- **Root Cause:** Mac defaults to `arm64`; AKS expects `amd64`.
- **Solution:** Use `docker buildx build --platform linux/amd64`.

---

### ✅ 2. ACR Authentication Made Simple
- **Problem:** Image pull secrets caused errors like:
  ```
  FailedToRetrieveImagePullSecret acr-secret
  ```
- **Solution:** Use `az aks update --attach-acr` to link ACR to AKS, eliminating manual secrets.

---

### ✅ 3. Ingress Path and Streamlit Behavior
- **Problem:** App returned a blank page when using `/claims-ui`.
- **Root Cause:** Streamlit serves UI from `/` by default.
- **Solutions:**
  - Add annotation:  
    ```
    nginx.ingress.kubernetes.io/rewrite-target: /
    ```
  - OR set path as `/` in Ingress.

---

### ✅ 4. TLS Requires Proper Annotations
- Missing `cert-manager.io/cluster-issuer` prevents certificate creation.
- Must also include `secretName` under `tls`.

---

### ✅ 5. Internal Service Communication Needs DNS
- **Best Practice:** Use internal DNS instead of public ingress for service-to-service calls.
- **Troubleshooting Steps:**
  - Check cluster DNS (`nslookup` inside pod).
  - Validate service names and namespaces.
  - Confirm no restrictive NetworkPolicies.

---

### ✅ 6. Automate Deployment
- A structured script (`deploy.sh`) ensures consistency:
  - Builds image with correct platform
  - Pushes to ACR
  - Deploys manifests in order

---

## **Next Steps**
- Package with **Helm** for flexibility.
- Add **HPA** for scaling under load.
- Secure internal API calls with **NetworkPolicy**.
- Automate with **CI/CD pipeline** (GitHub Actions/Azure DevOps).

---
