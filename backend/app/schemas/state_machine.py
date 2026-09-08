from typing import Dict, Set
from app.models.enums import ApplicationStatus


class InvalidStateTransitionError(ValueError):
    """Raised when an illegal or unapproved application state transition is attempted."""
    def __init__(self, from_status: ApplicationStatus | str, to_status: ApplicationStatus | str, reason: str = ""):
        self.from_status = from_status
        self.to_status = to_status
        self.reason = reason
        super().__init__(
            f"Invalid transition from {from_status} to {to_status}." + (f" Reason: {reason}" if reason else "")
        )


# Mapping of valid source status -> allowed destination statuses
VALID_TRANSITIONS: Dict[ApplicationStatus, Set[ApplicationStatus]] = {
    ApplicationStatus.DISCOVERED: {
        ApplicationStatus.MATCHED,
        ApplicationStatus.DRAFTING,
        ApplicationStatus.WITHDRAWN,
        ApplicationStatus.FAILED,
    },
    ApplicationStatus.MATCHED: {
        ApplicationStatus.DRAFTING,
        ApplicationStatus.WITHDRAWN,
        ApplicationStatus.FAILED,
    },
    ApplicationStatus.DRAFTING: {
        ApplicationStatus.PENDING_REVIEW,
        ApplicationStatus.REQUIRES_USER_ACTION,
        ApplicationStatus.FAILED,
        ApplicationStatus.WITHDRAWN,
    },
    ApplicationStatus.PENDING_REVIEW: {
        ApplicationStatus.APPROVED,
        ApplicationStatus.DRAFTING,  # User requested re-draft
        ApplicationStatus.REJECTED,
        ApplicationStatus.WITHDRAWN,
        ApplicationStatus.REQUIRES_USER_ACTION,
    },
    ApplicationStatus.APPROVED: {
        ApplicationStatus.SUBMITTING,
        ApplicationStatus.PENDING_REVIEW,  # Revoke approval / back to review
        ApplicationStatus.WITHDRAWN,
    },
    ApplicationStatus.SUBMITTING: {
        ApplicationStatus.SUBMITTED,
        ApplicationStatus.REQUIRES_USER_ACTION,  # Bot detection / OTP / 2FA triggered during submission
        ApplicationStatus.FAILED,
        ApplicationStatus.WITHDRAWN,
    },
    ApplicationStatus.SUBMITTED: {
        ApplicationStatus.VIEWED,
        ApplicationStatus.INTERVIEW,
        ApplicationStatus.OFFER,
        ApplicationStatus.REJECTED,
        ApplicationStatus.WITHDRAWN,
    },
    ApplicationStatus.VIEWED: {
        ApplicationStatus.INTERVIEW,
        ApplicationStatus.OFFER,
        ApplicationStatus.REJECTED,
        ApplicationStatus.WITHDRAWN,
    },
    ApplicationStatus.INTERVIEW: {
        ApplicationStatus.OFFER,
        ApplicationStatus.REJECTED,
        ApplicationStatus.WITHDRAWN,
    },
    ApplicationStatus.REQUIRES_USER_ACTION: {
        ApplicationStatus.DRAFTING,
        ApplicationStatus.PENDING_REVIEW,
        ApplicationStatus.APPROVED,
        ApplicationStatus.SUBMITTING,
        ApplicationStatus.FAILED,
        ApplicationStatus.WITHDRAWN,
    },
    # Terminal states
    ApplicationStatus.OFFER: set(),
    ApplicationStatus.REJECTED: set(),
    ApplicationStatus.WITHDRAWN: set(),
    ApplicationStatus.FAILED: {
        ApplicationStatus.DRAFTING,  # Allow retry from failed state
        ApplicationStatus.SUBMITTING,
    },
}


class ApplicationStateMachine:
    """
    Validates and enforces the application lifecycle state transitions.
    Guarantees that no application can reach SUBMITTING without going through APPROVED.
    """

    @classmethod
    def can_transition(
        cls,
        from_status: ApplicationStatus | str,
        to_status: ApplicationStatus | str,
    ) -> bool:
        from_enum = ApplicationStatus(from_status)
        to_enum = ApplicationStatus(to_status)
        allowed = VALID_TRANSITIONS.get(from_enum, set())
        return to_enum in allowed

    @classmethod
    def validate_transition(
        cls,
        from_status: ApplicationStatus | str,
        to_status: ApplicationStatus | str,
        user_approved: bool = False,
    ) -> None:
        from_enum = ApplicationStatus(from_status)
        to_enum = ApplicationStatus(to_status)

        if not cls.can_transition(from_enum, to_enum):
            raise InvalidStateTransitionError(
                from_status=from_enum.value,
                to_status=to_enum.value,
                reason=f"Transition from {from_enum.value} to {to_enum.value} is not permitted by lifecycle rules.",
            )

        # Strict Human-In-The-Loop Check: Only APPROVED can go to SUBMITTING
        if to_enum == ApplicationStatus.SUBMITTING and from_enum != ApplicationStatus.APPROVED:
            raise InvalidStateTransitionError(
                from_status=from_enum.value,
                to_status=to_enum.value,
                reason="Applications cannot enter SUBMITTING without prior explicit user approval (APPROVED status).",
            )
