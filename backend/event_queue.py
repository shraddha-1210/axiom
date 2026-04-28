"""
Event-Driven Queue System for Layer 2 Triage

Implements Cloud Pub/Sub integration for asynchronous processing

This module provides:
1. Event publishing when assets are uploaded (Layer 1)
2. Event consumption for Layer 2 triage processing
3. Queue-based routing for scalable processing
4. Fallback to local queue when GCP unavailable
"""

import os
import json
import asyncio
from typing import Dict, Optional, Callable
from datetime import datetime
from queue import Queue
import threading
from threading import Thread

try:
    from google.cloud import pubsub_v1
    HAS_PUBSUB = True
except ImportError:
    HAS_PUBSUB = False


class EventQueue:
    """
    Event queue system for Layer 2 triage processing.
    Uses Cloud Pub/Sub in production, local queue for development.
    """
    
    def __init__(self):
        self.project_id = os.getenv("GCP_PROJECT_ID", "axiom-project")
        self.topic_name = "asset-triage-queue"
        self.subscription_name = "asset-triage-subscription"
        
        # Check if GCP credentials are available
        self.has_gcp_creds = bool(
            os.getenv("GOOGLE_APPLICATION_CREDENTIALS") or 
            os.getenv("GOOGLE_CLOUD_PROJECT")
        )
        
        # Initialize Cloud Pub/Sub or fallback to local queue
        if self.has_gcp_creds and HAS_PUBSUB:
            try:
                self.publisher = pubsub_v1.PublisherClient()
                self.subscriber = pubsub_v1.SubscriberClient()
                
                self.topic_path = self.publisher.topic_path(self.project_id, self.topic_name)
                self.subscription_path = self.subscriber.subscription_path(
                    self.project_id, 
                    self.subscription_name
                )
                self.use_pubsub = True
                print("✓ Using Cloud Pub/Sub for event queue")
                
            except Exception as e:
                print(f"⚠ Cloud Pub/Sub unavailable: {e}")
                self.use_pubsub = False
                self._init_local_queue()
        else:
            self.use_pubsub = False
            self._init_local_queue()
    
    def _init_local_queue(self):
        """Initialize local in-memory queue for development"""
        self.local_queue = Queue()
        self.use_pubsub = False
        self.processing_thread = None
        self.is_processing = False
        print("✓ Using local in-memory queue (development mode)")
    
    # ========================================================================
    # Event Publishing (Layer 1 → Layer 2)
    # ========================================================================
    
    def publish_asset_uploaded_event(
        self, 
        asset_id: str, 
        filepath: str, 
        uploader: str,
        file_hash: str,
        manifest: Dict
    ) -> bool:
        """
        Publishes an event when a new asset is uploaded (Layer 1).
        
        This triggers Layer 2 triage processing.
        
        Args:
            asset_id: Unique asset identifier
            filepath: Path to uploaded file
            uploader: Uploader identifier
            file_hash: SHA-256 hash of file
            manifest: C2PA manifest
        
        Returns:
            True if event published successfully
        """
        event_data = {
            "event_type": "asset.uploaded",
            "timestamp": datetime.utcnow().isoformat(),
            "asset_id": asset_id,
            "filepath": filepath,
            "uploader": uploader,
            "file_hash": file_hash,
            "manifest": manifest
        }
        
        return self._publish_event(event_data)
    
    def publish_triage_complete_event(
        self,
        asset_id: str,
        decision: str,
        hamming_distance: int,
        similarity: float,
        cost: float
    ) -> bool:
        """
        Publishes an event when Layer 2 triage is complete.
        
        Args:
            asset_id: Asset identifier
            decision: Triage decision (BLOCK, ESCALATE_PALIGEMMA, etc.)
            hamming_distance: Calculated Hamming distance
            similarity: Visual similarity percentage
            cost: Processing cost
        
        Returns:
            True if event published successfully
        """
        event_data = {
            "event_type": "triage.complete",
            "timestamp": datetime.utcnow().isoformat(),
            "asset_id": asset_id,
            "decision": decision,
            "hamming_distance": hamming_distance,
            "similarity": similarity,
            "cost": cost
        }
        
        return self._publish_event(event_data)
    
    def publish_paligemma_complete_event(
        self,
        asset_id: str,
        decision: str,
        confidence_score: float,
        cost: float
    ) -> bool:
        """
        Publishes an event when Layer 2.5 PaliGemma analysis is complete.
        
        Args:
            asset_id: Asset identifier
            decision: PaliGemma decision (ESCALATE_LAYER3, ARCHIVE)
            confidence_score: Confidence score (0-100)
            cost: Processing cost
        
        Returns:
            True if event published successfully
        """
        event_data = {
            "event_type": "paligemma.complete",
            "timestamp": datetime.utcnow().isoformat(),
            "asset_id": asset_id,
            "decision": decision,
            "confidence_score": confidence_score,
            "cost": cost
        }
        
        return self._publish_event(event_data)
    
    def publish_scraped_asset_event(
        self,
        asset_id: str,
        source_url: str,
        platform: str,
        filepath: str,
        osint_context: Optional[Dict] = None
    ) -> bool:
        """
        Publishes an event when a new asset is scraped from external sources.
        
        This triggers immediate Layer 2 triage processing.
        
        Args:
            asset_id: Unique identifier for scraped asset
            source_url: URL where asset was found
            platform: Platform name (youtube, reddit, telegram)
            filepath: Path to downloaded file
            osint_context: OSINT metadata (captions, comments, etc.)
        
        Returns:
            True if event published successfully
        """
        event_data = {
            "event_type": "asset.scraped",
            "timestamp": datetime.utcnow().isoformat(),
            "asset_id": asset_id,
            "source_url": source_url,
            "platform": platform,
            "filepath": filepath,
            "osint_context": osint_context or {}
        }
        
        return self._publish_event(event_data)
    
    # ========================================================================
    # Event Publishing Implementation
    # ========================================================================
    
    def _publish_event(self, event_data: Dict) -> bool:
        """
        Publishes event to Cloud Pub/Sub or local queue.
        
        Args:
            event_data: Event payload dictionary
        
        Returns:
            True if published successfully
        """
        try:
            if self.use_pubsub:
                return self._publish_to_pubsub(event_data)
            else:
                return self._publish_to_local_queue(event_data)
        except Exception as e:
            print(f"✗ Error publishing event: {e}")
            return False
    
    def _publish_to_pubsub(self, event_data: Dict) -> bool:
        """Publish event to Cloud Pub/Sub"""
        try:
            # Ensure topic exists
            self._ensure_topic_exists()
            
            # Publish message
            message_data = json.dumps(event_data).encode('utf-8')
            future = self.publisher.publish(self.topic_path, message_data)
            
            # Wait for publish to complete
            message_id = future.result(timeout=10)
            print(f"✓ Published event {event_data['event_type']} (ID: {message_id})")
            return True
            
        except Exception as e:
            print(f"✗ Pub/Sub publish error: {e}")
            return False
    
    def _publish_to_local_queue(self, event_data: Dict) -> bool:
        """Publish event to local in-memory queue"""
        try:
            self.local_queue.put(event_data)
            print(f"✓ Published event {event_data['event_type']} to local queue")
            return True
        except Exception as e:
            print(f"✗ Local queue publish error: {e}")
            return False
    
    def _ensure_topic_exists(self):
        """Ensure Pub/Sub topic exists, create if not"""
        try:
            self.publisher.get_topic(request={"topic": self.topic_path})
        except Exception:
            # Topic doesn't exist, create it
            try:
                self.publisher.create_topic(request={"name": self.topic_path})
                print(f"✓ Created Pub/Sub topic: {self.topic_name}")
            except Exception as e:
                print(f"⚠ Could not create topic: {e}")
    
    # ========================================================================
    # Event Consumption (Layer 2 Processing)
    # ========================================================================
    
    def start_processing(self, callback: Callable[[Dict], None]):
        """
        Start processing events from the queue.
        
        Args:
            callback: Function to call for each event
        """
        if self.use_pubsub:
            self._start_pubsub_processing(callback)
        else:
            self._start_local_processing(callback)
    
    def stop_processing(self):
        """Stop processing events"""
        self.is_processing = False
        if self.processing_thread and self.processing_thread.is_alive():
            self.processing_thread.join(timeout=5)
    
    def _start_pubsub_processing(self, callback: Callable[[Dict], None]):
        """Start processing events from Cloud Pub/Sub"""
        try:
            # Ensure subscription exists
            self._ensure_subscription_exists()
            
            def process_message(message):
                try:
                    event_data = json.loads(message.data.decode('utf-8'))
                    callback(event_data)
                    message.ack()
                except Exception as e:
                    print(f"✗ Error processing message: {e}")
                    message.nack()
            
            # Start pulling messages
            streaming_pull_future = self.subscriber.subscribe(
                self.subscription_path, 
                callback=process_message,
                flow_control=pubsub_v1.types.FlowControl(max_messages=100)
            )
            
            print(f"✓ Started Pub/Sub processing on {self.subscription_name}")
            
            # Keep the main thread running
            try:
                streaming_pull_future.result()
            except KeyboardInterrupt:
                streaming_pull_future.cancel()
                
        except Exception as e:
            print(f"✗ Pub/Sub processing error: {e}")
    
    def _start_local_processing(self, callback: Callable[[Dict], None]):
        """Start processing events from local queue"""
        self.is_processing = True
        
        def process_local_queue():
            while self.is_processing:
                try:
                    # Get event from queue (blocking with timeout)
                    event_data = self.local_queue.get(timeout=1)
                    callback(event_data)
                    self.local_queue.task_done()
                except:
                    # Timeout or queue empty, continue
                    continue
        
        self.processing_thread = Thread(target=process_local_queue, daemon=True)
        self.processing_thread.start()
        print("✓ Started local queue processing")
    
    def _ensure_subscription_exists(self):
        """Ensure Pub/Sub subscription exists, create if not"""
        try:
            self.subscriber.get_subscription(request={"subscription": self.subscription_path})
        except Exception:
            # Subscription doesn't exist, create it
            try:
                self.subscriber.create_subscription(
                    request={
                        "name": self.subscription_path,
                        "topic": self.topic_path,
                        "ack_deadline_seconds": 60
                    }
                )
                print(f"✓ Created Pub/Sub subscription: {self.subscription_name}")
            except Exception as e:
                print(f"⚠ Could not create subscription: {e}")


