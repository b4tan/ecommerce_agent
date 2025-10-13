# Google Cloud Platform Deployment Guide

This guide covers deploying the E-commerce AI Agent on Google Cloud Platform using Cloud Run (serverless, recommended) or Compute Engine (VM-based).

## 🚀 Option 1: Cloud Run (Recommended)

**Best for**: Serverless, auto-scaling, pay-per-use deployment

### Prerequisites

1. **Google Cloud Account** with billing enabled
2. **gcloud CLI** installed: https://cloud.google.com/sdk/docs/install
3. **Docker** installed locally
4. **Project created** in GCP Console

### Step 1: Setup GCP Project

```bash
# Login to Google Cloud
gcloud auth login

# Create a new project (or use existing)
gcloud projects create ecommerce-agent-PROJECT_ID --name="Ecommerce Agent"

# Set project
gcloud config set project ecommerce-agent-PROJECT_ID

# Enable required APIs
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable containerregistry.googleapis.com
gcloud services enable artifactregistry.googleapis.com
```

### Step 2: Set Up Budget Alerts (CRITICAL!)

1. Go to https://console.cloud.google.com/billing
2. Click **Budgets & alerts**
3. Click **CREATE BUDGET**
4. Configure:
   - **Name**: "Monthly Budget Alert"
   - **Budget amount**: $20 (or your preferred limit)
   - **Alert thresholds**: 50%, 90%, 100%
   - **Email notifications**: Add your email
5. Click **FINISH**

### Step 3: Build and Push Docker Image

```bash
# Navigate to project directory
cd /path/to/ecommerce_agent

# Configure Docker for GCP
gcloud auth configure-docker

# Build image using Cloud Build (recommended - faster)
gcloud builds submit --tag gcr.io/ecommerce-agent-PROJECT_ID/ecommerce-agent

# OR build locally and push
docker build -t gcr.io/ecommerce-agent-PROJECT_ID/ecommerce-agent .
docker push gcr.io/ecommerce-agent-PROJECT_ID/ecommerce-agent
```

### Step 4: Deploy to Cloud Run

```bash
# Deploy with environment variables
gcloud run deploy ecommerce-agent \
  --image gcr.io/ecommerce-agent-PROJECT_ID/ecommerce-agent \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --timeout 300 \
  --max-instances 10 \
  --set-env-vars GOOGLE_API_KEY=your_gemini_api_key_here \
  --set-env-vars ENABLE_RATE_LIMITING=true \
  --set-env-vars MAX_REQUESTS_PER_MINUTE=10 \
  --set-env-vars MAX_REQUESTS_PER_HOUR=100 \
  --set-env-vars MAX_REQUESTS_PER_DAY=500 \
  --set-env-vars MAX_IMAGE_UPLOADS_PER_HOUR=20 \
  --set-env-vars MAX_IMAGE_UPLOADS_PER_DAY=100 \
  --set-env-vars MAX_DAILY_API_CALLS=1000

# Get the service URL
gcloud run services describe ecommerce-agent --region us-central1 --format='value(status.url)'
# Example output: https://ecommerce-agent-abc123-uc.a.run.app
```

### Step 5: Test Deployment

```bash
# Get your service URL
SERVICE_URL=$(gcloud run services describe ecommerce-agent --region us-central1 --format='value(status.url)')

# Test health endpoint
curl $SERVICE_URL/

# Test stats endpoint
curl $SERVICE_URL/stats

# Test chat endpoint
curl -X POST $SERVICE_URL/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "show me running shoes"}'
```

### Step 6: Access Frontend

Your frontend will be served at: `https://ecommerce-agent-abc123-uc.a.run.app`

Open in browser and start chatting!

### Cost Optimization for Cloud Run

```bash
# For lower costs, reduce resources:
gcloud run services update ecommerce-agent \
  --region us-central1 \
  --memory 1Gi \
  --cpu 1 \
  --max-instances 5 \
  --min-instances 0  # Scale to zero when not in use
```

---

## 🖥️ Option 2: Compute Engine (VM)

