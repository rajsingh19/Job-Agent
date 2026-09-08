import io
import pytest
from fpdf import FPDF
from httpx import AsyncClient


def create_pdf_with_location(name: str, email: str, location: str) -> bytes:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    content = f"{name}\nEmail: {email}\nLocation: {location}\nSkills: Python, FastAPI"
    for line in content.split("\n"):
        pdf.cell(200, 10, text=line, new_x="LMARGIN", new_y="NEXT")
    buffer = io.BytesIO()
    pdf.output(buffer)
    return buffer.getvalue()


@pytest.mark.asyncio
async def test_preferences_crud(client: AsyncClient):
    headers = {"X-User-Id": "user_pref_test_1"}

    # 1. Get default preferences
    get_res = await client.get("/api/v1/preferences", headers=headers)
    assert get_res.status_code == 200
    pref_data = get_res.json()
    assert pref_data["remote_preference"] == "ANY"
    assert pref_data["target_roles"] == []

    # 2. Update preferences
    update_payload = {
        "target_roles": ["Software Engineer", "Backend Developer"],
        "preferred_locations": ["Bangalore", "Remote"],
        "remote_preference": "REMOTE",
        "minimum_stipend": 50000.0,
        "required_skills": ["Python", "FastAPI"],
        "excluded_companies": ["SpamCo"],
    }
    put_res = await client.put("/api/v1/preferences", json=update_payload, headers=headers)
    assert put_res.status_code == 200
    updated = put_res.json()
    assert updated["remote_preference"] == "REMOTE"
    assert "Bangalore" in updated["preferred_locations"]
    assert "SpamCo" in updated["excluded_companies"]


@pytest.mark.asyncio
async def test_combined_candidate_profile_and_non_overwriting(client: AsyncClient):
    """
    CRITICAL TEST:
    Resume contains: Location: Delhi
    User Preferences contain: Preferred Locations: ['Bangalore']
    Verify that CandidateProfile preserves both independently and resume parsing
    NEVER overwrites user preferences.
    """
    headers = {"X-User-Id": "user_independence_test_2"}

    # Set authoritative user preferences
    pref_payload = {
        "target_roles": ["Backend Engineer"],
        "preferred_locations": ["Bangalore"],
        "remote_preference": "HYBRID",
        "minimum_stipend": 75000.0,
    }
    await client.put("/api/v1/preferences", json=pref_payload, headers=headers)

    # Upload and parse a resume that states Delhi
    resume_bytes = create_pdf_with_location("Rohit Sharma", "rohit@example.com", "Delhi")
    upload_res = await client.post(
        "/api/v1/resumes",
        files={"file": ("rohit_resume.pdf", resume_bytes, "application/pdf")},
        headers=headers,
    )
    assert upload_res.status_code == 201
    resume_id = upload_res.json()["id"]

    await client.post(f"/api/v1/resumes/{resume_id}/parse", headers=headers)

    # Fetch combined profile
    profile_res = await client.get("/api/v1/profile", headers=headers)
    assert profile_res.status_code == 200
    candidate_profile = profile_res.json()

    # Verify both sources remain independent and authoritative
    assert candidate_profile["preferences"]["preferred_locations"] == ["Bangalore"]
    assert candidate_profile["preferences"]["remote_preference"] == "HYBRID"
    assert candidate_profile["resume_profile"]["email"] == "rohit@example.com"
