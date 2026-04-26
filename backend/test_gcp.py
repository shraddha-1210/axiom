import os
import sys
from gcp_services import verify_gcp_setup, storage_client, kms_client

def main():
    print("Beginning GCP Service Verification...")
    status = verify_gcp_setup()
    
    print("\n--- Connection Status ---")
    for service, is_connected in status.items():
        print(f"{service:20}: {'SUCCESS' if is_connected else 'FAILED'}")
    
    if not status["credentials_loaded"]:
        print("\nERROR: GOOGLE_APPLICATION_CREDENTIALS not loaded or file missing.")
        sys.exit(1)
        
    print("\nTesting Cloud Storage...")
    try:
        # Just listing buckets to verify IAM permissions
        buckets = list(storage_client.list_buckets(max_results=1))
        print("Cloud Storage OK: Verified list_buckets permission.")
    except Exception as e:
        print(f"Cloud Storage Exception: {e}")

    print("\nTesting Cloud KMS...")
    try:
        # Just an empty list call to verify IAM permissions
        # Requires project ID from env or credentials
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "axiom-494419") # default to the one from user's shell
        parent = f"projects/{project_id}/locations/global"
        list(kms_client.list_key_rings(request={"parent": parent}))
        print("Cloud KMS OK: Verified list_key_rings permission.")
    except Exception as e:
        print(f"Cloud KMS Exception: {e}")

if __name__ == "__main__":
    main()