**Best for**: Full control, running 24/7, multiple services

### Step 1: Create VM Instance

```bash
# Create a VM with Docker pre-installed
gcloud compute instances create ecommerce-agent-vm \
  --zone=us-central1-a \
  --machine-type=e2-medium \
  --image-family=cos-stable \
  --image-project=cos-cloud \
  --boot-disk-size=20GB \
  --tags=http-server,https-server

# Allow HTTP/HTTPS traffic
gcloud compute firewall-rules create allow-http \
  --allow tcp:80,tcp:443,tcp:8001 \
  --target-tags http-server

# SSH into the VM
gcloud compute ssh ecommerce-agent-vm --zone=us-central1-a
```

### Step 2: Setup on VM

```bash
# Once SSH'd into the VM:

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Clone your repository
git clone https://github.com/yourusername/ecommerce_agent.git
cd ecommerce_agent

# Create .env file
cat > .env << EOF
GOOGLE_API_KEY=your_gemini_api_key_here
ENABLE_RATE_LIMITING=true
MAX_REQUESTS_PER_MINUTE=10
MAX_REQUESTS_PER_HOUR=100
MAX_REQUESTS_PER_DAY=500
MAX_DAILY_API_CALLS=1000
EOF

# Start services
docker-compose up -d

# Check logs
docker-compose logs -f
```

### Step 3: Get External IP

```bash
# Get external IP
gcloud compute instances describe ecommerce-agent-vm \
  --zone=us-central1-a \
  --format='get(networkInterfaces[0].accessConfigs[0].natIP)'

# Access your app at: http://EXTERNAL_IP:8001
```

### Step 4: Setup Domain (Optional)

```bash
# Reserve static IP
gcloud compute addresses create ecommerce-agent-ip --region=us-central1

# Get the IP
gcloud compute addresses describe ecommerce-agent-ip --region=us-central1

# Point your domain to this IP in your DNS provider
# Then setup Nginx or Caddy for HTTPS
```

---

## 🔒 Security Best Practices

### 1. Use Secret Manager (Recommended)

Instead of passing API keys directly:

```bash
# Enable Secret Manager API
gcloud services enable secretmanager.googleapis.com

# Create secret
echo -n "your_gemini_api_key" | gcloud secrets create gemini-api-key --data-file=-

# Grant Cloud Run access to secret
gcloud secrets add-iam-policy-binding gemini-api-key \
  --member=serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com \
  --role=roles/secretmanager.secretAccessor

# Deploy with secret
gcloud run deploy ecommerce-agent \
  --image gcr.io/PROJECT_ID/ecommerce-agent \
  --update-secrets GOOGLE_API_KEY=gemini-api-key:latest
```

### 2. Restrict Access (Optional)

```bash
# Deploy without public access
gcloud run deploy ecommerce-agent \
  --no-allow-unauthenticated

# Only allow specific users
gcloud run services add-iam-policy-binding ecommerce-agent \
  --member="user:your-email@gmail.com" \
  --role="roles/run.invoker"
```

---

## 📊 Monitoring & Logging

### View Logs

```bash
# Cloud Run logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=ecommerce-agent" \
  --limit 50 \
  --format json

# Or use Cloud Console:
# https://console.cloud.google.com/logs
```

### Setup Monitoring

1. Go to **Cloud Console** → **Monitoring**
2. Create dashboard for:
   - Request count
   - Response time
   - Error rate
   - Memory usage
   - CPU usage

### Setup Alerts

```bash
# Create alert for high error rate
gcloud alpha monitoring policies create \
  --notification-channels=CHANNEL_ID \
  --display-name="High Error Rate" \
  --condition-display-name="Error rate > 5%" \
  --condition-threshold-value=0.05
```

---

## 💰 Cost Estimation

### Cloud Run Pricing (us-central1)

| Resource | Price | Notes |
|----------|-------|-------|
| CPU | $0.00002400 per vCPU-second | Only while processing requests |
| Memory | $0.00000250 per GiB-second | Only while processing requests |
| Requests | $0.40 per million requests | First 2 million free/month |
| Network | $0.12 per GB egress | First 1 GB free/month |

