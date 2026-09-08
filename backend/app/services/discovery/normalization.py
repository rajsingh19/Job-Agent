import html
import re
from typing import List, Optional, Tuple
from app.models.enums import ExperienceLevel, RemoteType

CANONICAL_SKILL_MAP = {
    "python": "Python",
    "javascript": "JavaScript",
    "typescript": "TypeScript",
    "java": "Java",
    "c++": "C++",
    "c#": "C#",
    "go": "Go",
    "rust": "Rust",
    "scala": "Scala",
    "react": "React",
    "next.js": "Next.js",
    "vue": "Vue.js",
    "angular": "Angular",
    "node.js": "Node.js",
    "express": "Express",
    "fastapi": "FastAPI",
    "django": "Django",
    "flask": "Flask",
    "sql": "SQL",
    "postgresql": "PostgreSQL",
    "mysql": "MySQL",
    "mongodb": "MongoDB",
    "redis": "Redis",
    "elasticsearch": "Elasticsearch",
    "sqlite": "SQLite",
    "docker": "Docker",
    "kubernetes": "Kubernetes",
    "aws": "AWS",
    "gcp": "GCP",
    "azure": "Azure",
    "terraform": "Terraform",
    "ci/cd": "CI/CD",
    "linux": "Linux",
    "git": "Git",
    "playwright": "Playwright",
    "selenium": "Selenium",
    "machine learning": "Machine Learning",
    "pytorch": "PyTorch",
    "tensorflow": "TensorFlow",
    "llm": "LLM",
    "nlp": "NLP",
    "graphql": "GraphQL",
    "rest api": "REST API",
    "pandas": "Pandas",
    "numpy": "NumPy",
    "kafka": "Kafka",
    "spark": "Spark",
    "agile": "Agile",
}


class JobNormalizer:
    """
    Normalizes job titles, company names, locations, remote types, experience levels,
    descriptions, and extracted skill tags into consistent structures.
    """

    @staticmethod
    def normalize_company_name(raw_company: str) -> str:
        """Cleans and standardizes company names."""
        if not raw_company:
            return "Unknown Company"

        company = html.unescape(raw_company).strip()
        # Remove trailing legal suffixes for display/cleanliness
        company = re.sub(
            r",?\s*\b(Inc|LLC|Corp|Corporation|Ltd|Limited|GmbH|Pvt\s*Ltd)\b\.?",
            "",
            company,
            flags=re.IGNORECASE,
        ).strip()
        return company or raw_company.strip()

    @staticmethod
    def normalize_title(raw_title: str) -> str:
        """Normalizes job titles, expanding standard abbreviations and stripping redundant annotations."""
        if not raw_title:
            return "Untitled Position"

        title = html.unescape(raw_title).strip()

        # Remove location/remote tags in brackets e.g. "(Remote)", "[US Only]", "(Hybrid)"
        title = re.sub(r"\s*[\(\[\{]\s*(remote|hybrid|onsite|on-site|us|usa|emea|apac|india)[^\)\]\}]*[\)\]\}]", "", title, flags=re.IGNORECASE)

        # Standard abbreviation expansions
        replacements = [
            (r"\bSr\.?\b", "Senior"),
            (r"\bJr\.?\b", "Junior"),
            (r"\bSWE\b", "Software Engineer"),
            (r"\bSDE\b", "Software Development Engineer"),
            (r"\bDev\b", "Developer"),
            (r"\bEng\b", "Engineer"),
            (r"\bAI/ML\b", "AI / Machine Learning"),
            (r"\bML\b", "Machine Learning"),
        ]
        for pattern, repl in replacements:
            title = re.sub(pattern, repl, title, flags=re.IGNORECASE)

        # Remove emojis and unwanted trailing punctuation
        title = re.sub(r"[^\w\s\-\/\+\.\#]", " ", title)
        # Clean stray dots attached to words (like "Senior.")
        title = re.sub(r"(?<=\w)\.(?=\s|$)", "", title)

        # Clean multiple whitespaces
        title = re.sub(r"\s+", " ", title).strip()
        return title

    @staticmethod
    def normalize_location(raw_location: Optional[str]) -> Optional[str]:
        """Cleans and standardizes location strings."""
        if not raw_location or not raw_location.strip():
            return None

        loc = html.unescape(raw_location).strip()
        loc = re.sub(r"\s+", " ", loc)

        # Standardize common multi-location text
        if re.search(r"\b(remote|anywhere|virtual)\b", loc, re.IGNORECASE):
            return "Remote"

        return loc

    @staticmethod
    def detect_remote_type(title: str, location: Optional[str], description: str) -> RemoteType:
        """Determines remote policy based on title, location, and description keywords."""
        combined = f"{title} {location or ''} {description[:600]}".lower()

        if re.search(r"\b(fully remote|100% remote|remote\s*-\s*|work from anywhere|wfh)\b", combined):
            return RemoteType.REMOTE
        elif re.search(r"\b(hybrid|flexible remote|partially remote|hybrid remote)\b", combined):
            return RemoteType.HYBRID
        elif re.search(r"\b(on-site|onsite|in-office|office based|in office)\b", combined):
            return RemoteType.ON_SITE
        elif "remote" in combined or (location and "remote" in location.lower()):
            return RemoteType.REMOTE

        return RemoteType.ANY

    @staticmethod
    def detect_experience_level(title: str, description: str) -> Optional[ExperienceLevel]:
        """Infers experience level from title and description."""
        combined = f"{title} {description[:400]}".lower()

        if re.search(r"\b(intern|internship|co-op|coop|student trainee)\b", combined):
            return ExperienceLevel.INTERNSHIP
        elif re.search(r"\b(lead|principal|staff|director|head of|vp|architect)\b", combined):
            return ExperienceLevel.LEAD
        elif re.search(r"\b(senior|sr\b|lead)\b", combined):
            return ExperienceLevel.SENIOR_LEVEL
        elif re.search(r"\b(junior|jr\b|entry level|associate|graduate|entry-level)\b", combined):
            return ExperienceLevel.ENTRY_LEVEL
        elif re.search(r"\b(mid-level|mid level|intermediate)\b", combined):
            return ExperienceLevel.MID_LEVEL

        return None

    @staticmethod
    def clean_html_description(raw_description: str) -> str:
        """Strips HTML markup and converts into clean text."""
        if not raw_description:
            return ""

        # Unescape HTML entities first
        text = html.unescape(raw_description)

        # Convert block elements to newlines
        text = re.sub(r"<(?:p|div|li|br|h[1-6])[^>]*>", "\n", text, flags=re.IGNORECASE)
        text = re.sub(r"</(?:p|div|li|h[1-6])>", "\n", text, flags=re.IGNORECASE)

        # Strip remaining HTML tags
        text = re.sub(r"<[^>]+>", " ", text)

        # Consolidate whitespace and empty lines
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return "\n\n".join(lines).strip()

    @staticmethod
    def extract_skills(title: str, description: str, existing_skills: Optional[List[str]] = None) -> List[str]:
        """Extracts recognized skill tags from text and combines with existing skills using canonical casing."""
        combined = f"{title} {description}".lower()
        found_skills = set(s.strip() for s in (existing_skills or []) if s.strip())

        for skill_key, canonical_name in CANONICAL_SKILL_MAP.items():
            pattern = r"\b" + re.escape(skill_key) + r"\b"
            if re.search(pattern, combined):
                found_skills.add(canonical_name)

        return sorted(list(found_skills))
