"""Isolated Replica Web Application for SentinelX Mode 2 Defense.

Provides a dedicated local testbed simulating 'Acme Financial Customer Portal':
- Routes: /replica, /replica/login, /replica/portal, /replica/admin, /replica/admin-decoy, /replica/status.
- Checks LocalReplicaAdapter on incoming requests: if target IP is blocked,
  returns HTTP 403 with remaining TTL details.
- Hardened client identity: Uses actual connection address and only trusts X-Forwarded-For
  from explicitly configured trusted reverse proxies. Never trusts ?client_ip=.
- Decoy honeypot trap (/replica/admin-decoy): Logs structured honeypot_interaction events
  with zero storage of request bodies, passwords, tokens, or form data.
- Strictly isolated from Mode 1 real sites and configurations.
"""

from typing import Dict, Any, Optional, Set
from datetime import datetime, timezone
from fastapi import APIRouter, Request, HTTPException, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from src.enforcement.models import OperatingMode
from src.enforcement.adapters.local_replica import LocalReplicaAdapter
from src.replica.honeypot import record_honeypot_interaction
from src.replica.html_views import render_northstar_campus_portal

replica_router = APIRouter(prefix="/replica", tags=["Mode 2: Isolated Replica Lab"])

# Singleton local replica adapter instance for the replica web application
_replica_adapter: Optional[LocalReplicaAdapter] = None

# Explicitly configured trusted reverse proxies (default: empty set)
_trusted_proxies: Set[str] = set()


def get_replica_adapter() -> LocalReplicaAdapter:
    """Get or create singleton LocalReplicaAdapter for the replica app."""
    global _replica_adapter
    if _replica_adapter is None:
        _replica_adapter = LocalReplicaAdapter()
    return _replica_adapter


def set_replica_adapter(adapter: LocalReplicaAdapter):
    """Override adapter (e.g. for testing or policy engine shared binding)."""
    global _replica_adapter
    _replica_adapter = adapter


def get_trusted_proxies() -> Set[str]:
    """Return set of explicitly configured trusted proxy IP addresses."""
    return set(_trusted_proxies)


def set_trusted_proxies(proxies: Any):
    """Set explicitly configured trusted proxy IP addresses."""
    global _trusted_proxies
    _trusted_proxies = set(proxies)


def add_trusted_proxy(ip: str):
    """Add a trusted proxy IP address."""
    global _trusted_proxies
    _trusted_proxies.add(ip)


def reset_trusted_proxies():
    """Reset trusted proxies back to default empty set."""
    global _trusted_proxies
    _trusted_proxies = set()


class ReplicaLoginRequest(BaseModel):
    username: str = Field(..., examples=["admin"])
    password: str = Field(..., examples=["Secret123!"])
    client_ip: Optional[str] = Field(
        None,
        description="Deprecated/Ignored: Connection identity is derived strictly from network socket or trusted proxy."
    )


def _extract_replica_client_ip(request: Request) -> str:
    """Extract client IP using actual connection address, trusting X-Forwarded-For ONLY if from configured proxy.

    Security Rule: Never trusts ?client_ip= query parameters or body parameters for identity.
    """
    conn_ip = request.client.host if (request.client and request.client.host) else "127.0.0.1"

    # Forwarded headers are ONLY trusted if the direct connection comes from an explicitly configured proxy
    if conn_ip in _trusted_proxies:
        fwd = request.headers.get("X-Forwarded-For")
        if fwd:
            candidate = fwd.split(",")[0].strip()
            if candidate:
                return candidate

    return conn_ip


def _check_replica_block(target_ip: str, route: str):
    """Check if target_ip is actively blocked on LocalReplicaAdapter and raise 403 if so."""
    adapter = get_replica_adapter()
    if adapter.is_ip_blocked(target_ip):
        active = [b for b in adapter.get_active_blocks() if b.target_ip == target_ip]
        exp = active[0].expires_at if active else "soon"
        reason = active[0].reason if active else "Automated block active."
        ttl_rem = 0
        if active:
            now_dt = datetime.now(timezone.utc)
            exp_dt = datetime.fromisoformat(active[0].expires_at)
            ttl_rem = max(0, int((exp_dt - now_dt).total_seconds()))
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "ACCESS_BLOCKED",
                "status": "REPLICA_BLOCKED",
                "target_ip": target_ip,
                "route": route,
                "expires_at": exp,
                "ttl_remaining_seconds": ttl_rem,
                "reason": reason,
                "message": "Access blocked by SentinelX Mode 2 Replica Defense.",
            }
        )


def check_replica_route_access(route: str, target_ip: str) -> Dict[str, Any]:
    """Internal server-side probe evaluating replica access for a target IP without client-controlled params."""
    adapter = get_replica_adapter()
    if adapter.is_ip_blocked(target_ip):
        active = [b for b in adapter.get_active_blocks() if b.target_ip == target_ip]
        exp = active[0].expires_at if active else "soon"
        reason = active[0].reason if active else "Automated block active."
        ttl_rem = 0
        if active:
            now_dt = datetime.now(timezone.utc)
            exp_dt = datetime.fromisoformat(active[0].expires_at)
            ttl_rem = max(0, int((exp_dt - now_dt).total_seconds()))
        return {
            "status_code": 403,
            "blocked": True,
            "target_ip": target_ip,
            "route": route,
            "expires_at": exp,
            "ttl_remaining_seconds": ttl_rem,
            "reason": reason,
        }
    return {
        "status_code": 200,
        "blocked": False,
        "target_ip": target_ip,
        "route": route,
        "reason": "Traffic permitted.",
    }


