from typing import Dict
from app.services.portal.models import PortalConfig


def get_greenhouse_config() -> PortalConfig:
    return PortalConfig(
        portal_id="greenhouse",
        name="Greenhouse",
        domain_patterns=[
            r"(?:boards|job-boards)\.greenhouse\.io",
            r"greenhouse\.io",
        ],
        url_patterns=[
            r"/jobs/\d+",
            r"/apply",
        ],
        login_url_patterns=[],
        form_selectors=[
            "#application_form",
            "form#application",
            "form[action*='greenhouse.io']",
            "form",
        ],
        next_selectors=[
            "button:has-text('Next')",
            "input[value='Next']",
            "a:has-text('Next Step')",
        ],
        submit_selectors=[
            "#submit_app",
            "button#submit_app",
            "input#submit_app",
            "button:has-text('Submit Application')",
            "input[type='submit'][value*='Submit']",
            "[data-testid='submit-application']",
        ],
        resume_selectors=[
            "input[type='file'][id*='resume']",
            "input[type='file'][name*='resume']",
            "input[type='file']",
            "[data-field='resume'] input[type='file']",
        ],
        confirmation_url_patterns=[
            r"/confirmation",
            r"/application/confirmation",
            r"/applied",
        ],
        confirmation_text_patterns=[
            r"thank\s+you\s+for\s+applying",
            r"application\s+submitted",
            r"your\s+application\s+has\s+been\s+submitted",
            r"we\s+have\s+received\s+your\s+application",
        ],
        confirmation_ref_patterns=[
            r"(?:confirmation|reference)\s*(?:#|no\.?|number|id|code)?(?:\s+is)?[:\s]+([A-Za-z0-9\-_]{4,30})",
            r"(?:application|submission)\s+(?:#|no\.?|number|id|code|ref)(?:\s+is)?[:\s]+([A-Za-z0-9\-_]{4,30})",
            r"(?:ref|conf)[:\s]+([A-Za-z0-9\-_]{4,30})",
        ],
        error_selectors=[
            ".field-error",
            ".error-message",
            "#error_explanation",
            "[aria-invalid='true']",
        ],
        challenge_selectors=[
            "div.g-recaptcha",
            "iframe[src*='recaptcha']",
            "iframe[src*='hcaptcha']",
            "iframe[src*='turnstile']",
        ],
        known_field_aliases={
            "first_name": ["first_name", "firstName", "first-name", "candidate_first_name"],
            "last_name": ["last_name", "lastName", "last-name", "candidate_last_name"],
            "email": ["email", "candidate_email", "email_address"],
            "phone": ["phone", "candidate_phone", "phone_number", "mobile_phone"],
            "resume": ["resume", "resume_file", "curriculum_vitae"],
            "cover_letter": ["cover_letter", "cover_letter_file", "notes"],
            "linkedin": ["linkedin", "linkedin_profile", "urls[LinkedIn]"],
            "github": ["github", "github_profile", "urls[GitHub]"],
            "portfolio": ["portfolio", "website", "urls[Portfolio]"],
        },
    )


