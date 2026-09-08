import re
from typing import List, Optional, Tuple
from app.services.submission.models import ConfirmationStatus


class SubmissionConfirmationDetector:
    """
    Detects portal-level confirmation of job application submission.
    Scans URL patterns, DOM success banners, confirmation reference codes,
    and flags ambiguities or residual form errors.
    """

    SUCCESS_URL_PATTERNS = [
        re.compile(r"/thank[s\-_]?you", re.IGNORECASE),
        re.compile(r"/confirmation", re.IGNORECASE),
        re.compile(r"/submitted", re.IGNORECASE),
        re.compile(r"/application[_\-]received", re.IGNORECASE),
        re.compile(r"/applied", re.IGNORECASE),
        re.compile(r"/success", re.IGNORECASE),
    ]

    SUCCESS_TEXT_PATTERNS = [
        re.compile(r"thank\s+you\s+for\s+(?:your\s+)?application", re.IGNORECASE),
        re.compile(r"thank\s+you\s+for\s+applying", re.IGNORECASE),
        re.compile(r"application\s+(?:has\s+been\s+)?submitted", re.IGNORECASE),
        re.compile(r"application\s+received", re.IGNORECASE),
        re.compile(r"we(?:'ve|\s+have)\s+received\s+your\s+application", re.IGNORECASE),
        re.compile(r"your\s+application\s+was\s+submitted", re.IGNORECASE),
        re.compile(r"thanks\s+for\s+applying", re.IGNORECASE),
        re.compile(r"congratulations[,\s]+your\s+application", re.IGNORECASE),
        re.compile(r"successfully\s+applied", re.IGNORECASE),
    ]

    ERROR_TEXT_PATTERNS = [
        re.compile(r"please\s+correct\s+the\s+errors", re.IGNORECASE),
        re.compile(r"please\s+fix\s+the\s+following\s+errors", re.IGNORECASE),
        re.compile(r"there\s+was\s+a\s+problem\s+submitting", re.IGNORECASE),
        re.compile(r"error\s+submitting\s+application", re.IGNORECASE),
        re.compile(r"this\s+field\s+is\s+required", re.IGNORECASE),
        re.compile(r"submission\s+failed", re.IGNORECASE),
    ]

    CONFIRMATION_REF_PATTERNS = [
        re.compile(
            r"(?:confirmation|reference)\s*(?:#|no\.?|number|id|code)?(?:\s+is)?[:\s]+([A-Za-z0-9\-_]{4,30})",
            re.IGNORECASE,
        ),
        re.compile(
            r"(?:application|submission)\s+(?:#|no\.?|number|id|code|ref)(?:\s+is)?[:\s]+([A-Za-z0-9\-_]{4,30})",
            re.IGNORECASE,
        ),
        re.compile(
            r"(?:ref|conf)[:\s]+([A-Za-z0-9\-_]{4,30})",
            re.IGNORECASE,
        ),
    ]

    @classmethod
    def detect_from_content(
        cls,
        url: str,
        page_text: str,
    ) -> Tuple[ConfirmationStatus, Optional[str], Optional[str], List[str]]:
        """
        Pure evaluation of page URL and text for submission confirmation.
        Returns:
            (status, confirmation_type, confirmation_reference, warnings)
        """
        warnings: List[str] = []

        # 1. Check for explicit error text first
        for err_pattern in cls.ERROR_TEXT_PATTERNS:
            if err_pattern.search(page_text):
                return (
                    ConfirmationStatus.NOT_CONFIRMED,
                    "ERROR_BANNER_DETECTED",
                    None,
                    ["Form errors or validation messages detected on page after submit click."],
                )

        # 2. Extract reference / confirmation number
        confirmation_ref: Optional[str] = None
        for ref_pattern in cls.CONFIRMATION_REF_PATTERNS:
            match = ref_pattern.search(page_text)
            if match:
                confirmation_ref = match.group(1).strip()
                break

        # 3. Check for text matches
        matched_text = False
        for text_pattern in cls.SUCCESS_TEXT_PATTERNS:
            if text_pattern.search(page_text):
                matched_text = True
                break

        # 4. Check for URL match
        matched_url = False
        for url_pattern in cls.SUCCESS_URL_PATTERNS:
            if url_pattern.search(url):
                matched_url = True
                break

        if matched_text and matched_url:
            return (
                ConfirmationStatus.CONFIRMED,
                "URL_AND_TEXT_CONFIRMATION",
                confirmation_ref,
                warnings,
            )
        elif matched_text:
            return (
                ConfirmationStatus.CONFIRMED,
                "TEXT_CONFIRMATION",
                confirmation_ref,
                warnings,
            )
        elif matched_url:
            return (
                ConfirmationStatus.CONFIRMED,
                "URL_CONFIRMATION",
                confirmation_ref,
                warnings,
            )
        else:
            # Ambiguous state: submit was clicked, but neither success nor error was clearly detected
            warnings.append(
                "Neither explicit confirmation message nor form error detected. Requires human verification."
            )
            return (
                ConfirmationStatus.UNKNOWN,
                "AMBIGUOUS_POST_SUBMISSION",
                confirmation_ref,
                warnings,
            )

    @classmethod
    async def detect_from_page(
        cls,
        page: any,
    ) -> Tuple[ConfirmationStatus, Optional[str], Optional[str], List[str]]:
        """
        Extracts URL and visible text from Playwright Page and detects confirmation.
        """
        url = page.url or ""
        try:
            # Extract visible body text
            body_text = await page.inner_text("body", timeout=5000)
        except Exception:
            try:
                body_text = await page.content()
            except Exception:
                body_text = ""

        return cls.detect_from_content(url=url, page_text=body_text)
