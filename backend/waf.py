from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import ipaddress
import logging

logger = logging.getLogger("WAF_Simulator")

# Initialize Limiter for Rate Limiting
limiter = Limiter(key_func=get_remote_address)

# Simulated IP Reputation Database (Mock List)
MALICIOUS_IPS = {
    "192.168.1.99",  # Example bad local IP
    "203.0.113.50",  # Example mock botnet IP
}

# Simulated Geo-Blocked Regions (Mock List)
GEO_BLOCKED_IPS = {
    "198.51.100.22",  # Example IP from a sanctioned/blocked region
}

# Trusted reverse-proxy / load-balancer CIDRs.
# Only accept x-forwarded-for when the TCP connection comes from one of these.
# In production, set this to your Cloud Armor / GCP LB CIDR ranges.
TRUSTED_PROXY_CIDRS = [
    ipaddress.ip_network("127.0.0.1/32"),       # local dev
    ipaddress.ip_network("::1/128"),             # local dev IPv6
    ipaddress.ip_network("35.191.0.0/16"),       # GCP Load Balancer health checks
    ipaddress.ip_network("130.211.0.0/22"),      # GCP Load Balancer forwarding
]


def _is_trusted_proxy(ip: str) -> bool:
    """Returns True if the direct TCP peer is a known trusted proxy."""
    try:
        addr = ipaddress.ip_address(ip)
        return any(addr in net for net in TRUSTED_PROXY_CIDRS)
    except ValueError:
        return False


def _resolve_client_ip(request: Request) -> str:
    """
    Safely resolves the real client IP.

    Rules:
    - ONLY trust x-forwarded-for when the direct TCP connection arrives
      from a known trusted proxy CIDR.  This prevents any client from
      injecting a fake x-forwarded-for to spoof their IP.
    - Falls back to the raw TCP peer address otherwise.
    """
    direct_peer = request.client.host if request.client else "unknown"

    if _is_trusted_proxy(direct_peer):
        forwarded_for = request.headers.get("x-forwarded-for", "")
        # x-forwarded-for may be a comma-separated list; the first entry is the
        # original client IP, subsequent entries are proxy hops.
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

    return direct_peer


class CloudArmorMiddleware(BaseHTTPMiddleware):
    """
    Simulates Google Cloud Armor (Layer 1 Security)
    - IP Reputation Checks (with trusted-proxy validation)
    - Basic Geo-Blocking Checks
    - NOTE: No payload-level inspection (SQLi/XSS) in this MVP shim.
      In production, Cloud Armor managed rule sets cover these vectors.
    """

    async def dispatch(self, request: Request, call_next):
        client_ip = _resolve_client_ip(request)

        # 1. IP Reputation Check
        if client_ip in MALICIOUS_IPS:
            logger.warning(f"WAF: Blocked malicious IP {client_ip}")
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
