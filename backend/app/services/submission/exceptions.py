class SubmissionError(Exception):
    """Base exception for all submission-related errors."""
    pass


class ApprovalRequiredError(SubmissionError):
    """Raised when application submission is attempted without explicit human approval."""
    def __init__(self, application_id: str, message: str = "Explicit human approval is required before submission."):
        self.application_id = application_id
        super().__init__(f"{message} (Application: '{application_id}')")


class ApprovalExpiredError(SubmissionError):
    """Raised when an application draft was modified after approval, invalidating the previous version hash."""
    def __init__(self, application_id: str, message: str = "Approval has expired because the application content changed."):
        self.application_id = application_id
        super().__init__(f"{message} (Application: '{application_id}'). Re-approval is required.")


class AlreadySubmittedError(SubmissionError):
    """Raised when attempting to submit an application that has already reached SUBMITTED state."""
    def __init__(self, application_id: str, submitted_at: str = ""):
        self.application_id = application_id
        self.submitted_at = submitted_at
        super().__init__(
            f"Application '{application_id}' has already been submitted"
            + (f" at {submitted_at}." if submitted_at else ".")
            + " Duplicate submission is blocked."
        )


class SubmissionControlNotFoundError(SubmissionError):
    """Raised when the final submit button or control cannot be found on the page."""
    def __init__(self, message: str = "Final submission control was not found on the application page."):
        super().__init__(message)


class SubmissionConfirmationError(SubmissionError):
    """Raised when submission confirmation could not be verified."""
    def __init__(self, message: str = "Submission confirmation could not be verified on the portal page."):
        super().__init__(message)


class ConcurrentSubmissionError(SubmissionError):
    """Raised when concurrent submission attempts occur on the same application."""
    def __init__(self, application_id: str):
        super().__init__(f"Another submission attempt is already in progress for application '{application_id}'.")


class SubmissionBlockedError(SubmissionError):
    """
    CRITICAL SECURITY GUARD:
    Raised when final submission is attempted without a valid, cryptographically bound
    SubmissionAuthorization token.
    """
    def __init__(self, message: str = "Submission action blocked: Missing or invalid submission authorization."):
        super().__init__(message)
