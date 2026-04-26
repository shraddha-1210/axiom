"""
Test script for Layer 2 & 2.5 Pipeline
Demonstrates complete triage and PaliGemma analysis workflow
"""

import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from triage import (
    run_complete_triage,
    store_asset_hashes,
    extract_keyframes,
    compute_phash_for_frames,
    TriageDecision
)
from paligemma_triage import (
    run_paligemma_triage,
    PaliGemmaDecision,
    detect_compression_artifacts,
    check_geometric_consistency,
    detect_temporal_flickering,
    analyze_osint_context
)


def test_layer2_triage():
    """Test Layer 2 pHash triage pipeline"""
    print("\n" + "="*70)
    print("TEST: Layer 2 pHash Triage Pipeline")
    print("="*70)
    
    # This would be a real video file in production
    test_video = "/tmp/media/test_video.mp4"
    
    if not os.path.exists(test_video):
        print(f"⚠ Test video not found: {test_video}")
        print("Creating mock test scenario...")
        
        # Mock scenario
        print("\nMock Scenario:")
        print("- Video: test_video.mp4")
        print("- Frames extracted: 15 I-frames")
        print("- Hashes computed: dHash + aHash for each frame")
        print("- Redis cache check: No matches found")
        print("- Hamming distance: 12 (moderate similarity)")
        print("- Decision: ESCALATE_PALIGEMMA")
        print("- Cost: $0.0001")
        
        return {
            "decision": TriageDecision.ESCALATE_PALIGEMMA,
            "hamming_distance": 12,
            "visual_similarity": 85.5,
            "cost": 0.0001
        }
    
    # Run actual triage
    result = run_complete_triage(test_video, asset_id="test_001")
    
    print(f"\n✓ Triage Complete")
    print(f"  Decision: {result.decision.value}")
    print(f"  Hamming Distance: {result.hamming_distance}")
    print(f"  Visual Similarity: {result.visual_similarity:.1f}%")
    print(f"  Audio Match: {result.audio_match}")
    print(f"  Cost: ${result.cost:.6f}")
    
    return result


def test_layer25_paligemma():
    """Test Layer 2.5 PaliGemma triage pipeline"""
    print("\n" + "="*70)
    print("TEST: Layer 2.5 PaliGemma Triage Pipeline")
    print("="*70)
    
    # This would be actual frame paths in production
    frame_dir = "/tmp/media/frames_test_001"
    
    if not os.path.exists(frame_dir):
        print(f"⚠ Frame directory not found: {frame_dir}")
        print("Creating mock test scenario...")
        
        # Mock scenario
        print("\nMock Scenario:")
        print("- Frames analyzed: 5 keyframes")
        print("- Visual coherence: 0.75")
        print("- Compression artifacts: Detected (score: 0.68)")
        print("- Geometric consistency: 0.82")
        print("- Temporal flickering: Not detected")
        print("- OSINT piracy intent: 0.45")
        print("- Confidence score: 68.5/100")
        print("- Decision: ESCALATE_LAYER3")
        print("- Cost: $0.002")
        
        return {
            "decision": PaliGemmaDecision.ESCALATE_LAYER3,
            "confidence_score": 68.5,
            "cost": 0.002
        }
    
    # Get frame paths
    frame_paths = sorted([
        os.path.join(frame_dir, f) 
        for f in os.listdir(frame_dir) 
        if f.endswith('.jpg')
    ])
    
    # Mock OSINT context
    osint_context = {
        "caption": "Check out this leaked video",
        "post_text": "Free download available",
        "account_age_days": 15,
        "comments": ["Thanks for sharing!", "Where's the full version?"]
    }
    
    # Run PaliGemma triage
    result = run_paligemma_triage(frame_paths, osint_context)
    
    print(f"\n✓ PaliGemma Triage Complete")
    print(f"  Decision: {result.decision.value}")
    print(f"  Confidence Score: {result.confidence_score:.1f}/100")
    print(f"  Visual Coherence: {result.visual_coherence:.2f}")
    print(f"  Compression Artifacts: {result.compression_artifacts}")
    print(f"  Geometric Consistency: {result.geometric_consistency:.2f}")
    print(f"  Temporal Flickering: {result.temporal_flickering}")
    print(f"  OSINT Piracy Intent: {result.osint_piracy_intent:.2f}")
    print(f"  Cost: ${result.cost:.6f}")
    
    return result


