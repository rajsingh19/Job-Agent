import io
import pytest
from fpdf import FPDF
from httpx import AsyncClient


def create_simple_pdf(name: str = "User A") -> bytes:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    pdf.cell(200, 10, text=f"{name}\nemail_{name.replace(' ', '')}@example.com\nPython Developer", new_x="LMARGIN", new_y="NEXT")
    buffer = io.BytesIO()
    pdf.output(buffer)
    return buffer.getvalue()


@pytest.mark.asyncio
async def test_multi_user_isolation_preventing_unauthorized_access(client: AsyncClient):
    """Verifies that User B cannot read or parse User A's resume."""
    headers_user_a = {"X-User-Id": "user_alpha"}
    headers_user_b = {"X-User-Id": "user_beta"}

    pdf_bytes = create_simple_pdf("Alpha User")
    upload_res = await client.post(
        "/api/v1/resumes",
        files={"file": ("alpha.pdf", pdf_bytes, "application/pdf")},
        headers=headers_user_a,
    )
    assert upload_res.status_code == 201
    resume_id = upload_res.json()["id"]

    # User B attempts to access User A's resume
    get_res = await client.get(f"/api/v1/resumes/{resume_id}", headers=headers_user_b)
    assert get_res.status_code == 403
    assert get_res.json()["detail"]["error"] == "FORBIDDEN_RESOURCE_ACCESS"

    # User B attempts to trigger parse on User A's resume
    parse_res = await client.post(f"/api/v1/resumes/{resume_id}/parse", headers=headers_user_b)
    assert parse_res.status_code == 403
    assert parse_res.json()["detail"]["error"] == "FORBIDDEN_RESOURCE_ACCESS"


@pytest.mark.asyncio
async def test_no_filesystem_internal_paths_leaked(client: AsyncClient):
    """Verifies that internal absolute filesystem paths are not exposed in API responses."""
    headers = {"X-User-Id": "user_gamma"}
    pdf_bytes = create_simple_pdf("Gamma User")

    upload_res = await client.post(
        "/api/v1/resumes",
        files={"file": ("gamma.pdf", pdf_bytes, "application/pdf")},
        headers=headers,
    )
    assert upload_res.status_code == 201
    data = upload_res.json()

    # file_reference should be a sanitized relative reference, not containing /home or root
    assert not data["file_reference"].startswith("/")
    assert not data["file_reference"].startswith("/home")
    assert not data["file_reference"].startswith("C:")
