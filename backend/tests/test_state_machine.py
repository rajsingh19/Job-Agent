import pytest
from app.models.enums import ApplicationStatus
from app.schemas.state_machine import ApplicationStateMachine, InvalidStateTransitionError


def test_valid_progressive_lifecycle():
    """Verifies standard forward application progression."""
    progression = [
        (ApplicationStatus.DISCOVERED, ApplicationStatus.MATCHED),
        (ApplicationStatus.MATCHED, ApplicationStatus.DRAFTING),
        (ApplicationStatus.DRAFTING, ApplicationStatus.PENDING_REVIEW),
        (ApplicationStatus.PENDING_REVIEW, ApplicationStatus.APPROVED),
        (ApplicationStatus.APPROVED, ApplicationStatus.SUBMITTING),
        (ApplicationStatus.SUBMITTING, ApplicationStatus.SUBMITTED),
        (ApplicationStatus.SUBMITTED, ApplicationStatus.VIEWED),
        (ApplicationStatus.VIEWED, ApplicationStatus.INTERVIEW),
        (ApplicationStatus.INTERVIEW, ApplicationStatus.OFFER),
    ]

    for from_state, to_state in progression:
        assert ApplicationStateMachine.can_transition(from_state, to_state) is True
        # Should not raise exception
        ApplicationStateMachine.validate_transition(from_state, to_state)


def test_human_in_the_loop_submission_enforcement():
    """
    CRITICAL: The system must NEVER allow direct transition to SUBMITTING or SUBMITTED
    without explicit user approval (APPROVED status).
    """
    # Attempting to submit directly from DISCOVERED
    with pytest.raises(InvalidStateTransitionError):
        ApplicationStateMachine.validate_transition(
            ApplicationStatus.DISCOVERED,
            ApplicationStatus.SUBMITTING,
        )

    # Attempting to submit directly from DRAFTING
    with pytest.raises(InvalidStateTransitionError):
        ApplicationStateMachine.validate_transition(
            ApplicationStatus.DRAFTING,
            ApplicationStatus.SUBMITTING,
        )

    # Attempting to submit directly from PENDING_REVIEW without moving to APPROVED first
    with pytest.raises(InvalidStateTransitionError):
        ApplicationStateMachine.validate_transition(
            ApplicationStatus.PENDING_REVIEW,
            ApplicationStatus.SUBMITTING,
        )

    # Attempting to bypass SUBMITTING straight to SUBMITTED
    with pytest.raises(InvalidStateTransitionError):
        ApplicationStateMachine.validate_transition(
            ApplicationStatus.PENDING_REVIEW,
            ApplicationStatus.SUBMITTED,
        )


def test_requires_user_action_and_recovery():
    """
    Verifies that anti-bot / OTP / login challenges transition to REQUIRES_USER_ACTION
    and can safely resume once the user takes action.
    """
    # CAPTCHA / 2FA encountered during drafting
    assert ApplicationStateMachine.can_transition(
        ApplicationStatus.DRAFTING,
        ApplicationStatus.REQUIRES_USER_ACTION,
    ) is True

    # CAPTCHA / OTP encountered during submission
    assert ApplicationStateMachine.can_transition(
        ApplicationStatus.SUBMITTING,
        ApplicationStatus.REQUIRES_USER_ACTION,
    ) is True

    # User resolves action -> resume drafting or review
    assert ApplicationStateMachine.can_transition(
        ApplicationStatus.REQUIRES_USER_ACTION,
        ApplicationStatus.PENDING_REVIEW,
    ) is True

    assert ApplicationStateMachine.can_transition(
        ApplicationStatus.REQUIRES_USER_ACTION,
        ApplicationStatus.APPROVED,
    ) is True


def test_terminal_states():
    """Verifies that terminal states do not allow arbitrary outgoing transitions."""
    assert ApplicationStateMachine.can_transition(ApplicationStatus.OFFER, ApplicationStatus.SUBMITTING) is False
    assert ApplicationStateMachine.can_transition(ApplicationStatus.REJECTED, ApplicationStatus.APPROVED) is False
    assert ApplicationStateMachine.can_transition(ApplicationStatus.WITHDRAWN, ApplicationStatus.DRAFTING) is False
