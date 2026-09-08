import re
from typing import List, Set
from app.models.job import JobPosting
from app.schemas.resume import CandidateProfile
from app.services.matching.models import RoleMatchEvaluation

# Canonical role clusters for semantic role comparison
ROLE_CLUSTERS = [
    {"software engineer", "software developer", "swe", "sde", "full stack engineer", "full stack developer", "backend engineer", "backend developer", "frontend engineer", "frontend developer", "web developer"},
    {"machine learning engineer", "ai engineer", "ai/ml engineer", "data scientist", "research scientist", "mlops engineer", "deep learning engineer"},
    {"devops engineer", "site reliability engineer", "sre", "cloud engineer", "infrastructure engineer", "platform engineer"},
    {"data engineer", "data warehouse engineer", "bi developer", "analytics engineer"},
    {"product manager", "technical product manager", "associate product manager", "product owner"},
    {"qa engineer", "software development engineer in test", "sdet", "test engineer", "automation engineer"},
]


class RoleMatcher:
    """
    Evaluates role and title similarity between candidate target roles and job title.
    """

    @classmethod
    def _clean_role(cls, text: str) -> str:
        t = re.sub(r"\W+", " ", text.lower()).strip()
        # Remove seniority words for base role matching
        t = re.sub(r"\b(senior|junior|lead|principal|staff|intern|associate|entry level)\b", "", t).strip()
        t = re.sub(r"\s+", " ", t)
        return t

    @classmethod
    def evaluate(cls, candidate: CandidateProfile, job: JobPosting) -> RoleMatchEvaluation:
        target_roles = [r.strip() for r in candidate.preferences.get("target_roles", []) if r.strip()]

        if not target_roles:
            # Fall back to past roles in resume experience
            for exp in candidate.resume_profile.experience:
                if exp.role and exp.role.strip():
                    target_roles.append(exp.role.strip())

        if not target_roles:
            # Default generic match
            target_roles = ["Software Engineer"]

        job_title_clean = cls._clean_role(job.title)
        best_score = 0.0
        best_match_role = None
        best_reason = ""

        for target in target_roles:
            target_clean = cls._clean_role(target)

            # 1. Exact match
            if target_clean == job_title_clean:
                score = 100.0
                reason = f"Exact role match with target '{target}'."
            # 2. Substring match
            elif target_clean in job_title_clean or job_title_clean in target_clean:
                score = 90.0
                reason = f"Strong title overlap with target '{target}'."
            else:
                # 3. Cluster / Domain match
                in_same_cluster = False
                for cluster in ROLE_CLUSTERS:
                    if any(target_clean in c for c in cluster) and any(job_title_clean in c for c in cluster):
                        in_same_cluster = True
                        break

                if in_same_cluster:
                    score = 80.0
                    reason = f"Role '{job.title}' is in the same domain cluster as '{target}'."
                else:
                    # Token overlap Jaccard
                    tokens_t = set(target_clean.split())
                    tokens_j = set(job_title_clean.split())
                    if tokens_t and tokens_j:
                        overlap = len(tokens_t.intersection(tokens_j)) / len(tokens_t.union(tokens_j))
                        score = round(overlap * 70.0, 1)
                        reason = f"Partial keyword title overlap ({round(overlap*100)}%) with '{target}'."
                    else:
                        score = 20.0
                        reason = f"Low role similarity between '{job.title}' and '{target}'."

            if score > best_score:
                best_score = score
                best_match_role = target
                best_reason = reason

        return RoleMatchEvaluation(
            score=max(0.0, min(100.0, best_score)),
            matched_role=best_match_role,
            similarity_reason=best_reason,
        )