def get_lever_config() -> PortalConfig:
    return PortalConfig(
        portal_id="lever",
        name="Lever",
        domain_patterns=[
            r"jobs\.lever\.co",
            r"lever\.co",
        ],
        url_patterns=[
            r"/apply$",
            r"/[a-f0-9\-]{36}/apply",
            r"/[a-f0-9\-]{36}",
        ],
        login_url_patterns=[],
        form_selectors=[
            "form#application-form",
            "form.application-form",
            "form[action*='lever.co']",
            "form",
        ],
        next_selectors=[
            "button:has-text('Next')",
            "button:has-text('Continue')",
        ],
        submit_selectors=[
            "#btn-submit",
            "button#btn-submit",
            "button[type='submit']",
            "button:has-text('Submit Application')",
            "button:has-text('Apply now')",
        ],
        resume_selectors=[
            "input[type='file'][name='resume']",
            "input[type='file'][id*='resume']",
            "input[type='file']",
            ".application-question[data-qa='resume'] input[type='file']",
        ],
        confirmation_url_patterns=[
            r"/thanks$",
            r"/thank-you",
            r"/confirmation",
        ],
        confirmation_text_patterns=[
            r"thank\s+you\s+for\s+applying",
            r"application\s+submitted",
            r"we\s+have\s+received\s+your\s+application",
            r"thanks\s+for\s+applying",
        ],
        confirmation_ref_patterns=[
            r"(?:confirmation|reference)\s*(?:#|no\.?|number|id|code)?(?:\s+is)?[:\s]+([A-Za-z0-9\-_]{4,30})",
            r"(?:application|submission)\s+(?:#|no\.?|number|id|code|ref)(?:\s+is)?[:\s]+([A-Za-z0-9\-_]{4,30})",
            r"(?:ref|conf)[:\s]+([A-Za-z0-9\-_]{4,30})",
        ],
        error_selectors=[
            ".error-message",
            ".application-error",
            "[data-qa='error']",
        ],
        challenge_selectors=[
            "div.g-recaptcha",
            "iframe[src*='recaptcha']",
            "iframe[src*='hcaptcha']",
            "iframe[src*='turnstile']",
        ],
        known_field_aliases={
            "full_name": ["name", "fullName", "candidate_name"],
            "email": ["email", "candidate_email"],
            "phone": ["phone", "candidate_phone"],
            "resume": ["resume", "resume_file"],
            "cover_letter": ["comments", "additional_info"],
            "linkedin": ["urls[LinkedIn]", "linkedin"],
            "github": ["urls[GitHub]", "github"],
            "portfolio": ["urls[Portfolio]", "urls[Other]", "portfolio"],
        },
    )


def get_ashby_config() -> PortalConfig:
    return PortalConfig(
        portal_id="ashby",
        name="Ashby",
        domain_patterns=[
            r"jobs\.ashbyhq\.com",
            r"ashbyhq\.com",
        ],
        url_patterns=[
            r"/application",
            r"/apply",
        ],
        login_url_patterns=[],
        form_selectors=[
            "form",
            "[data-testid='application-form']",
            "div.application-form-container",
        ],
        next_selectors=[
            "button:has-text('Next')",
            "button:has-text('Continue')",
            "[data-testid='next-step']",
        ],
        submit_selectors=[
            "button[type='submit']",
            "button:has-text('Submit Application')",
            "[data-testid='submit-application']",
            "button:has-text('Submit')",
        ],
        resume_selectors=[
            "input[type='file'][name*='resume']",
            "input[type='file']",
            "[data-testid='file-upload-input']",
        ],
        confirmation_url_patterns=[
            r"/application/submitted",
            r"/submitted",
            r"/thank-you",
        ],
        confirmation_text_patterns=[
            r"application\s+submitted",
            r"thank\s+you\s+for\s+applying",
            r"we've\s+received\s+your\s+application",
            r"your\s+application\s+was\s+submitted",
        ],
        confirmation_ref_patterns=[
            r"(?:confirmation|reference)\s*(?:#|no\.?|number|id|code)?(?:\s+is)?[:\s]+([A-Za-z0-9\-_]{4,30})",
            r"(?:application|submission)\s+(?:#|no\.?|number|id|code|ref)(?:\s+is)?[:\s]+([A-Za-z0-9\-_]{4,30})",
            r"(?:ref|conf)[:\s]+([A-Za-z0-9\-_]{4,30})",
        ],
        error_selectors=[
            "[data-testid='error-message']",
            ".error-banner",
            "[aria-invalid='true']",
        ],
        challenge_selectors=[
            "iframe[src*='recaptcha']",
            "iframe[src*='hcaptcha']",
            "iframe[src*='turnstile']",
            "div.cf-turnstile",
        ],
        known_field_aliases={
            "first_name": ["firstName", "first_name", "name.first"],
            "last_name": ["lastName", "last_name", "name.last"],
            "email": ["email", "emailAddress"],
            "phone": ["phoneNumber", "phone"],
            "resume": ["resume", "resumeFile"],
            "linkedin": ["linkedInUrl", "linkedin"],
            "github": ["githubUrl", "github"],
            "portfolio": ["portfolioUrl", "website"],
        },
    )


