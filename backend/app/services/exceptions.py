from fastapi import HTTPException, status


class AppException(HTTPException):
    """Base application exception with standardized code and status code."""
    def __init__(self, status_code: int, code: str, message: str, details: dict | None = None):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(
            status_code=status_code,
            detail={
                "error": code,
                "message": message,
                "details": self.details,
            },
        )


class UnsupportedFileTypeError(AppException):
    def __init__(self, message: str = "Unsupported file type. Only PDF and DOCX files are supported."):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="UNSUPPORTED_FILE_TYPE",
            message=message,
        )


class FileTooLargeError(AppException):
    def __init__(self, max_size_mb: float):
        super().__init__(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE if hasattr(status, "HTTP_413_CONTENT_TOO_LARGE") else 413,
            code="FILE_TOO_LARGE",
            message=f"File exceeds maximum allowed size of {max_size_mb:.1f} MB.",
        )


class FileCorruptedError(AppException):
    def __init__(self, message: str = "The uploaded file is corrupted or unreadable."):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="FILE_CORRUPTED",
            message=message,
        )


class TextExtractionFailedError(AppException):
    def __init__(self, message: str = "Failed to extract text from the resume document."):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT if hasattr(status, "HTTP_422_UNPROCESSABLE_CONTENT") else 422,
            code="TEXT_EXTRACTION_FAILED",
            message=message,
        )


class TextExtractionRequiredError(AppException):
    def __init__(self, message: str = "Document appears to be scanned or image-only. Text extraction is required."):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT if hasattr(status, "HTTP_422_UNPROCESSABLE_CONTENT") else 422,
            code="TEXT_EXTRACTION_REQUIRED",
            message=message,
        )


class LLMUnavailableError(AppException):
    def __init__(self, message: str = "AI / LLM parsing provider is currently unavailable."):
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code="LLM_UNAVAILABLE",
            message=message,
        )


class LLMParseFailedError(AppException):
    def __init__(self, message: str = "Failed to parse resume into structured profile using LLM."):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT if hasattr(status, "HTTP_422_UNPROCESSABLE_CONTENT") else 422,
            code="LLM_PARSE_FAILED",
            message=message,
        )


class ProfileValidationError(AppException):
    def __init__(self, message: str = "Candidate profile failed validation checks.", details: dict | None = None):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT if hasattr(status, "HTTP_422_UNPROCESSABLE_CONTENT") else 422,
            code="PROFILE_VALIDATION_FAILED",
            message=message,
            details=details,
        )


class ResumeNotFoundError(AppException):
    def __init__(self, resume_id: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            code="RESUME_NOT_FOUND",
            message=f"Resume with ID '{resume_id}' was not found.",
        )


class UserNotFoundError(AppException):
    def __init__(self, user_id: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            code="USER_NOT_FOUND",
            message=f"User with ID '{user_id}' was not found.",
        )


class ForbiddenResourceAccessError(AppException):
    def __init__(self, message: str = "You do not have permission to access this resource."):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            code="FORBIDDEN_RESOURCE_ACCESS",
            message=message,
        )
