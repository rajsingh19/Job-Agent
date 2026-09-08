from app.schemas.application_draft import (
    CandidateApplicationContext,
    FieldSource,
    FieldType,
)
from app.services.applications.field_mapper import ApplicationFieldMapper


def test_standard_field_mapping_common_labels():
    mapper = ApplicationFieldMapper()
    context = CandidateApplicationContext(
        name="Samantha Jones",
        email="samantha.jones@example.com",
        phone="+1-555-9876",
        location="New York, NY",
        linkedin_url="https://linkedin.com/in/sjones",
        github_url="https://github.com/sjones",
        portfolio_url="https://sjones.dev",
        skills=["Python", "FastAPI"],
    )

    fields = mapper.map_standard_fields(context)
    field_dict = {f.field_id: f for f in fields}

    assert field_dict["full_name"].value == "Samantha Jones"
    assert field_dict["full_name"].source == FieldSource.CANDIDATE_PROFILE
    assert field_dict["full_name"].confidence == 1.0

    assert field_dict["email"].value == "samantha.jones@example.com"
    assert field_dict["email"].field_type == FieldType.EMAIL

    assert field_dict["phone"].value == "+1-555-9876"
    assert field_dict["phone"].field_type == FieldType.PHONE

    assert field_dict["linkedin_url"].value == "https://linkedin.com/in/sjones"
    assert field_dict["github_url"].value == "https://github.com/sjones"
    assert field_dict["portfolio_url"].value == "https://sjones.dev"


def test_field_mapping_user_input_override():
    mapper = ApplicationFieldMapper()
    context = CandidateApplicationContext(
        name="Original Name",
        email="original@example.com",
        skills=[],
    )

    explicit_inputs = {
        "full_name": "Overridden Name",
        "phone": "+1-555-1111",
    }

    fields = mapper.map_standard_fields(
        context=context,
        explicit_user_inputs=explicit_inputs,
    )
    field_dict = {f.field_id: f for f in fields}

    assert field_dict["full_name"].value == "Overridden Name"
    assert field_dict["full_name"].source == FieldSource.USER_INPUT

    assert field_dict["phone"].value == "+1-555-1111"
    assert field_dict["phone"].source == FieldSource.USER_INPUT


def test_field_mapping_name_derivation():
    mapper = ApplicationFieldMapper()
    context = CandidateApplicationContext(
        name="Grace Brewster Hopper",
        email="hopper@navy.mil",
        skills=[],
    )

    custom_specs = [
        {"field_id": "first_name", "label": "First Name", "required": True},
        {"field_id": "last_name", "label": "Last Name", "required": True},
    ]

    fields = mapper.map_standard_fields(context, field_specs=custom_specs)
    field_dict = {f.field_id: f for f in fields}

    assert field_dict["first_name"].value == "Grace"
    assert field_dict["first_name"].source == FieldSource.DERIVED

    assert field_dict["last_name"].value == "Brewster Hopper"
    assert field_dict["last_name"].source == FieldSource.DERIVED


def test_field_mapping_unknown_ambiguous_fields():
    mapper = ApplicationFieldMapper()
    context = CandidateApplicationContext(
        name="Candidate",
        email="cand@example.com",
        skills=[],
    )

    custom_specs = [
        {"field_id": "secret_clearance", "label": "Government Security Clearance Level", "required": True},
    ]

    fields = mapper.map_standard_fields(context, field_specs=custom_specs)
    f = fields[0]

    assert f.value is None
    assert f.source == FieldSource.UNKNOWN
    assert f.confidence == 0.0
    assert "not standard or unmapped" in f.warning
