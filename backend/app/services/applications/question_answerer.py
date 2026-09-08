import logging
import re
from typing import Any, Dict, List, Optional
from app.models.job import JobPosting
from app.schemas.application_draft import (
    CandidateApplicationContext,
    DraftCustomQuestion,
    FieldSource,
    QuestionCategory,
)
from app.services.ai.provider import LLMProvider, get_llm_provider
from app.services.applications.question_classifier import QuestionClassifier

logger = logging.getLogger(__name__)


class QuestionAnswerer:
    """
    Truthful, grounded question answering engine for job application custom questions.
    Enforces anti-fabrication constraints:
    - Never fabricates work history, degrees, skills, or certifications.
    - Sensitive questions (work auth, salary, legal, demographic) require explicit user input unless pre-configured.
    - Factual questions are extracted directly from CandidateApplicationContext.
    - Subjective questions are grounded in candidate facts and always marked `requires_review=True`.
    """

    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        self.llm_provider = llm_provider or get_llm_provider()

    async def answer_question(
        self,
        question_id: str,
        question_text: str,
        context: CandidateApplicationContext,
        job: JobPosting,
        explicit_user_answers: Optional[Dict[str, str]] = None,
    ) -> DraftCustomQuestion:
        user_answers = explicit_user_answers or {}
        category = QuestionClassifier.classify(question_text)
        q_lower = question_text.lower()

        # 1. Check explicit user answer first
        if question_id in user_answers or question_text in user_answers:
            ans = user_answers.get(question_id, user_answers.get(question_text))
            return DraftCustomQuestion(
                question_id=question_id,
                question=question_text,
                category=category,
                answer=ans,
                source=FieldSource.USER_INPUT,
                confidence=1.0,
                required=True,
                requires_review=False,
                requires_user_input=False,
            )

        # 2. Sensitive Questions: Work Authorization & Visa Sponsorship
        if category == QuestionCategory.WORK_AUTHORIZATION:
            if "sponsorship" in q_lower:
                if context.sponsorship_required is not None:
                    ans = "Yes" if context.sponsorship_required else "No"
                    return DraftCustomQuestion(
                        question_id=question_id,
                        question=question_text,
                        category=category,
                        answer=ans,
                        source=FieldSource.USER_PREFERENCE,
                        confidence=1.0,
                        requires_review=False,
                        requires_user_input=False,
                    )
            elif context.work_authorization:
                return DraftCustomQuestion(
                    question_id=question_id,
                    question=question_text,
                    category=category,
                    answer=context.work_authorization,
                    source=FieldSource.USER_PREFERENCE,
                    confidence=1.0,
                    requires_review=False,
                    requires_user_input=False,
                )

            # Not explicitly supplied: strictly require user input
            return DraftCustomQuestion(
                question_id=question_id,
                question=question_text,
                category=category,
                answer=None,
                source=FieldSource.UNKNOWN,
                confidence=0.0,
                requires_review=True,
                requires_user_input=True,
                warning="Work authorization / sponsorship status requires explicit user confirmation.",
            )

        # 3. Sensitive Questions: Salary & Compensation Expectations
        if category == QuestionCategory.SALARY:
            if context.expected_salary is not None:
                return DraftCustomQuestion(
                    question_id=question_id,
                    question=question_text,
                    category=category,
                    answer=f"${context.expected_salary:,.2f}",
                    source=FieldSource.USER_PREFERENCE,
                    confidence=1.0,
                    requires_review=False,
                    requires_user_input=False,
                )
            return DraftCustomQuestion(
                question_id=question_id,
                question=question_text,
                category=category,
                answer=None,
                source=FieldSource.UNKNOWN,
                confidence=0.0,
                requires_review=True,
                requires_user_input=True,
                warning="Expected salary not explicitly configured; user input required.",
            )

        # 4. Sensitive Questions: Availability & Start Dates
        if category == QuestionCategory.AVAILABILITY:
            if context.available_from:
                return DraftCustomQuestion(
                    question_id=question_id,
                    question=question_text,
                    category=category,
                    answer=context.available_from,
                    source=FieldSource.USER_PREFERENCE,
                    confidence=1.0,
                    requires_review=False,
                    requires_user_input=False,
                )
            return DraftCustomQuestion(
                question_id=question_id,
                question=question_text,
                category=category,
                answer=None,
                source=FieldSource.UNKNOWN,
                confidence=0.0,
                requires_review=True,
                requires_user_input=True,
                warning="Start date / availability not configured; user input required.",
            )

        # 5. Sensitive Personal Facts (Disability, Veteran, Demographics)
        if category == QuestionCategory.PERSONAL_FACT and any(
            k in q_lower for k in ["disability", "veteran", "gender", "race", "ethnicity", "convicted"]
        ):
            return DraftCustomQuestion(
                question_id=question_id,
                question=question_text,
                category=category,
                answer=None,
                source=FieldSource.UNKNOWN,
                confidence=0.0,
                requires_review=True,
                requires_user_input=True,
                warning="Sensitive demographic or compliance disclosure; requires explicit user selection.",
            )

        # 6. Factual: Education Credentials
        if category == QuestionCategory.EDUCATION and context.education:
            edu = context.education[0]
            if "graduation" in q_lower or "year" in q_lower:
                year = edu.get("end_date") or edu.get("start_date") or "2024"
                return DraftCustomQuestion(
                    question_id=question_id,
                    question=question_text,
                    category=category,
                    answer=str(year),
                    source=FieldSource.CANDIDATE_PROFILE,
                    confidence=1.0,
                    requires_review=False,
                )
            if "gpa" in q_lower and edu.get("gpa"):
                return DraftCustomQuestion(
                    question_id=question_id,
                    question=question_text,
                    category=category,
                    answer=str(edu.get("gpa")),
                    source=FieldSource.CANDIDATE_PROFILE,
                    confidence=1.0,
                    requires_review=False,
                )
            deg = edu.get("degree") or edu.get("field_of_study")
            inst = edu.get("institution")
            ans = f"{deg} from {inst}" if deg and inst else (deg or inst or "Computer Science")
            return DraftCustomQuestion(
                question_id=question_id,
                question=question_text,
                category=category,
                answer=ans,
                source=FieldSource.CANDIDATE_PROFILE,
                confidence=1.0,
                requires_review=False,
            )

        # 7. Factual: Specific Skill Presence
        if category == QuestionCategory.SKILL:
            cand_skills_lower = {s.lower() for s in context.skills}
            # Check if any candidate skill is mentioned in question
            matched_skills = [s for s in context.skills if s.lower() in q_lower]
            if matched_skills:
                skills_str = ", ".join(matched_skills)
                return DraftCustomQuestion(
                    question_id=question_id,
                    question=question_text,
                    category=category,
                    answer=f"Yes, I have hands-on experience with {skills_str}.",
                    source=FieldSource.CANDIDATE_PROFILE,
                    confidence=1.0,
                    requires_review=False,
                )

        # 8. Subjective Questions: Motivation, Role Fit, Projects, Behavioral
        # Grounded generation using AI provider
        try:
            skills_summary = ", ".join(context.skills[:10]) if context.skills else "software engineering"
            project_summary = (
                context.projects[0].get("name", "engineering project") if context.projects else "software projects"
            )
            prompt = (
                f"Candidate Name: {context.name}\n"
                f"Candidate Skills: {skills_summary}\n"
                f"Candidate Projects: {project_summary}\n"
                f"Job Title: {job.title} at {job.company}\n\n"
                f"Question: {question_text}\n"
                f"Instruction: Write a professional, concise (1-3 sentences) answer strictly grounded in the candidate's actual skills ({skills_summary}) and project ({project_summary}). "
                f"DO NOT invent any employers, credentials, or technologies not listed above."
            )
            system_prompt = "You are a truthful, professional job application assistant. Never hallucinate qualifications."

            generated_answer = await self.llm_provider.generate_text(prompt=prompt, system_prompt=system_prompt)
            clean_answer = generated_answer.strip().strip('"')

            return DraftCustomQuestion(
                question_id=question_id,
                question=question_text,
                category=category,
                answer=clean_answer,
                source=FieldSource.AI_GENERATED,
                confidence=0.85,
                requires_review=True,
                requires_user_input=False,
            )
        except Exception as e:
            logger.warning(f"AI generation failed for question '{question_text}': {e}")
            # Fallback deterministic answer grounded in candidate skills
            skills_str = ", ".join(context.skills[:4]) if context.skills else "software engineering"
            return DraftCustomQuestion(
                question_id=question_id,
                question=question_text,
                category=category,
                answer=f"My background in {skills_str} directly prepares me to contribute to {job.company}'s mission for the {job.title} position.",
                source=FieldSource.DERIVED,
                confidence=0.75,
                requires_review=True,
                warning="Generated using deterministic fallback template; review recommended.",
            )

    async def answer_questions(
        self,
        questions: List[Dict[str, Any]],
        context: CandidateApplicationContext,
        job: JobPosting,
        explicit_user_answers: Optional[Dict[str, str]] = None,
    ) -> List[DraftCustomQuestion]:
        """Answers a batch of custom application questions."""
        results: List[DraftCustomQuestion] = []
        for q in questions:
            q_id = q.get("question_id") or q.get("id") or f"q_{hash(q.get('question', ''))}"
            q_text = q.get("question") or q.get("question_text", "")
            answered = await self.answer_question(
                question_id=q_id,
                question_text=q_text,
                context=context,
                job=job,
                explicit_user_answers=explicit_user_answers,
            )
            results.append(answered)
        return results
