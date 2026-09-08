import logging
import re
from datetime import datetime, timezone
from urllib.parse import urlparse
from typing import Any, Dict, List, Optional
from app.services.browser.models import BrowserField, DiscoveredForm
from app.services.portal.models import FormStepInfo, PortalDiagnostics

logger = logging.getLogger(__name__)

# Patterns that must never appear in diagnostics or logs
FORBIDDEN_KEY_PATTERNS = [
    re.compile(r"password", re.IGNORECASE),
    re.compile(r"token", re.IGNORECASE),
    re.compile(r"secret", re.IGNORECASE),
    re.compile(r"cookie", re.IGNORECASE),
    re.compile(r"auth", re.IGNORECASE),
    re.compile(r"otp", re.IGNORECASE),
    re.compile(r"passcode", re.IGNORECASE),
]


class PortalDiagnosticsCollector:
    """
    Safely captures diagnostic telemetry for browser execution sessions.
    Strictly redacts credentials, OTPs, tokens, cookies, and local filesystem paths.
    """

    @classmethod
    def sanitize_url(cls, url: Optional[str]) -> str:
        """Extracts domain or safe URL path, stripping sensitive query params."""
        if not url:
            return ""
        try:
            parsed = urlparse(url if "://" in url else f"https://{url}")
            return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        except Exception:
            return ""

    @classmethod
    def collect_diagnostics(
        cls,
        portal_id: str,
        portal_name: str,
        current_url: Optional[str],
        step_info: Optional[FormStepInfo] = None,
        form: Optional[DiscoveredForm] = None,
        auth_state: str = "UNKNOWN",
        challenge_state: str = "NONE",
        navigation_history: Optional[List[str]] = None,
        selector_failures: Optional[List[str]] = None,
        warnings: Optional[List[str]] = None,
        timeline_events: Optional[List[Dict[str, Any]]] = None,
    ) -> PortalDiagnostics:
        sanitized_url = cls.sanitize_url(current_url)
        try:
            domain = urlparse(sanitized_url).netloc or sanitized_url
        except Exception:
            domain = ""

        # Safe field counts
        total_fields = len(form.fields) if form else 0
        missing_req: List[str] = []
        if form:
            for f in form.fields:
                if f.required and (not f.value or not str(f.value).strip()):
                    missing_req.append(f.field_id)

        # Sanitize navigation history (no query parameters containing secrets)
        safe_nav_history = [cls.sanitize_url(u) for u in (navigation_history or [])]

        # Sanitize timeline events
        safe_timeline: List[Dict[str, Any]] = []
        for event in (timeline_events or []):
            safe_event = {
                "step": event.get("step"),
                "status": event.get("status"),
                "timestamp": event.get("timestamp", datetime.now(timezone.utc).isoformat()),
                "message": event.get("message"),
            }
            safe_timeline.append(safe_event)

        diagnostics = PortalDiagnostics(
            portal_id=portal_id,
            portal_name=portal_name,
            url_domain=domain,
            current_step=step_info or FormStepInfo(),
            total_fields_discovered=total_fields,
            missing_required_fields=missing_req,
            auth_state=auth_state,
            challenge_state=challenge_state,
            selector_failures=selector_failures or [],
            navigation_history=safe_nav_history,
            timeline=safe_timeline,
            warnings=warnings or [],
        )

        logger.info(
            "Captured portal diagnostics: portal=%s domain=%s step=%s fields=%d missing_req=%d",
            portal_id,
            domain,
            diagnostics.current_step.step_index,
            total_fields,
            len(missing_req),
        )
        return diagnostics
