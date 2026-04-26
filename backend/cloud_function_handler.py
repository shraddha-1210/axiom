"""
Cloud Functions Gen 2 / Cloud Run Handler for Layer 2 Event Processing

This module implements the event-driven mechanism mentioned in the Layer 2 specification.
It listens to Cloud Pub/Sub events and triggers Layer 2 triage processing.

Deployment:
- Cloud Functions Gen 2: Serverless event processing
- Cloud Run: Containerized event processing with more control
- Both listen to the asset-triage-queue Pub/Sub topic
"""

import os
import json
import base64
from typing import Dict, Any
from flask import Flask, request, jsonify

# Import Layer 2 processing modules
from triage import run_complete_triage, TriageDecision
from paligemma_triage import run_paligemma_triage, PaliGemmaDecision
from event_queue import event_queue

# Initialize Flask app for Cloud Run
app = Flask(__name__)


# ============================================================================
# Cloud Functions Gen 2 Entry Points
# ============================================================================

def layer2_triage_trigger(cloud_event):
    """
    Cloud Functions Gen 2 entry point for Layer 2 triage processing.
    
    Triggered by Cloud Pub/Sub messages on the asset-triage-queue topic.
    
    Args:
        cloud_event: CloudEvent containing Pub/Sub message
    """
    try:
        # Decode Pub/Sub message
        message_data = base64.b64decode(cloud_event.data["message"]["data"])
        event_data = json.loads(message_data.decode('utf-8'))
        
        print(f"[Cloud Function] Processing event: {event_data.get('event_type')}")
        
        # Route event to appropriate handler
        result = process_layer2_event(event_data)
        
        print(f"[Cloud Function] Event processed successfully: {result}")
        return result
        
    except Exception as e:
        print(f"[Cloud Function] Error processing event: {e}")
        raise e


def layer25_paligemma_trigger(cloud_event):
    """
    Cloud Functions Gen 2 entry point for Layer 2.5 PaliGemma processing.
    
    Triggered by triage.complete events with ESCALATE_PALIGEMMA decision.
    
    Args:
        cloud_event: CloudEvent containing Pub/Sub message
    """
    try:
        # Decode Pub/Sub message
        message_data = base64.b64decode(cloud_event.data["message"]["data"])
        event_data = json.loads(message_data.decode('utf-8'))
        
        print(f"[Cloud Function] Processing PaliGemma event: {event_data.get('asset_id')}")
        
        # Process PaliGemma analysis
        result = process_paligemma_event(event_data)
        
        print(f"[Cloud Function] PaliGemma processed successfully: {result}")
        return result
        
    except Exception as e:
        print(f"[Cloud Function] Error processing PaliGemma event: {e}")
        raise e


# ============================================================================
# Cloud Run HTTP Endpoints
# ============================================================================

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for Cloud Run"""
    return jsonify({
        "status": "healthy",
        "service": "layer2-event-processor",
        "version": "1.0.0"
    })


@app.route('/process-event', methods=['POST'])
def process_event_http():
    """
    HTTP endpoint for processing Layer 2 events (Cloud Run).
    
    Accepts Pub/Sub push messages or direct HTTP calls.
    """
    try:
        # Handle Pub/Sub push message format
        if request.headers.get('ce-type') == 'google.cloud.pubsub.topic.v1.messagePublished':
            # Cloud Event format
            message_data = request.json.get('message', {}).get('data', '')
            event_data = json.loads(base64.b64decode(message_data).decode('utf-8'))
        else:
            # Direct HTTP call
            event_data = request.json
        
        print(f"[Cloud Run] Processing event: {event_data.get('event_type')}")
        
        # Process event
        result = process_layer2_event(event_data)
        
        return jsonify({
            "status": "success",
            "result": result
        })
        
    except Exception as e:
        print(f"[Cloud Run] Error processing event: {e}")
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500


@app.route('/process-paligemma', methods=['POST'])
def process_paligemma_http():
    """
    HTTP endpoint for processing Layer 2.5 PaliGemma events (Cloud Run).
    """
    try:
        # Handle Pub/Sub push message format
        if request.headers.get('ce-type') == 'google.cloud.pubsub.topic.v1.messagePublished':
            message_data = request.json.get('message', {}).get('data', '')
            event_data = json.loads(base64.b64decode(message_data).decode('utf-8'))
        else:
            event_data = request.json
        
        print(f"[Cloud Run] Processing PaliGemma event: {event_data.get('asset_id')}")
        
        # Process PaliGemma event
        result = process_paligemma_event(event_data)
        
        return jsonify({
            "status": "success",
            "result": result
        })
        
    except Exception as e:
        print(f"[Cloud Run] Error processing PaliGemma event: {e}")
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500


# ============================================================================
# Event Processing Logic
# ============================================================================

def process_layer2_event(event_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process Layer 2 events (asset uploads, scraped content).
    
    Args:
        event_data: Event payload dictionary
    
    Returns:
        Processing result dictionary
    """
    event_type = event_data.get("event_type")
    asset_id = event_data.get("asset_id")
    
    if event_type == "asset.uploaded":
        return process_asset_uploaded(event_data)
    elif event_type == "asset.scraped":
        return process_asset_scraped(event_data)
    else:
        raise ValueError(f"Unknown event type: {event_type}")


