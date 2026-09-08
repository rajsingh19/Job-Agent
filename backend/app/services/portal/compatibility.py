from typing import List, Optional
from pydantic import BaseModel, Field
from app.services.browser.models import DiscoveredForm
from app.services.portal.models import PortalCapabilities


class CompatibilityReport(BaseModel):
    """
    Assessment of compatibility between a discovered application form and a portal adapter.
    """
    is_compatible: bool
    portal_id: str
    unsupported_features: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    requires_user_action: bool = False
    recommendation: Optional[str] = None


class CompatibilityChecker:
    """
    Evaluates form compatibility against portal capabilities.
    Enforces safety boundaries when unsupported or risky features are detected.
    """

    @classmethod
    def check_compatibility(
        cls,
        form: DiscoveredForm,
        capabilities: PortalCapabilities,
        portal_id: str = "generic_ats",
    ) -> CompatibilityReport:
        unsupported: List[str] = []
        warnings: List[str] = []
        requires_user_action = False

        # 1. Multi-step form verification
        if (form.has_next_button or (form.total_steps and form.total_steps > 1)) and not capabilities.supports_multi_step_forms:
            unsupported.append("MULTI_STEP_FORMS")
            warnings.append(
                f"Portal '{portal_id}' does not have verified multi-step form support. Manual progression required."
            )
            requires_user_action = True

        # 2. Resume upload field verification
        has_file_input = any(f.input_type == "file" for f in form.fields)
        if has_file_input and not capabilities.supports_resume_upload:
            unsupported.append("RESUME_UPLOAD")
            warnings.append(
                f"Portal '{portal_id}' does not support automated file/resume uploads."
            )
            requires_user_action = True

        # 3. Confirmation heuristics verification
        if not capabilities.has_known_confirmation_patterns:
            warnings.append(
                f"Portal '{portal_id}' has unverified confirmation patterns; manual confirmation review recommended."
            )

        is_compatible = len(unsupported) == 0

        recommendation = None
        if not is_compatible:
            recommendation = (
                "Form requires capabilities unsupported by this connector. Transitioning to REQUIRES_USER_ACTION."
            )

        return CompatibilityReport(
            is_compatible=is_compatible,
            portal_id=portal_id,
            unsupported_features=unsupported,
            warnings=warnings,
            requires_user_action=requires_user_action,
            recommendation=recommendation,
        )
