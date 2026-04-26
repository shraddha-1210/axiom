#!/bin/bash

# Deployment script for Cloud Run (Layer 2 event processing)

set -e

PROJECT_ID=${GCP_PROJECT_ID:-"axiom-project"}
REGION=${GCP_REGION:-"us-central1"}
SERVICE_NAME="layer2-event-processor"

echo "Deploying Layer 2 Event Processor to Cloud Run..."

# Build and push container image
echo "Building container image..."
gcloud builds submit --tag gcr.io/$PROJECT_ID/$SERVICE_NAME \
    --file=Dockerfile.cloudrun \
    --project=$PROJECT_ID

# Deploy to Cloud Run
echo "Deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
    --image gcr.io/$PROJECT_ID/$SERVICE_NAME \
    --platform managed \
    --region $REGION \
    --allow-unauthenticated \
    --memory 2Gi \
    --cpu 2 \
    --timeout 900 \
    --max-instances 100 \
    --set-env-vars="ENVIRONMENT=production,GCP_PROJECT_ID=$PROJECT_ID" \
    --project=$PROJECT_ID

# Get service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME \
    --platform managed \
    --region $REGION \
    --format 'value(status.url)' \
    --project=$PROJECT_ID)

echo "Cloud Run service deployed successfully!"
echo "Service URL: $SERVICE_URL"

# Create Pub/Sub push subscriptions to Cloud Run
echo "Creating Pub/Sub push subscriptions..."

# Create topics if they don't exist
gcloud pubsub topics create asset-triage-queue --project=$PROJECT_ID || echo "Topic already exists"
gcloud pubsub topics create paligemma-triage-queue --project=$PROJECT_ID || echo "Topic already exists"

# Create push subscriptions
gcloud pubsub subscriptions create asset-triage-cloudrun \
    --topic=asset-triage-queue \
    --push-endpoint="$SERVICE_URL/process-event" \
    --project=$PROJECT_ID || echo "Subscription already exists"

gcloud pubsub subscriptions create paligemma-triage-cloudrun \
    --topic=paligemma-triage-queue \
    --push-endpoint="$SERVICE_URL/process-paligemma" \
    --project=$PROJECT_ID || echo "Subscription already exists"

echo "Deployment complete!"
echo ""
echo "Cloud Run service: $SERVICE_URL"
echo "Endpoints:"
echo "- GET  $SERVICE_URL/health"
echo "- POST $SERVICE_URL/process-event"
echo "- POST $SERVICE_URL/process-paligemma"
echo ""
echo "Test with:"
echo "curl -X POST $SERVICE_URL/process-event -H 'Content-Type: application/json' -d '{\"event_type\":\"asset.scraped\",\"asset_id\":\"test\"}'"