def process_asset_uploaded(event_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process asset.uploaded event (Layer 1 → Layer 2).
    
    Registers asset hashes in Redis for future comparison.
    
    Args:
        event_data: Event payload with asset details
    
    Returns:
        Processing result
    """
    asset_id = event_data["asset_id"]
    filepath = event_data["filepath"]
    
    print(f"[Layer 2] Registering uploaded asset: {asset_id}")
    
    # This is already handled in the main API, but we can add additional processing here
    # For example, triggering additional background tasks
    
    return {
        "action": "registered",
        "asset_id": asset_id,
        "message": f"Asset {asset_id} registered for Layer 2 comparison"
    }


def process_asset_scraped(event_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process asset.scraped event (External sources → Layer 2).
    
    Runs complete Layer 2 triage pipeline.
    
    Args:
        event_data: Event payload with scraped asset details
    
    Returns:
        Triage result
    """
    asset_id = event_data["asset_id"]
    filepath = event_data["filepath"]
    osint_context = event_data.get("osint_context", {})
    
    print(f"[Layer 2] Running triage on scraped asset: {asset_id}")
    
    # Run Layer 2 triage
    triage_result = run_complete_triage(filepath, asset_id)
    
    # Publish triage complete event
    event_queue.publish_triage_complete_event(
        asset_id=asset_id,
        decision=triage_result.decision.value,
        hamming_distance=triage_result.hamming_distance,
        similarity=triage_result.visual_similarity,
        cost=triage_result.cost
    )
    
    # Handle routing based on decision
    if triage_result.decision == TriageDecision.BLOCK:
        # Trigger automated takedown
        trigger_automated_takedown(asset_id, triage_result)
        
    elif triage_result.decision == TriageDecision.ESCALATE_PALIGEMMA:
        # Will be handled by PaliGemma event processor
        print(f"[Layer 2] Escalating {asset_id} to Layer 2.5 PaliGemma")
        
    elif triage_result.decision == TriageDecision.ESCALATE_VERTEX:
        # Trigger Layer 3 processing
        trigger_layer3_processing(asset_id, triage_result, osint_context)
        
    elif triage_result.decision == TriageDecision.DISCARD:
        # Archive as unrelated
        archive_asset(asset_id, "unrelated_content")
    
    return {
        "action": "triage_complete",
        "asset_id": asset_id,
        "decision": triage_result.decision.value,
        "hamming_distance": triage_result.hamming_distance,
        "similarity": triage_result.visual_similarity,
        "cost": triage_result.cost
    }


def process_paligemma_event(event_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process Layer 2.5 PaliGemma analysis event.
    
    Args:
        event_data: Event payload with triage results
    
    Returns:
        PaliGemma analysis result
    """
    asset_id = event_data["asset_id"]
    
    print(f"[Layer 2.5] Running PaliGemma analysis on: {asset_id}")
    
    # Get frames for analysis
    frame_dir = f"/tmp/media/frames_{asset_id}"
    if not os.path.exists(frame_dir):
        raise FileNotFoundError(f"Frames not found for asset {asset_id}")
    
    frame_paths = sorted([
        os.path.join(frame_dir, f) 
        for f in os.listdir(frame_dir) 
        if f.endswith('.jpg')
    ])
    
    if not frame_paths:
        raise ValueError(f"No frames found for asset {asset_id}")
    
    # Run PaliGemma analysis
    pali_result = run_paligemma_triage(frame_paths)
    
    # Publish PaliGemma complete event
    event_queue.publish_paligemma_complete_event(
        asset_id=asset_id,
        decision=pali_result.decision.value,
        confidence_score=pali_result.confidence_score,
        cost=pali_result.cost
    )
    
    # Handle escalation decision
    if pali_result.decision == PaliGemmaDecision.ESCALATE_LAYER3:
        # Trigger Layer 3 processing
        trigger_layer3_processing(asset_id, pali_result)
    else:
        # Archive as low-risk
        archive_asset(asset_id, "low_confidence")
    
    return {
        "action": "paligemma_complete",
        "asset_id": asset_id,
        "decision": pali_result.decision.value,
        "confidence_score": pali_result.confidence_score,
        "cost": pali_result.cost
    }


# ============================================================================
# Action Handlers
# ============================================================================

def trigger_automated_takedown(asset_id: str, triage_result) -> None:
    """
    Trigger automated takedown for blocked assets.
    
    Args:
        asset_id: Asset identifier
        triage_result: Layer 2 triage result
    """
    print(f"[Action] Triggering automated takedown for asset {asset_id}")
    
    # In production, this would:
    # 1. Generate DMCA takedown notice
    # 2. Submit to platform APIs (YouTube, Reddit, etc.)
    # 3. Alert SOC team
    # 4. Log incident in database
    
    # For now, just log the action
    print(f"✓ Automated takedown initiated for {asset_id} (Hamming: {triage_result.hamming_distance})")


def trigger_layer3_processing(asset_id: str, analysis_result, osint_context: Dict = None) -> None:
    """
    Trigger Layer 3 Gemini processing.
    
    Args:
        asset_id: Asset identifier
        analysis_result: Layer 2 or 2.5 analysis result
        osint_context: Optional OSINT context
    """
    print(f"[Action] Triggering Layer 3 Gemini processing for asset {asset_id}")
    
    # In production, this would publish an event to trigger Layer 3
    # For now, we can call the interrogation directly
    
    try:
        from gemini_interrogator import analyze_video_frames_for_fraud
        
        context = ""
        if osint_context:
            context = osint_context.get("caption", "")
        
        gemini_result = analyze_video_frames_for_fraud([], source_context=context)
        
        # Log incident in database
        from database import SessionLocal, IncidentRecord
        
        db = SessionLocal()
        try:
            incident = IncidentRecord(
                incident_id=f"inc_{os.urandom(4).hex()}",
                asset_id=asset_id,
                classification=gemini_result.get("classification", "UNKNOWN"),
                confidence=str(gemini_result.get("confidence", "0.0")),
                gemini_report=gemini_result,
                action_taken=gemini_result.get("recommended_action", "REVIEW")
            )
            db.add(incident)
            db.commit()
            print(f"✓ Layer 3 incident logged for {asset_id}")
        except Exception as e:
            print(f"✗ Error logging incident: {e}")
            db.rollback()
        finally:
            db.close()
            
    except Exception as e:
        print(f"✗ Error in Layer 3 processing: {e}")


def archive_asset(asset_id: str, reason: str) -> None:
    """
    Archive asset with specified reason.
    
    Args:
        asset_id: Asset identifier
        reason: Archival reason
    """
    print(f"[Action] Archiving asset {asset_id} (reason: {reason})")
    
    # In production, this would:
    # 1. Move asset to archive storage
    # 2. Update database status
    # 3. Clean up temporary files
    
    print(f"✓ Asset {asset_id} archived")


# ============================================================================
# Cloud Run Entry Point
# ============================================================================

if __name__ == '__main__':
    # For local development
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=True)