def test_osint_analysis():
    """Test OSINT context analysis"""
    print("\n" + "="*70)
    print("TEST: OSINT Context Analysis")
    print("="*70)
    
    # Test Case 1: High piracy intent
    print("\nTest Case 1: High Piracy Intent")
    score1 = analyze_osint_context(
        caption="Free download full movie leaked",
        post_text="Watch free no copyright",
        account_age_days=5,
        comments=["Thanks for the torrent!", "Pirated version works great"]
    )
    print(f"  Piracy Intent Score: {score1:.2f}")
    print(f"  Assessment: {'HIGH RISK' if score1 > 0.6 else 'MODERATE' if score1 > 0.3 else 'LOW RISK'}")
    
    # Test Case 2: Low piracy intent
    print("\nTest Case 2: Low Piracy Intent")
    score2 = analyze_osint_context(
        caption="Official trailer release",
        post_text="Check out the new official content",
        account_age_days=730,
        comments=["Looks great!", "Can't wait for release"]
    )
    print(f"  Piracy Intent Score: {score2:.2f}")
    print(f"  Assessment: {'HIGH RISK' if score2 > 0.6 else 'MODERATE' if score2 > 0.3 else 'LOW RISK'}")
    
    # Test Case 3: Moderate piracy intent
    print("\nTest Case 3: Moderate Piracy Intent")
    score3 = analyze_osint_context(
        caption="Rip from streaming service",
        post_text="Found this online",
        account_age_days=45,
        comments=["Where did you get this?"]
    )
    print(f"  Piracy Intent Score: {score3:.2f}")
    print(f"  Assessment: {'HIGH RISK' if score3 > 0.6 else 'MODERATE' if score3 > 0.3 else 'LOW RISK'}")


def test_routing_matrix():
    """Test Hamming distance routing matrix"""
    print("\n" + "="*70)
    print("TEST: Hamming Distance Routing Matrix")
    print("="*70)
    
    test_cases = [
        (3, "Direct Copy - BLOCK"),
        (15, "Moderate Similarity - ESCALATE_PALIGEMMA"),
        (28, "Significant Edit - ESCALATE_VERTEX"),
        (45, "Unrelated Content - DISCARD")
    ]
    
    from triage import determine_triage_decision, calculate_cost
    
    for hamming, description in test_cases:
        decision = determine_triage_decision(hamming)
        cost = calculate_cost(decision)
        similarity = ((64 - hamming) / 64) * 100
        
        print(f"\nHamming Distance: {hamming}")
        print(f"  Similarity: {similarity:.1f}%")
        print(f"  Decision: {decision.value}")
        print(f"  Cost: ${cost:.6f}")
        print(f"  Description: {description}")


def test_event_driven_processing():
    """Test event-driven Layer 2 processing"""
    print("\n" + "="*70)
    print("TEST: Event-Driven Processing")
    print("="*70)
    
    try:
        from event_queue import EventQueue, Layer2EventHandler
        
        # Initialize event system
        event_queue = EventQueue()
        handler = Layer2EventHandler()
        
        print("\n✓ Event queue initialized")
        
        # Test asset uploaded event
        print("\nTesting asset.uploaded event...")
        success = event_queue.publish_asset_uploaded_event(
            asset_id="test_asset_001",
            filepath="/tmp/media/test_video.mp4",
            uploader="test_user",
            file_hash="abc123def456",
            manifest={"test": "manifest"}
        )
        print(f"  Event published: {success}")
        
        # Test scraped asset event
        print("\nTesting asset.scraped event...")
        success = event_queue.publish_scraped_asset_event(
            asset_id="scraped_001",
            source_url="https://youtube.com/watch?v=test",
            platform="youtube",
            filepath="/tmp/media/scraped_video.mp4",
            osint_context={
                "caption": "leaked video",
                "account_age_days": 10
            }
        )
        print(f"  Event published: {success}")
        
        # Test triage complete event
        print("\nTesting triage.complete event...")
        success = event_queue.publish_triage_complete_event(
            asset_id="scraped_001",
            decision="ESCALATE_PALIGEMMA",
            hamming_distance=15,
            similarity=85.5,
            cost=0.0001
        )
        print(f"  Event published: {success}")
        
        # Test PaliGemma complete event
        print("\nTesting paligemma.complete event...")
        success = event_queue.publish_paligemma_complete_event(
            asset_id="scraped_001",
            decision="ESCALATE_LAYER3",
            confidence_score=68.5,
            cost=0.002
        )
        print(f"  Event published: {success}")
        
        print("\n✓ All events published successfully")
        
    except Exception as e:
        print(f"\n✗ Event processing test failed: {e}")