@replica_router.get("", status_code=status.HTTP_200_OK)
@replica_router.get("/", status_code=status.HTTP_200_OK)
def replica_home(request: Request):
    """Replica campus portal homepage."""
    ip = _extract_replica_client_ip(request)
    _check_replica_block(ip, request.url.path)

    if "text/html" in request.headers.get("accept", ""):
        return HTMLResponse(content=render_northstar_campus_portal(active_route="/replica", client_ip=ip))

    return {
        "service": "Northstar Campus Portal (Lab Replica)",
        "environment": "MODE_2_ISOLATED_REPLICA",
        "status": "ONLINE",
        "routes": ["/replica/login", "/replica/portal", "/replica/admin", "/replica/admin-decoy", "/replica/status"],
        "notice": "Safe lab testbed for defensive validation. Isolated from Mode 1 production sites.",
    }


@replica_router.get("/login", status_code=status.HTTP_200_OK)
def replica_login_page(request: Request):
    """Simulated SSO login page for browser navigation."""
    ip = _extract_replica_client_ip(request)
    _check_replica_block(ip, "/replica/login")

    if "text/html" in request.headers.get("accept", ""):
        return HTMLResponse(content=render_northstar_campus_portal(active_route="/replica/login", client_ip=ip))

    return {
        "service": "Northstar Single Sign-On (SSO)",
        "status": "READY_FOR_POST",
        "endpoint": "/replica/login",
        "method": "POST",
    }


@replica_router.post("/login")
def replica_login(req: ReplicaLoginRequest, request: Request):
    """Simulated login endpoint. Returns 403 if IP blocked, 401 on bad password, 200 on success."""
    target_ip = _extract_replica_client_ip(request)
    _check_replica_block(target_ip, "/replica/login")

    # Valid credential check
    if req.username == "admin" and req.password == "ReplicaLab2026!":
        return {
            "status": "AUTHENTICATED",
            "user": "admin",
            "token": "rep-jwt-session-token-valid",
            "message": "Welcome to Northstar Campus Portal."
        }

    # Invalid credentials -> HTTP 401
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={
            "error": "INVALID_CREDENTIALS",
            "message": "Authentication failed: invalid username or password.",
            "target_ip": target_ip,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )


@replica_router.get("/portal")
def replica_portal(request: Request):
    """Protected customer portal dashboard."""
    ip = _extract_replica_client_ip(request)
    _check_replica_block(ip, "/replica/portal")

    if "text/html" in request.headers.get("accept", ""):
        return HTMLResponse(content=render_northstar_campus_portal(active_route="/replica/portal", client_ip=ip))

    return {
        "portal": "Northstar Campus Portal | Student Dashboard",
        "student_name": "Elena Vance",
        "account_id": "ACC-99201-REPLICA",
        "balance": 15420.50,
        "recent_transactions": [
            {"id": "tx-1", "amount": -120.00, "desc": "Campus Bookstore Course Pack"},
            {"id": "tx-2", "amount": 2500.00, "desc": "Fall Semester Tuition Deposit"},
        ]
    }


@replica_router.get("/admin")
def replica_admin(request: Request):
    """Protected administrative route."""
    ip = _extract_replica_client_ip(request)
    _check_replica_block(ip, "/replica/admin")

    if "text/html" in request.headers.get("accept", ""):
        return HTMLResponse(content=render_northstar_campus_portal(active_route="/replica/admin", client_ip=ip))

    return {
        "portal": "Northstar Campus Admin Console (Replica)",
        "authorized_ip": ip,
        "system_status": "NORMAL",
    }


@replica_router.get("/admin-decoy", status_code=status.HTTP_200_OK)
@replica_router.post("/admin-decoy", status_code=status.HTTP_200_OK)
def replica_admin_decoy(request: Request):
    """Decoy administrative trap route.

    Records structured honeypot interaction and returns a generic decoy challenge.
    Never stores request bodies, passwords, tokens, or submitted form parameters.
    Checks if source IP is blocked on LocalReplicaAdapter and raises 403 if so.
    """
    conn_ip = _extract_replica_client_ip(request)

    # 1. Record honeypot interaction event with real connection identity
    event = record_honeypot_interaction(
        route="/replica/admin-decoy",
        http_method=request.method,
        source_identity=conn_ip,
        identity_type="REAL_CONNECTION",
        site_id="lab-replica-site",
    )

    # 2. Check if IP is already actively blocked
    _check_replica_block(conn_ip, "/replica/admin-decoy")

    # 3. Return HTML view if requested by browser
    if "text/html" in request.headers.get("accept", ""):
        return HTMLResponse(content=render_northstar_campus_portal(
            active_route="/replica/admin-decoy",
            client_ip=conn_ip,
            scenario_hint=event.event_id,
        ))

    # 4. Return decoy challenge response (never processing or storing sensitive inputs)
    return {
        "service": "Northstar Internal Staff Gateway (Decoy)",
        "status": "CHALLENGE_REQUIRED",
        "notice": "Administrative access restricted. Security challenge active.",
        "route": "/replica/admin-decoy",
        "event_id": event.event_id,
        "timestamp": event.timestamp,
    }


@replica_router.get("/status")
def replica_status():
    """Retrieve current replica state and active local blocks."""
    adapter = get_replica_adapter()
    blocks = adapter.get_active_blocks()
    return {
        "operating_mode": OperatingMode.MODE_2_REPLICA_DEFENSE.value,
        "site_id": "lab-replica-site",
        "active_blocks_count": len(blocks),
        "active_blocks": [b.model_dump() for b in blocks],
        "isolation_status": "STRICTLY_ISOLATED_FROM_MODE_1",
        "honeypot_deployed": True,
        "honeypot_routes": ["/replica/admin-decoy"],
    }