**Example Costs**:
- **Light usage** (1000 requests/day, 500ms avg): ~$2-5/month
- **Medium usage** (5000 requests/day, 500ms avg): ~$10-15/month
- **Heavy usage** (20000 requests/day, 500ms avg): ~$30-50/month

### Compute Engine Pricing (e2-medium)

| Instance Type | vCPUs | Memory | Price/month |
|---------------|-------|--------|-------------|
| e2-micro | 0.25-2 | 1 GB | ~$7 |
| e2-small | 0.5-2 | 2 GB | ~$14 |
| e2-medium | 1-2 | 4 GB | ~$27 |

**Note**: VM runs 24/7, so costs are predictable but higher for low traffic.

---

## 🔄 Continuous Deployment

### Setup Cloud Build Trigger

1. Connect your GitHub repository
2. Create `cloudbuild.yaml`:

```yaml
steps:
  # Build the container image
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/ecommerce-agent', '.']
  
  # Push to Container Registry
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/ecommerce-agent']
  
  # Deploy to Cloud Run
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: gcloud
    args:
      - 'run'
      - 'deploy'
      - 'ecommerce-agent'
      - '--image'
      - 'gcr.io/$PROJECT_ID/ecommerce-agent'
      - '--region'
      - 'us-central1'
      - '--platform'
      - 'managed'

images:
  - 'gcr.io/$PROJECT_ID/ecommerce-agent'
```

3. Push to main branch → Auto-deploy!

---

## 🆘 Troubleshooting

### Container fails to start

```bash
# Check logs
gcloud logging read "resource.type=cloud_run_revision" --limit 100

# Common issues:
# - Missing GOOGLE_API_KEY
# - Database files not in image
# - Port mismatch (Cloud Run expects 8080 by default)
```

### Fix port for Cloud Run

Update `Dockerfile`:
```dockerfile
# Change from:
CMD ["python", "-m", "uvicorn", "backend.gateway.app:app", "--host", "0.0.0.0", "--port", "8001"]

# To:
CMD ["python", "-m", "uvicorn", "backend.gateway.app:app", "--host", "0.0.0.0", "--port", "8080"]
```

Or set PORT env var in Cloud Run:
```bash
gcloud run services update ecommerce-agent --port 8001
```

### High costs

```bash
# Check current spend
gcloud billing accounts list
gcloud billing projects describe PROJECT_ID

# Reduce max instances
gcloud run services update ecommerce-agent --max-instances 3

# Set min instances to 0 (scale to zero)
gcloud run services update ecommerce-agent --min-instances 0
```

---

## 📋 Quick Reference

### Useful Commands

```bash
# View service details
gcloud run services describe ecommerce-agent --region us-central1

# Update environment variable
gcloud run services update ecommerce-agent \
  --update-env-vars MAX_DAILY_API_CALLS=500

# View logs (live)
gcloud logging tail "resource.type=cloud_run_revision"

# Delete service
gcloud run services delete ecommerce-agent --region us-central1

# List all services
gcloud run services list
```

---

## ✅ Deployment Checklist

- [ ] GCP project created
- [ ] Billing enabled
- [ ] **Budget alerts configured** (CRITICAL!)
- [ ] APIs enabled (Cloud Run, Cloud Build)
- [ ] Docker image built and pushed
- [ ] Environment variables set (especially GOOGLE_API_KEY)
- [ ] Service deployed successfully
- [ ] Health check passes (`curl $SERVICE_URL/`)
- [ ] Rate limiting enabled
- [ ] Tested a few queries
- [ ] Monitoring dashboard created
- [ ] Cost alerts configured

---

## 🎉 You're Done!

Your E-commerce AI Agent is now running on Google Cloud Platform!

**Service URL**: Check with `gcloud run services describe ecommerce-agent --region us-central1 --format='value(status.url)'`

**Remember**: Monitor your costs daily for the first week!