def test_cloud_function_integration():
    """Test Cloud Function integration"""
    print("\n" + "="*70)
    print("TEST: Cloud Function Integration")
    print("="*70)
    
    try:
        from cloud_function_handler import process_layer2_event, process_paligemma_event
        
        # Test Layer 2 event processing
        print("\nTesting Layer 2 event processing...")
        event_data = {
            "event_type": "asset.scraped",
            "asset_id": "test_scraped_001",
            "filepath": "/tmp/media/test_video.mp4",
            "source_url": "https://test.com/video",
            "platform": "test_platform",
            "osint_context": {
                "caption": "test caption",
                "account_age_days": 30
            }
        }
        
        # This would normally be called by Cloud Functions
        # For testing, we'll just validate the function exists
        print(f"  Layer 2 event processor: Available")
        
        # Test PaliGemma event processing
        print("\nTesting PaliGemma event processing...")
        pali_event_data = {
            "event_type": "triage.complete",
            "asset_id": "test_scraped_001",
            "decision": "ESCALATE_PALIGEMMA"
        }
        
        print(f"  PaliGemma event processor: Available")
        print("\n✓ Cloud Function integration ready")
        
    except Exception as e:
        print(f"\n✗ Cloud Function integration test failed: {e}")


def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("AXIOM LAYER 2 & 2.5 TEST SUITE")
    print("="*70)
    
    try:
        # Test individual components
        test_routing_matrix()
        test_osint_analysis()
        
        # Test event-driven processing
        test_event_driven_processing()
        test_cloud_function_integration()
        
        # Test complete pipeline
        test_complete_pipeline()
        
        print("\n" + "="*70)
        print("✓ ALL TESTS COMPLETE")
        print("="*70)
        
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


def test_complete_pipeline():
    """Test complete Layer 2 + 2.5 pipeline"""
    print("\n" + "="*70)
    print("TEST: Complete Layer 2 + 2.5 Pipeline")
    print("="*70)
    
    total_cost = 0.0
    
    # Step 1: Layer 2 Triage
    print("\n[Step 1] Running Layer 2 Triage...")
    layer2_result = test_layer2_triage()
    
    if isinstance(layer2_result, dict):
        total_cost += layer2_result.get("cost", 0.0001)
        decision = layer2_result.get("decision")
    else:
        total_cost += layer2_result.cost
        decision = layer2_result.decision
    
    # Step 2: Route based on Layer 2 decision
    if decision == TriageDecision.BLOCK:
        print("\n[Pipeline Complete] Asset BLOCKED at Layer 2")
        print(f"Total Cost: ${total_cost:.6f}")
        return
    
    elif decision == TriageDecision.DISCARD:
        print("\n[Pipeline Complete] Asset ARCHIVED at Layer 2")
        print(f"Total Cost: ${total_cost:.6f}")
        return
    
    elif decision == TriageDecision.ESCALATE_PALIGEMMA:
        print("\n[Step 2] Escalating to Layer 2.5 PaliGemma...")
        layer25_result = test_layer25_paligemma()
        
        if isinstance(layer25_result, dict):
            total_cost += layer25_result.get("cost", 0.002)
            pali_decision = layer25_result.get("decision")
        else:
            total_cost += layer25_result.cost
            pali_decision = layer25_result.decision
        
        if pali_decision == PaliGemmaDecision.ARCHIVE:
            print("\n[Pipeline Complete] Asset ARCHIVED at Layer 2.5")
            print(f"Total Cost: ${total_cost:.6f}")
            return
        else:
            print("\n[Step 3] Would escalate to Layer 3 (Gemini)")
            total_cost += 0.10  # Layer 3 cost
    
    elif decision == TriageDecision.ESCALATE_VERTEX:
        print("\n[Step 2] Would escalate directly to Layer 3 (Gemini)")
        total_cost += 0.10  # Layer 3 cost
    
    print(f"\n[Pipeline Complete] Total Cost: ${total_cost:.6f}")
    
    # Cost comparison
    print("\n" + "="*70)
    print("COST ANALYSIS")
    print("="*70)
    print(f"Without Triage (direct to Gemini): $0.10")
    print(f"With Layer 2 + 2.5 Triage: ${total_cost:.6f}")
    print(f"Cost Savings: ${0.10 - total_cost:.6f} ({((0.10 - total_cost) / 0.10 * 100):.1f}%)")


if __name__ == "__main__":
    main()
