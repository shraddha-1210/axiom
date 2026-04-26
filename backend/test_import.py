#!/usr/bin/env python3

# Simple test to check what's wrong with paligemma_triage import

print("Testing paligemma_triage import...")

try:
    import paligemma_triage
    print("✓ Module imported successfully")
    print(f"Available attributes: {[attr for attr in dir(paligemma_triage) if not attr.startswith('_')]}")
except Exception as e:
    print(f"✗ Import failed: {e}")

try:
    from paligemma_triage import PaliGemmaDecision
    print("✓ PaliGemmaDecision imported successfully")
except Exception as e:
    print(f"✗ PaliGemmaDecision import failed: {e}")

try:
    from paligemma_triage import PaliGemmaResult
    print("✓ PaliGemmaResult imported successfully")
except Exception as e:
    print(f"✗ PaliGemmaResult import failed: {e}")

try:
    from paligemma_triage import run_paligemma_triage
    print("✓ run_paligemma_triage imported successfully")
except Exception as e:
    print(f"✗ run_paligemma_triage import failed: {e}")

# Check if file exists and is readable
import os
file_path = "paligemma_triage.py"
if os.path.exists(file_path):
    print(f"✓ File exists: {file_path}")
    print(f"File size: {os.path.getsize(file_path)} bytes")
else:
    print(f"✗ File not found: {file_path}")