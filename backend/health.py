"""
Layer 4 — Deep Health Monitor

Checks all five external services and returns a unified status matrix.
Equivalent to the Cloud Monitoring health checks in the enterprise architecture.
"""

import os
import time
from pathlib import Path
from typing import Dict, Any

from dotenv import load_dotenv

env_path = Path('.env') if Path('.env').exists() else Path('../.env')
load_dotenv(dotenv_path=env_path)


def _check_neondb() -> Dict[str, Any]:
    start = time.monotonic()
    try:
        from database import SessionLocal
        db = SessionLocal()
        db.execute(__import__("sqlalchemy").text("SELECT 1"))
        db.close()
        return {"status": "ok", "latency_ms": round((time.monotonic() - start) * 1000, 2)}
    except Exception as e:
        return {"status": "error", "error": str(e), "latency_ms": -1}


def _check_pinecone() -> Dict[str, Any]:
    start = time.monotonic()
    try:
        from pinecone import Pinecone
        api_key = os.getenv("PINECONE_API_KEY")
        index_name = os.getenv("PINECONE_INDEX", "axiom")
        if not api_key:
            return {"status": "unconfigured"}
        pc = Pinecone(api_key=api_key)
        stats = pc.Index(index_name).describe_index_stats()
        return {
            "status": "ok",
            "total_vectors": stats.get("total_vector_count", 0),
            "latency_ms": round((time.monotonic() - start) * 1000, 2)
        }
    except Exception as e:
        return {"status": "error", "error": str(e), "latency_ms": -1}


def _check_upstash() -> Dict[str, Any]:
    start = time.monotonic()
    try:
        import redis as redis_lib
        url = os.getenv("REDIS_URL")
        if not url:
            return {"status": "unconfigured"}
        r = redis_lib.from_url(url, socket_connect_timeout=3)
        r.ping()
        return {"status": "ok", "latency_ms": round((time.monotonic() - start) * 1000, 2)}
    except Exception as e:
        return {"status": "error", "error": str(e), "latency_ms": -1}


def _check_paligemma() -> Dict[str, Any]:
    start = time.monotonic()
    try:
        import requests as req
        url = os.getenv("PALIGEMMA_URL") or os.getenv("COLAB_NGROK_URL")
        if not url:
            return {"status": "unconfigured"}
        r = req.get(f"{url}/health", timeout=5)
        if r.status_code == 200:
            return {"status": "ok", "latency_ms": round((time.monotonic() - start) * 1000, 2)}
        return {"status": "degraded", "http_code": r.status_code}
    except Exception as e:
        return {"status": "error", "error": str(e), "latency_ms": -1}


def _check_gemini() -> Dict[str, Any]:
    start = time.monotonic()
    try:
        import google.generativeai as genai
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return {"status": "unconfigured"}
        genai.configure(api_key=api_key)
        models = [m.name for m in genai.list_models()]
        return {
            "status": "ok" if models else "empty",
            "latency_ms": round((time.monotonic() - start) * 1000, 2)
        }
    except Exception as e:
        return {"status": "error", "error": str(e), "latency_ms": -1}


def get_full_health_matrix() -> Dict[str, Any]:
    """
    Run all health checks in sequence and return a unified status matrix.
    Green = all services reachable.
    Degraded = at least one service error but core DB is healthy.
    Critical = NeonDB unreachable.
    """
    checks = {
        "neondb":    _check_neondb(),
        "pinecone":  _check_pinecone(),
        "upstash":   _check_upstash(),
        "paligemma": _check_paligemma(),
        "gemini":    _check_gemini(),
    }

    # Determine overall system status
    has_any_error = any(v.get("status") == "error" for v in checks.values())
    db_ok = checks["neondb"]["status"] == "ok"

    if not db_ok:
        overall = "critical"
    elif has_any_error:
        overall = "degraded"
    else:
        overall = "healthy"

    return {
        "overall": overall,
        "services": checks,
        "region": os.getenv("GCP_REGION", "local"),
    }