# ============================================================================
# Event Handlers for Layer 2 Processing
# ============================================================================

class Layer2EventHandler:
    """Handles events for Layer 2 triage processing"""
    
    def __init__(self):
        from triage import run_complete_triage
        from paligemma_triage import run_paligemma_triage
        
        self.run_triage = run_complete_triage
        self.run_paligemma = run_paligemma_triage
        self.event_queue = EventQueue()
    
    def handle_event(self, event_data: Dict):
        """
        Main event handler that routes events to appropriate processors.
        
        Args:
            event_data: Event payload dictionary
        """
        event_type = event_data.get("event_type")
        
        try:
            if event_type == "asset.uploaded":
                self._handle_asset_uploaded(event_data)
            elif event_type == "asset.scraped":
                self._handle_asset_scraped(event_data)
            elif event_type == "triage.complete":
                self._handle_triage_complete(event_data)
            elif event_type == "paligemma.complete":
                self._handle_paligemma_complete(event_data)
            else:
                print(f"⚠ Unknown event type: {event_type}")
                
        except Exception as e:
            print(f"✗ Error handling event {event_type}: {e}")
    
    def _handle_asset_uploaded(self, event_data: Dict):
        """Handle asset.uploaded event (Layer 1 → Layer 2)"""
        asset_id = event_data["asset_id"]
        filepath = event_data["filepath"]
        
        print(f"\n[Event] Processing uploaded asset: {asset_id}")
        
        # Register asset hashes in Redis for future comparisons
        from triage import extract_keyframes, compute_phash_for_frames, store_asset_hashes
        
        frame_dir = f"/tmp/media/frames_{asset_id}"
        frames = extract_keyframes(filepath, frame_dir)
        
        if frames:
            hashes = compute_phash_for_frames(frames)
            if hashes and len(hashes) > 0:
                dhash = hashes[0].get("dhash")
                ahash = hashes[0].get("ahash")
                
                if dhash and ahash:
                    store_asset_hashes(asset_id, dhash, ahash)
                    print(f"✓ Registered asset {asset_id} hashes for Layer 2 comparison")
    
    def _handle_asset_scraped(self, event_data: Dict):
        """Handle asset.scraped event (External → Layer 2)"""
        asset_id = event_data["asset_id"]
        filepath = event_data["filepath"]
        osint_context = event_data.get("osint_context", {})
        
        print(f"\n[Event] Processing scraped asset: {asset_id}")
        
        # Run Layer 2 triage
        triage_result = self.run_triage(filepath, asset_id)
        
        # Publish triage complete event
        self.event_queue.publish_triage_complete_event(
            asset_id=asset_id,
            decision=triage_result.decision.value,
            hamming_distance=triage_result.hamming_distance,
            similarity=triage_result.visual_similarity,
            cost=triage_result.cost
        )
        
        print(f"✓ Layer 2 triage complete: {triage_result.decision.value}")
    
    def _handle_triage_complete(self, event_data: Dict):
        """Handle triage.complete event (Layer 2 → Layer 2.5 or Layer 3)"""
        asset_id = event_data["asset_id"]
        decision = event_data["decision"]
        
        if decision == "ESCALATE_PALIGEMMA":
            print(f"\n[Event] Escalating {asset_id} to Layer 2.5 PaliGemma")
            
            # Get frames for PaliGemma analysis
            frame_dir = f"/tmp/media/frames_{asset_id}"
            if os.path.exists(frame_dir):
                frame_paths = sorted([
                    os.path.join(frame_dir, f) 
                    for f in os.listdir(frame_dir) 
                    if f.endswith('.jpg')
                ])
                
                if frame_paths:
                    # Run PaliGemma analysis
                    pali_result = self.run_paligemma(frame_paths)
                    
                    # Publish PaliGemma complete event
                    self.event_queue.publish_paligemma_complete_event(
                        asset_id=asset_id,
                        decision=pali_result.decision.value,
                        confidence_score=pali_result.confidence_score,
                        cost=pali_result.cost
                    )
                    
                    print(f"✓ Layer 2.5 PaliGemma complete: {pali_result.decision.value}")
        
        elif decision == "ESCALATE_VERTEX":
            print(f"\n[Event] Escalating {asset_id} directly to Layer 3 Gemini")
            filepath = event_data.get("filepath", "")
            if filepath and os.path.exists(filepath):
                try:
                    from layer3_orchestrator import run_layer3_interrogation
                    triage_ctx = {
                        "hamming_distance": event_data.get("hamming_distance", 64),
                        "visual_similarity": event_data.get("similarity", 0.0),
                        "audio_match": False,
                        "osint_piracy_intent": 0.0,
                        "platform": event_data.get("platform", "unknown"),
                    }
                    result = run_layer3_interrogation(filepath, asset_id, triage_context=triage_ctx)
                    print(f"✓ Layer 3 complete: {result.classification} (action={result.recommended_action})")
                except Exception as exc:
                    print(f"✗ Layer 3 escalation failed for {asset_id}: {exc}")
            else:
                print(f"⚠ filepath missing or not found for {asset_id}, skipping Layer 3")
            
        elif decision == "BLOCK":
            print(f"\n[Event] Asset {asset_id} BLOCKED - automated takedown initiated")
            # This would trigger automated takedown
            
        elif decision == "DISCARD":
            print(f"\n[Event] Asset {asset_id} DISCARDED - archived as unrelated")
    
    def _handle_paligemma_complete(self, event_data: Dict):
        """Handle paligemma.complete event (Layer 2.5 → Layer 3 or Archive)"""
        asset_id = event_data["asset_id"]
        decision = event_data["decision"]
        confidence_score = event_data["confidence_score"]

        if decision == "ESCALATE_LAYER3":
            print(f"\n[Event] Escalating {asset_id} to Layer 3 Gemini (confidence: {confidence_score})")
            filepath = event_data.get("filepath", "")
            if filepath and os.path.exists(filepath):
                try:
                    from layer3_orchestrator import run_layer3_interrogation
                    triage_ctx = {
                        "hamming_distance": event_data.get("hamming_distance", 64),
                        "visual_similarity": event_data.get("visual_similarity", 0.0),
                        "audio_match": event_data.get("audio_match", False),
                        "osint_piracy_intent": event_data.get("osint_piracy_intent", 0.0),
                        "platform": event_data.get("platform", "unknown"),
                        "osint_caption": event_data.get("osint_caption", ""),
                        "paligemma_confidence": confidence_score,
                    }
                    result = run_layer3_interrogation(filepath, asset_id, triage_context=triage_ctx)
                    print(f"✓ Layer 3 complete: {result.classification} (action={result.recommended_action})")
                except Exception as exc:
                    print(f"✗ Layer 3 escalation failed for {asset_id}: {exc}")
            else:
                print(f"⚠ filepath missing or not found for {asset_id}, skipping Layer 3")

        elif decision == "ARCHIVE":
            print(f"\n[Event] Asset {asset_id} ARCHIVED - low confidence score ({confidence_score})")


# ============================================================================
# Global Event Queue Instance
# ============================================================================

# Global event queue instance for use across the application
event_queue = EventQueue()
layer2_handler = Layer2EventHandler()

def start_event_processing():
    """Start processing events in the background"""
    event_queue.start_processing(layer2_handler.handle_event)

def stop_event_processing():
    """Stop processing events"""
    event_queue.stop_processing()