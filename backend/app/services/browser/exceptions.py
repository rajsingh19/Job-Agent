class BrowserExecutionError(Exception):
    """Base exception for all browser automation errors."""
    pass


class BrowserSessionNotFoundError(BrowserExecutionError):
    """Raised when a requested browser session does not exist or has expired."""
    pass


class BrowserAuthenticationRequiredError(BrowserExecutionError):
    """Raised when the target website requires user authentication/login."""
    pass


class BrowserChallengeDetectedError(BrowserExecutionError):
    """Raised when a security challenge (CAPTCHA, bot detection, OTP, 2FA) is encountered."""
    def __init__(self, challenge_type: str, message: str = "Security challenge encountered."):
        self.challenge_type = challenge_type
        super().__init__(f"{message} (Challenge: {challenge_type})")


class FormDetectionError(BrowserExecutionError):
    """Raised when the application form cannot be identified or inspected."""
    pass


class FieldExecutionError(BrowserExecutionError):
    """Raised when interaction with a form field fails."""
    pass


class ResumeUploadError(BrowserExecutionError):
    """Raised when resume file validation or upload fails."""
    pass


class SubmissionBlockedError(BrowserExecutionError):
    """
    CRITICAL SECURITY GUARD:
    Raised when any attempt to perform final submission is detected in Phase 7.
    Phase 7 is strictly prohibited from submitting applications. Final submission
    is exclusively reserved for Phase 8 after explicit human approval.
    """
    def __init__(self, control_name: str = "Submit", message: str = "Final submission action is blocked in Phase 7."):
        self.control_name = control_name
        super().__init__(f"{message} Attempted control: '{control_name}'. Final submission requires Phase 8 explicit approval.")


class UserActionRequiredError(BrowserExecutionError):
    """Raised when human intervention is required before automated execution can continue."""
    def __init__(self, reason: str, user_instructions: str):
        self.reason = reason
        self.user_instructions = user_instructions
        super().__init__(f"User action required: {reason}. Instructions: {user_instructions}")
