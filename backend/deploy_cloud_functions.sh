#!/bin/bash

# Deployment script for Cloud Functions Gen 2 (Layer 2 event processing)

set -e

PROJECT_ID=${GCP_PROJECT_ID:-"axiom-project"}
REGION=${GCP_REGION:-"us-central1"}

echo "Deploying Layer 2 Cloud Functions to project: $PROJECT_ID"

# Deploy Layer 2 Triage Function
echo "Deploying layer2-triage-processor..."
gcloud functions deploy layer2-triage-processor \
    --gen2 \
    --runtime=python311 \
    --region=$REGION \
    --source=. \
    --entry-point=layer2_triage_trigger \
    --trigger-topic=asset-triage-queue \
    --memory=1Gi \
    --timeout=540s \
    --max-instances=100 \
    --set-env-vars="ENVIRONMENT=production" \
    --project=$PROJECT_ID

# Deploy Layer 2.5 PaliGemma Function
echo "Deploying layer25-paligemma-processor..."
gcloud functions deploy layer25-paligemma-processor \
    --gen2 \
    --runtime=python311 \
    --region=$REGION \
    --source=. \
    --entry-point=layer25_paligemma_trigger \
    --trigger-topic=paligemma-triage-queue \
    --memory=2Gi \
    --timeout=540s \
    --max-instances=50 \
    --set-env-vars="ENVIRONMENT=production" \
    --project=$PROJECT_ID

echo "Cloud Functions deployed successfully!"

# Create Pub/Sub topics if they don't exist
echo "Creating Pub/Sub topics..."
gcloud pubsub topics create asset-triage-queue --project=$PROJECT_ID || echo "Topic asset-triage-queue already exists"
gcloud pubsub topics create paligemma-triage-queue --project=$PROJECT_ID || echo "Topic paligemma-triage-queue already exists"

# Create subscriptions
echo "Creating Pub/Sub subscriptions..."
gcloud pubsub subscriptions create asset-triage-subscription \
    --topic=asset-triage-queue \
    --project=$PROJECT_ID || echo "Subscription asset-triage-subscription already exists"

gcloud pubsub subscriptions create paligemma-triage-subscription \
    --topic=paligemma-triage-queue \
    --project=$PROJECT_ID || echo "Subscription paligemma-triage-subscription already exists"

echo "Deployment complete!"
echo ""
echo "Functions deployed:"
echo "- layer2-triage-processor (triggered by asset-triage-queue)"
echo "- layer25-paligemma-processor (triggered by paligemma-triage-queue)"
echo ""
echo "Test with:"
echo "gcloud pubsub topics publish asset-triage-queue --message='{\"event_type\":\"asset.scraped\",\"asset_id\":\"test\"}'"