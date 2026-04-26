from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import logging

logger = logging.getLogger("WAF_Simulator")

# Initialize Limiter for Rate Limiting
limiter = Limiter(key_func=get_remote_address)

# Simulated IP Reputation Database (Mock List)
MALICIOUS_IPS = {
    "192.168.1.99", # Example bad local IP
    "203.0.113.50", # Example mock botnet IP
}

# Simulated Geo-Blocked Regions (Mock List)
GEO_BLOCKED_IPS = {
    "198.51.100.22", # Example IP from a sanctioned/blocked region
}

class CloudArmorMiddleware(BaseHTTPMiddleware):
    """
    Simulates Google Cloud Armor (Layer 1 Security)
    - IP Reputation Checks
    - Basic Geo-Blocking Checks
    """
    async def dispatch(self, request: Request, call_next):
        client_ip = request.headers.get("x-forwarded-for")
        if not client_ip:
            client_ip = request.client.host if request.client else "unknown"
        
        # 1. IP Reputation Check
        if client_ip in MALICIOUS_IPS:
            logger.warning(f"WAF: Blocked malicious IP {client_ip}")
            # return 403 Forbidden
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=403, 
                content={"detail": "WAF Blocked: IP Reputation Score too low (Simulated Cloud Armor)"}
            )
            
        # 2. Geo-Blocking Check
        if client_ip in GEO_BLOCKED_IPS:
            logger.warning(f"WAF: Blocked geo-restricted IP {client_ip}")
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=403, 
                content={"detail": "WAF Blocked: Region not allowed (Simulated Cloud Armor)"}
            )

        # Proceed if WAF passes
        response = await call_next(request)
        return response
