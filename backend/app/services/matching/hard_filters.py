import logging
import re
from typing import List, Set
from app.models.job import JobPosting
from app.schemas.resume import CandidateProfile
from app.services.matching.models import HardFilterEvaluation

logger = logging.getLogger(__name__)


class HardFilterEngine:
    """
    Evaluates candidate hard constraints against a job posting.
    Separates hard constraint satisfaction (PASS/FAIL) from soft score matching.
    """

    @classmethod
    def evaluate(cls, candidate: CandidateProfile, job: JobPosting) -> HardFilterEvaluation:
        prefs = candidate.preferences
        failed_constraints: List[str] = []
        unknown_constraints: List[str] = []
        details: dict = {}

        # 1. Excluded Companies Filter
        excluded_companies = [c.lower().strip() for c in prefs.get("excluded_companies", []) if c.strip()]
        job_company_clean = re.sub(r"\W+", "", job.company.lower())
        for excl in excluded_companies:
            excl_clean = re.sub(r"\W+", "", excl)
            if excl_clean and (excl_clean in job_company_clean or job_company_clean in excl_clean):
                failed_constraints.append("excluded_company")
                details["excluded_company"] = f"Company '{job.company}' matches excluded list."
                break

        # 2. Remote / Work Mode Filter
        pref_remote = prefs.get("remote_preference", "ANY")
        if hasattr(pref_remote, "value"):
            pref_remote = pref_remote.value
        pref_remote = str(pref_remote).upper()

        job_remote = str(job.remote_type).upper()

        if pref_remote == "REMOTE":
            if job_remote in ["ON_SITE", "HYBRID"]:
                failed_constraints.append("remote_work_policy")
                details["remote_work_policy"] = f"Candidate requires remote work, but job is '{job_remote}'."
        elif pref_remote == "ON_SITE":
            # If user wants strictly on-site, a purely remote role may fail if strict
            pass

        # 3. Location Filter
        pref_locations = [loc.lower().strip() for loc in prefs.get("preferred_locations", []) if loc.strip()]
        job_loc = (job.location or "").lower().strip()

        if pref_locations:
            if job_remote == "REMOTE" or "remote" in job_loc:
                # Remote satisfies location constraints
                pass
            elif not job_loc:
                unknown_constraints.append("location")
                details["location"] = "Job location is unspecified."
            else:
                # Check if job location matches any preferred location
                matched_loc = False
                for pref_l in pref_locations:
                    if pref_l in job_loc or job_loc in pref_l:
                        matched_loc = True
                        break
                if not matched_loc:
                    failed_constraints.append("location")
                    details["location"] = f"Job location '{job.location}' does not match preferred locations: {prefs.get('preferred_locations')}."

        # 4. Salary / Minimum Stipend Filter
        min_stipend = prefs.get("minimum_stipend")
        if min_stipend is not None and min_stipend > 0:
            if job.stipend_max is not None and job.stipend_max > 0:
                if job.stipend_max < min_stipend:
                    failed_constraints.append("minimum_stipend")
                    details["minimum_stipend"] = f"Job max salary ({job.stipend_max}) is below candidate minimum ({min_stipend})."
            elif job.stipend_min is not None and job.stipend_min > 0:
                if job.stipend_min < (min_stipend * 0.7):  # Allow reasonable range if min is lower
                    failed_constraints.append("minimum_stipend")
                    details["minimum_stipend"] = f"Job min salary ({job.stipend_min}) is substantially below candidate minimum ({min_stipend})."
            else:
                unknown_constraints.append("salary")
                details["salary"] = "Job does not specify salary or stipend."

        passed = len(failed_constraints) == 0

        return HardFilterEvaluation(
            passed=passed,
            failed_constraints=failed_constraints,
            unknown_constraints=unknown_constraints,
            details=details,
        )
