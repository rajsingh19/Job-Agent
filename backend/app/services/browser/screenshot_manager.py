import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional
from app.config import get_settings
from app.services.browser.models import ScreenshotMetadata

logger = logging.getLogger(__name__)


class ScreenshotManager:
    """
    Captures and stores visual execution checkpoints.
    Saves image artifacts with UUIDs in the screenshots directory and maintains safe metadata.
    """

    @classmethod
    async def capture_checkpoint(
        cls,
        page,
        step: str,
        application_id: str,
    ) -> Optional[ScreenshotMetadata]:
        """
        Captures full-page screenshot at a designated workflow checkpoint.
        """
        settings = get_settings()
        if not settings.browser_screenshot_enabled:
            return None

        try:
            screenshots_dir = settings.screenshots_dir.resolve()
            screenshots_dir.mkdir(parents=True, exist_ok=True)

            screenshot_id = f"scr_{uuid.uuid4().hex[:12]}"
            filename = f"{application_id}_{step}_{screenshot_id}.png"
            file_path = screenshots_dir / filename

            if hasattr(page, "screenshot"):
                await page.screenshot(path=str(file_path), full_page=True)

            url = page.url if hasattr(page, "url") else ""

            metadata = ScreenshotMetadata(
                id=screenshot_id,
                step=step,
                url=url,
                timestamp=datetime.now(timezone.utc),
                filename=filename,
                relative_path=f"storage/screenshots/{filename}",
            )
            logger.info("Captured screenshot checkpoint '%s' at %s", step, file_path)
            return metadata

        except Exception as e:
            logger.warning("Failed to capture screenshot checkpoint '%s': %s", step, e)
            return None