def get_generic_ats_config() -> PortalConfig:
    return PortalConfig(
        portal_id="generic_ats",
        name="Generic ATS",
        domain_patterns=[],
        url_patterns=[],
        login_url_patterns=[
            r"/login",
            r"/signin",
            r"/sign-in",
            r"/auth",
            r"/session/new",
        ],
        form_selectors=[
            "form",
            "[role='form']",
        ],
        next_selectors=[
            "button:has-text('Next')",
            "button:has-text('Continue')",
            "input[type='button'][value*='Next']",
            "a:has-text('Next')",
        ],
        submit_selectors=[
            "button:has-text('Submit Application')",
            "button:has-text('Submit application')",
            "button:has-text('Submit')",
            "input[type='submit']",
            "button[type='submit']",
            "button:has-text('Complete Application')",
            "button:has-text('Apply Now')",
        ],
        resume_selectors=[
            "input[type='file'][name*='resume']",
            "input[type='file'][id*='resume']",
            "input[type='file'][accept*='pdf']",
            "input[type='file']",
        ],
        confirmation_url_patterns=[
            r"/thank[s\-_]?you",
            r"/confirmation",
            r"/submitted",
            r"/application[_\-]received",
            r"/applied",
            r"/success",
        ],
        confirmation_text_patterns=[
            r"thank\s+you\s+for\s+(?:your\s+)?application",
            r"thank\s+you\s+for\s+applying",
            r"application\s+(?:has\s+been\s+)?submitted",
            r"application\s+received",
            r"we(?:'ve|\s+have)\s+received\s+your\s+application",
            r"your\s+application\s+was\s+submitted",
            r"thanks\s+for\s+applying",
            r"congratulations[,\s]+your\s+application",
            r"successfully\s+applied",
        ],
        confirmation_ref_patterns=[
            r"(?:confirmation|reference)\s*(?:#|no\.?|number|id|code)?(?:\s+is)?[:\s]+([A-Za-z0-9\-_]{4,30})",
            r"(?:application|submission)\s+(?:#|no\.?|number|id|code|ref)(?:\s+is)?[:\s]+([A-Za-z0-9\-_]{4,30})",
            r"(?:ref|conf)[:\s]+([A-Za-z0-9\-_]{4,30})",
        ],
        error_selectors=[
            "[aria-invalid='true']",
            ".error-message",
            ".invalid-feedback",
            ".alert-danger",
        ],
        challenge_selectors=[
            "iframe[src*='recaptcha']",
            "iframe[src*='hcaptcha']",
            "iframe[src*='turnstile']",
            "iframe[src*='challenges.cloudflare.com']",
            "div.g-recaptcha",
            "div.h-captcha",
            "div.cf-turnstile",
        ],
        known_field_aliases={
            "first_name": ["first_name", "firstName", "fname", "first-name"],
            "last_name": ["last_name", "lastName", "lname", "last-name"],
            "full_name": ["name", "fullName", "full_name", "candidate_name"],
            "email": ["email", "email_address", "user_email"],
            "phone": ["phone", "phone_number", "telephone", "mobile"],
            "resume": ["resume", "cv", "file_cv", "resume_file"],
            "linkedin": ["linkedin", "linkedin_url"],
        },
    )


PORTAL_CONFIGS: Dict[str, PortalConfig] = {
    "greenhouse": get_greenhouse_config(),
    "lever": get_lever_config(),
    "ashby": get_ashby_config(),
    "generic_ats": get_generic_ats_config(),
}
