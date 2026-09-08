import logging
import re
from urllib.parse import urlparse
from typing import List, Optional, Tuple
from app.models.enums import ATSProvider
from app.models.job import JobPosting
from app.schemas.connector import ATSDetectionResult, PlatformType

logger = logging.getLogger(__name__)


class ATSDetector:
    """
    Deterministic detection engine for identifying ATS providers and job application platforms.
    Evaluates apply URLs, source URLs, source metadata, and ATS provider fields with signal conflict tracking.
    """

    # Domain to platform mapping
    DOMAIN_RULES = [
        # Major ATS Platforms
        (r"(?:boards|job-boards)\.greenhouse\.io", PlatformType.GREENHOUSE, 0.98),
        (r"greenhouse\.io", PlatformType.GREENHOUSE, 0.95),
        (r"jobs\.lever\.co", PlatformType.LEVER, 0.98),
        (r"lever\.co", PlatformType.LEVER, 0.95),
        (r"jobs\.ashbyhq\.com", PlatformType.ASHBY, 0.98),
        (r"ashbyhq\.com", PlatformType.ASHBY, 0.95),
        # Major Job Boards
        (r"(?:www\.)?linkedin\.com", PlatformType.LINKEDIN, 0.95),
        (r"(?:www\.)?internshala\.com", PlatformType.INTERNSHALA, 0.95),
        (r"(?:www\.)?naukri\.com", PlatformType.NAUKRI, 0.95),
        (r"(?:www\.)?shine\.com", PlatformType.SHINE, 0.95),
        (r"(?:www\.)?(?:wellfound\.com|angel\.co)", PlatformType.WELLFOUND, 0.95),
        # Generic ATS Platforms (Workday, BambooHR, SmartRecruiters, iCIMS)
        (r"myworkdayjobs\.com", PlatformType.GENERIC_ATS, 0.90),
        (r"bamboohr\.com", PlatformType.GENERIC_ATS, 0.90),
        (r"smartrecruiters\.com", PlatformType.GENERIC_ATS, 0.90),
        (r"icims\.com", PlatformType.GENERIC_ATS, 0.90),
    ]

    # Source string to platform mapping
    SOURCE_RULES = {
        "greenhouse": PlatformType.GREENHOUSE,
        "lever": PlatformType.LEVER,
        "ashby": PlatformType.ASHBY,
        "linkedin": PlatformType.LINKEDIN,
        "internshala": PlatformType.INTERNSHALA,
        "naukri": PlatformType.NAUKRI,
        "shine": PlatformType.SHINE,
        "wellfound": PlatformType.WELLFOUND,
        "workday": PlatformType.GENERIC_ATS,
        "bamboohr": PlatformType.GENERIC_ATS,
        "generic_browser": PlatformType.BROWSER,
        "browser": PlatformType.BROWSER,
    }

    @staticmethod
    def _extract_domain(url: Optional[str]) -> str:
        """Safely extracts domain / netloc from URL string."""
        if not url or not isinstance(url, str) or not url.strip():
            return ""
        try:
            # Prepend scheme if missing for urlparse
            parsed = urlparse(url if "://" in url else f"https://{url}")
            return (parsed.netloc or "").lower()
        except Exception:
            return ""

    def detect_platform(self, job: JobPosting) -> ATSDetectionResult:
        """
        Detects the job platform and returns a structured ATSDetectionResult.
        Evaluates signals in deterministic priority and tracks signal conflicts.
        """
        signals: List[str] = []
        warnings: List[str] = []

        apply_domain = self._extract_domain(job.apply_url)
        source_domain = self._extract_domain(job.source_url)
        source_str = (job.source or "").lower().strip()
        ats_str = (job.ats_provider or "").lower().strip()

        # Step 1: Detect from Apply URL (Primary signal)
        url_platform: Optional[PlatformType] = None
        url_conf: float = 0.0

        if apply_domain:
            for pattern, plat, conf in self.DOMAIN_RULES:
                if re.search(pattern, apply_domain):
                    url_platform = plat
                    url_conf = conf
                    signals.append(f"apply_url_domain={apply_domain} -> {plat.value}")
                    break

        # Step 2: Detect from Source URL (Secondary domain signal)
        if not url_platform and source_domain:
            for pattern, plat, conf in self.DOMAIN_RULES:
                if re.search(pattern, source_domain):
                    url_platform = plat
                    url_conf = conf * 0.90  # Slightly lower confidence for secondary URL
                    signals.append(f"source_url_domain={source_domain} -> {plat.value}")
                    break

        # Step 3: Detect from Source & ATS Metadata
        meta_platform: Optional[PlatformType] = None
        if source_str in self.SOURCE_RULES:
            meta_platform = self.SOURCE_RULES[source_str]
            signals.append(f"source_metadata={source_str} -> {meta_platform.value}")
        elif ats_str and ats_str != ATSProvider.UNKNOWN.value.lower() and ats_str in self.SOURCE_RULES:
            meta_platform = self.SOURCE_RULES[ats_str]
            signals.append(f"ats_provider={ats_str} -> {meta_platform.value}")

        # Step 4: Reconcile and Determine Final Platform
        if url_platform and meta_platform:
            if url_platform == meta_platform or meta_platform == PlatformType.BROWSER:
                # Strong consensus or domain refinement over generic browser source
                final_platform = url_platform
                final_conf = min(0.99, max(url_conf, 0.95))
            else:
                # Conflicting signals: URL domain takes precedence over declared source string
                final_platform = url_platform
                final_conf = max(0.65, url_conf - 0.20)
                warning_msg = (
                    f"Conflicting signals detected: apply_url indicates '{url_platform.value}' "
                    f"while source metadata indicates '{meta_platform.value}'. Prioritizing apply_url."
                )
                warnings.append(warning_msg)
                signals.append(f"conflict=resolved_to_{url_platform.value}")
        elif url_platform:
            final_platform = url_platform
            final_conf = url_conf
        elif meta_platform:
            final_platform = meta_platform
            final_conf = 0.85
        else:
            # Fallback detection
            if job.apply_url and job.apply_url.startswith("http"):
                final_platform = PlatformType.BROWSER
                final_conf = 0.70
                signals.append(f"generic_url={apply_domain or 'http'} -> browser")
            else:
                final_platform = PlatformType.UNKNOWN
                final_conf = 0.30
                warnings.append("No recognized ATS domain or valid apply URL found.")
                signals.append("no_recognized_signals -> unknown")

        # Determine browser requirement
        requires_browser = final_platform in {
            PlatformType.LINKEDIN,
            PlatformType.INTERNSHALA,
            PlatformType.NAUKRI,
            PlatformType.SHINE,
            PlatformType.WELLFOUND,
            PlatformType.BROWSER,
            PlatformType.GENERIC_ATS,
            PlatformType.UNKNOWN,
        }

        return ATSDetectionResult(
            platform=final_platform,
            confidence=round(final_conf, 2),
            signals=signals,
            warnings=warnings,
            requires_browser=requires_browser,
        )
