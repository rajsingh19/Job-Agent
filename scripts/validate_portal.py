#!/usr/bin/env python3
"""
scripts/validate_portal.py

Manual developer validation tooling for inspecting and verifying real-world ATS portals.
Allows launching an interactive Playwright session to inspect:
- Portal adapter detection
- Form discovery & fields
- Navigation steps
- Challenge & authentication states
- Diagnostics capture

STRICT SAFETY INVARIANT:
This tool NEVER bypasses the Phase 8 human approval boundary. It CANNOT submit an application
without explicit Phase 8 authorization.
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.services.browser.auth_detector import AuthDetector
from app.services.browser.challenge_detector import ChallengeDetector
from app.services.browser.form_parser import FormParser
from app.services.portal.diagnostics import PortalDiagnosticsCollector
from app.services.portal.registry import PortalRegistry

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("validate_portal")


async def validate_portal_url(url: str, headless: bool = False):
    logger.info("Starting portal validation for target URL: %s", url)
    registry = PortalRegistry.get_instance()
    adapter = registry.get_adapter_for_url(url)

    logger.info("=" * 60)
    logger.info("PORTAL DETECTION:")
    logger.info("  Detected Portal: %s (%s)", adapter.name, adapter.portal_id)
    caps = adapter.capabilities()
    logger.info("  Supports Multi-Step: %s", caps.supports_multi_step_forms)
    logger.info("  Supports Resume Upload: %s", caps.supports_resume_upload)
    logger.info("  Known Confirmation: %s", caps.has_known_confirmation_patterns)
    logger.info("=" * 60)

    try:
        from playwright.async_api import async_playwright
    except ImportError:
        logger.error("Playwright is not installed. Please install playwright to run headed inspection.")
        return

    async with async_playwright() as p:
        logger.info("Launching browser (headless=%s)...", headless)
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context()
        page = await context.new_page()

        logger.info("Navigating to target URL...")
        try:
            await page.goto(url, timeout=30000, wait_until="domcontentloaded")
            logger.info("Navigation complete. Current URL: %s", page.url)
        except Exception as e:
            logger.error("Failed to navigate: %s", e)
            await browser.close()
            return

        # 1. Check Authentication Status
        auth_status = await AuthDetector.detect_auth_status(page)
        logger.info("AUTHENTICATION STATE: %s", auth_status.value)

        # 2. Check Security Challenges
        challenge_type, challenge_msg = await ChallengeDetector.detect_challenge(page)
        logger.info("SECURITY CHALLENGE STATE: %s (%s)", challenge_type.value, challenge_msg or "None")

        # 3. Inspect Form Fields
        discovered_form = await FormParser.parse_form(page, form_id="validation_form")
        logger.info("=" * 60)
        logger.info("DISCOVERED FORM INSPECTION:")
        logger.info("  Total Fields: %d", len(discovered_form.fields))
        logger.info("  Step Index: %d (Total Steps: %s)", discovered_form.step_index, discovered_form.total_steps)
        logger.info("  Has Next Control: %s", discovered_form.has_next_button)
        logger.info("  Has Submit Control: %s", discovered_form.has_submit_button)
        logger.info("-" * 60)
        for i, field in enumerate(discovered_form.fields, 1):
            logger.info("  [%d] id='%s' name='%s' type='%s' required=%s selector='%s'",
                        i, field.field_id, field.name, field.input_type, field.required, field.selector)
        logger.info("=" * 60)

        # 4. Diagnostics Collection
        step_info = await adapter.detect_current_step(page)
        diagnostics = PortalDiagnosticsCollector.collect_diagnostics(
            portal_id=adapter.portal_id,
            portal_name=adapter.name,
            current_url=page.url,
            step_info=step_info,
            form=discovered_form,
            auth_state=auth_status.value,
            challenge_state=challenge_type.value,
        )
        logger.info("DIAGNOSTICS SUMMARY:")
        logger.info("  Portal: %s", diagnostics.portal_id)
        logger.info("  Domain: %s", diagnostics.url_domain)
        logger.info("  Missing Required: %s", diagnostics.missing_required_fields)
        logger.info("=" * 60)

        logger.info("SAFETY BOUNDARY REMINDER: No automated submission will be executed.")
        logger.info("Press Enter in terminal or close browser window to exit.")
        if not headless:
            try:
                await page.wait_for_timeout(5000)
            except Exception:
                pass

        await browser.close()
        logger.info("Portal validation session finished successfully.")


def main():
    parser = argparse.ArgumentParser(description="Validate portal compatibility and field inspection.")
    parser.add_argument("url", help="Job application URL to validate")
    parser.add_argument("--headless", action="store_true", help="Run in headless mode")
    args = parser.parse_args()

    asyncio.run(validate_portal_url(url=args.url, headless=args.headless))


if __name__ == "__main__":
    main()
