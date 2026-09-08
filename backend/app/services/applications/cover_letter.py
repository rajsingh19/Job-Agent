import logging
from typing import Optional, Tuple
from app.models.job import JobPosting
from app.schemas.application_draft import CandidateApplicationContext
from app.services.ai.provider import LLMProvider, get_llm_provider

logger = logging.getLogger(__name__)


class CoverLetterGenerator:
    """
    Generates tailored, truthful cover letters grounded strictly in candidate facts.
    Never invents employers, dates, qualifications, or absent technologies.
    """

    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        self.llm_provider = llm_provider or get_llm_provider()

    async def generate_cover_letter(
        self,
        context: CandidateApplicationContext,
        job: JobPosting,
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Generates a concise, professional cover letter tailored to the job.
        Returns: (cover_letter_text, warning_if_fallback)
        """
        try:
            skills_str = ", ".join(context.skills[:8]) if context.skills else "software engineering"
            recent_role = (
                context.experience[0].get("role", "Engineer") if context.experience else "software developer"
            )
            top_project = (
                context.projects[0].get("name", "") if context.projects else ""
            )

            prompt = (
                f"Candidate Name: {context.name}\n"
                f"Recent Role: {recent_role}\n"
                f"Core Skills: {skills_str}\n"
                f"Notable Project: {top_project}\n"
                f"Applying for: {job.title} at {job.company}\n\n"
                f"Instruction: Write a concise, 3-paragraph professional cover letter from {context.name} applying for {job.title} at {job.company}. "
                f"Highlight the candidate's real skills ({skills_str}) and interest in {job.company}. "
                f"Strict Rule: NEVER invent any companies, degrees, dates, or technologies not listed above."
            )
            system_prompt = (
                "You are an expert executive cover letter writer. Ground every claim strictly in candidate facts."
            )

            letter = await self.llm_provider.generate_text(prompt=prompt, system_prompt=system_prompt)
            clean_letter = letter.strip()
            return clean_letter, None

        except Exception as e:
            logger.warning(f"Cover letter generation failed or provider unavailable: {e}")
            # Resilient fallback: return None with warning so application drafting succeeds
            return None, "Cover letter generation unavailable; AI service offline or unconfigured."
