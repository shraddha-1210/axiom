import os
from google.cloud import storage, pubsub_v1, kms

# Initialize clients if GOOGLE_APPLICATION_CREDENTIALS is provided
has_gcp_creds = os.getenv("GOOGLE_APPLICATION_CREDENTIALS") and os.path.exists(os.getenv("GOOGLE_APPLICATION_CREDENTIALS"))

storage_client = storage.Client() if has_gcp_creds else None
pubsub_publisher = pubsub_v1.PublisherClient() if has_gcp_creds else None
pubsub_subscriber = pubsub_v1.SubscriberClient() if has_gcp_creds else None
kms_client = kms.KeyManagementServiceClient() if has_gcp_creds else None

# Example helper functions
def verify_gcp_setup():
    """Check which GCP services are successfully connected."""
    return {
        "credentials_loaded": has_gcp_creds,
        "cloud_storage": storage_client is not None,
        "pubsub": pubsub_publisher is not None,
        "kms": kms_client is not None
    }
