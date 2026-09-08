import re
from typing import Any, Dict, List, Optional, Tuple
from app.schemas.application_draft import (
    ApplicationField,
    CandidateApplicationContext,
    FieldSource,
    FieldType,
)


class ApplicationFieldMapper:
    """
    Normalizes application form labels and maps them to canonical candidate facts.
    Maintains strict source provenance and never fabricates field values.
    """

    # Normalized canonical label patterns
    LABEL_PATTERNS: List[Tuple[str, str, FieldType]] = [
        (r"^(?:full\s*name|legal\s*name|candidate\s*name|name)$", "full_name", FieldType.TEXT),
        (r"^(?:first\s*name|given\s*name)$", "first_name", FieldType.TEXT),
        (r"^(?:last\s*name|surname|family\s*name)$", "last_name", FieldType.TEXT),
        (r"^(?:email|email\s*address|e-mail)$", "email", FieldType.EMAIL),
        (r"^(?:phone|phone\s*number|mobile|mobile\s*number|contact\s*number|cell)$", "phone", FieldType.PHONE),
        (r"^(?:location|city|address|current\s*city|current\s*location)$", "location", FieldType.TEXT),
        (r"^(?:linkedin|linkedin\s*(?:url|profile|link)?)$", "linkedin_url", FieldType.URL),
        (r"^(?:github|github\s*(?:url|profile|link)?)$", "github_url", FieldType.URL),
        (r"^(?:portfolio|website|personal\s*website|portfolio\s*(?:url|link)?)$", "portfolio_url", FieldType.URL),
        (r"^(?:resume|cv|upload\s*resume|attach\s*resume)$", "resume", FieldType.FILE),
    ]

    @staticmethod
    def _normalize_label(label: str) -> str:
        """Strips punctuation, lowercases, and collapses whitespace."""
        cleaned = re.sub(r"[^\w\s]", " ", label.lower())
        return " ".join(cleaned.split())

    def identify_canonical_field(self, label: str) -> Tuple[Optional[str], FieldType]:
        norm = self._normalize_label(label)
        for pattern, field_key, field_type in self.LABEL_PATTERNS:
            if re.search(pattern, norm):
                return field_key, field_type
        return None, FieldType.UNKNOWN

    def map_standard_fields(
        self,
        context: CandidateApplicationContext,
        field_specs: Optional[List[Dict[str, Any]]] = None,
        explicit_user_inputs: Optional[Dict[str, Any]] = None,
    ) -> List[ApplicationField]:
        """
        Maps a list of requested form field specifications to candidate facts.
        If field_specs is None, generates standard default fields.
        """
        user_inputs = explicit_user_inputs or {}
        mapped_fields: List[ApplicationField] = []

        # Default standard fields if none specified
        if not field_specs:
            field_specs = [
                {"field_id": "full_name", "label": "Full Name", "required": True},
                {"field_id": "email", "label": "Email Address", "required": True},
                {"field_id": "phone", "label": "Phone Number", "required": True},
                {"field_id": "location", "label": "Location", "required": False},
                {"field_id": "linkedin_url", "label": "LinkedIn Profile", "required": False},
                {"field_id": "github_url", "label": "GitHub Profile", "required": False},
                {"field_id": "portfolio_url", "label": "Portfolio URL", "required": False},
                {"field_id": "resume", "label": "Resume", "required": True},
            ]

        for spec in field_specs:
            field_id = spec.get("field_id") or spec.get("name", "")
            label = spec.get("label", field_id)
            required = spec.get("required", False)

            canonical_key, field_type = self.identify_canonical_field(label)
            if not canonical_key:
                canonical_key = field_id

            # 1. Check explicit user input (Top priority)
            if field_id in user_inputs or canonical_key in user_inputs:
                val = user_inputs.get(field_id, user_inputs.get(canonical_key))
                mapped_fields.append(
                    ApplicationField(
                        field_id=field_id,
                        label=label,
                        field_type=field_type if field_type != FieldType.UNKNOWN else FieldType.TEXT,
                        value=val,
                        source=FieldSource.USER_INPUT,
                        confidence=1.0,
                        required=required,
                    )
                )
                continue

            # 2. Candidate Context Values
            value = None
            source = FieldSource.UNKNOWN
            confidence = 1.0
            warning = None

            if canonical_key == "full_name":
                value = context.name
                source = FieldSource.CANDIDATE_PROFILE
            elif canonical_key == "first_name":
                parts = context.name.split() if context.name else []
                value = parts[0] if parts else None
                source = FieldSource.DERIVED
            elif canonical_key == "last_name":
                parts = context.name.split() if context.name else []
                value = " ".join(parts[1:]) if len(parts) > 1 else None
                source = FieldSource.DERIVED
            elif canonical_key == "email":
                value = context.email
                source = FieldSource.CANDIDATE_PROFILE
            elif canonical_key == "phone":
                value = context.phone
                source = FieldSource.CANDIDATE_PROFILE if context.phone else FieldSource.UNKNOWN
            elif canonical_key == "location":
                value = context.location
                source = FieldSource.CANDIDATE_PROFILE if context.location else FieldSource.UNKNOWN
            elif canonical_key == "linkedin_url":
                value = context.linkedin_url
                source = FieldSource.CANDIDATE_PROFILE if context.linkedin_url else FieldSource.UNKNOWN
            elif canonical_key == "github_url":
                value = context.github_url
                source = FieldSource.CANDIDATE_PROFILE if context.github_url else FieldSource.UNKNOWN
            elif canonical_key == "portfolio_url":
                value = context.portfolio_url
                source = FieldSource.CANDIDATE_PROFILE if context.portfolio_url else FieldSource.UNKNOWN
            elif canonical_key == "resume":
                value = "ATTACHED_RESUME"
                source = FieldSource.RESUME
            else:
                # Ambiguous / non-standard field
                value = None
                source = FieldSource.UNKNOWN
                confidence = 0.0
                warning = f"Field '{label}' is not standard or unmapped; user input required."

            mapped_fields.append(
                ApplicationField(
                    field_id=field_id,
                    label=label,
                    field_type=field_type if field_type != FieldType.UNKNOWN else FieldType.TEXT,
                    value=value,
                    source=source,
                    confidence=confidence if value is not None else 0.0,
                    required=required,
                    warning=warning,
                )
            )

        return mapped_fields
