import re
from typing import List, Tuple
from app.schemas.application_draft import QuestionCategory


class QuestionClassifier:
    """
    Deterministic rule-based custom question classifier for application forms.
    Accurately tags sensitive categories (work authorization, salary, availability)
    to protect candidate compliance and prevent hallucinations.
    """

    CLASSIFICATION_RULES: List[Tuple[str, QuestionCategory]] = [
        # Work authorization & visa sponsorship (High risk / sensitive)
        (
            r"(?:authorized\s+to\s+work|work\s+authorization|visa\s+status|require\s+sponsorship|require\s+visa|sponsorship\s+now\s+or\s+in\s+the\s+future|legal\s+right\s+to\s+work|eligible\s+to\s+work|h1-?b|opt|cpt|stem)",
            QuestionCategory.WORK_AUTHORIZATION,
        ),
        # Salary & compensation expectations
        (
            r"(?:salary|compensation|stipend|desired\s+pay|expected\s+salary|hourly\s+rate|remuneration|wage)",
            QuestionCategory.SALARY,
        ),
        # Availability & start dates
        (
            r"(?:start\s+date|when\s+can\s+you\s+start|earliest\s+start|available\s+to\s+start|availability|notice\s+period|available\s+full\s*-?\s*time|available\s+part\s*-?\s*time)",
            QuestionCategory.AVAILABILITY,
        ),
        # Motivation & company interest
        (
            r"(?:why\s+(?:are\s+you\s+interested|do\s+you\s+want|join|work\s+(?:for|at))|what\s+interests\s+you\s+about|motivation)",
            QuestionCategory.MOTIVATION,
        ),
        # Role fit & why hire
        (
            r"(?:why\s+should\s+we\s+hire\s+you|why\s+are\s+you\s+(?:a\s+good|the\s+best)\s+fit|how\s+does\s+your\s+background\s+fit|what\s+makes\s+you\s+qualified)",
            QuestionCategory.ROLE_FIT,
        ),
        # Project & technical challenges
        (
            r"(?:describe\s+.*?\bproject\b|\bproject\b|technical\s+challenge|favorite\s+project|portfolio\s+project|github\s+repository)",
            QuestionCategory.PROJECT,
        ),
        # Behavioral & soft skills
        (
            r"(?:tell\s+me\s+about\s+a\s+time|describe\s+a\s+situation|handled\s+conflict|worked\s+in\s+a\s+team|greatest\s+strength|weakness|leadership)",
            QuestionCategory.BEHAVIORAL,
        ),
        # Specific skills & proficiency
        (
            r"(?:proficiency\s+in|years\s+of\s+experience\s+with|experience\s+using|do\s+you\s+have\s+experience\s+(?:in|with)|familiarity\s+with|tech\s+stack)",
            QuestionCategory.SKILL,
        ),
        # Education & academic credentials
        (
            r"(?:graduation\s+(?:year|date)|degree|major|field\s+of\s+study|university|college|gpa|highest\s+level\s+of\s+education|academic)",
            QuestionCategory.EDUCATION,
        ),
        # Experience & past employers
        (
            r"(?:years\s+of\s+.*?\bexperience\b|current\s+employer|previous\s+company|employment\s+history|job\s+title|\bwork\s+history\b)",
            QuestionCategory.EXPERIENCE,
        ),
        # Personal facts & contact
        (
            r"(?:gender|pronouns|ethnicity|race|veteran|disability|city|postal\s+code|zip\s+code|relocate|willing\s+to\s+relocate)",
            QuestionCategory.PERSONAL_FACT,
        ),
    ]

    @classmethod
    def classify(cls, question_text: str) -> QuestionCategory:
        """Classifies question text into a canonical QuestionCategory."""
        if not question_text or not question_text.strip():
            return QuestionCategory.OTHER

        text_lower = question_text.lower().strip()
        for pattern, category in cls.CLASSIFICATION_RULES:
            if re.search(pattern, text_lower):
                return category

        return QuestionCategory.OTHER
