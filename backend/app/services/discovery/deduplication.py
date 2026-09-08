import hashlib
import re
from typing import List, Set, Tuple
from app.schemas.job import JobPostingCreate


class JobDeduplicator:
    """
    Handles deterministic source hashing and fuzzy cross-source deduplication of job postings.
    """

    @staticmethod
    def generate_source_hash(
        source: str,
        external_id: str | None,
        company: str,
        title: str,
        location: str | None,
        apply_url: str,
    ) -> str:
        """
        Generates a deterministic 64-character SHA-256 hash representing the job posting.
        Prefers (source + external_id) if available; otherwise falls back to normalized job attributes.
        """
        if external_id and external_id.strip():
            identifier = f"{source.strip().lower()}:{external_id.strip()}"
        else:
            norm_comp = re.sub(r"\W+", "", company.lower())
            norm_title = re.sub(r"\W+", "", title.lower())
            norm_loc = re.sub(r"\W+", "", (location or "").lower())
            norm_url = apply_url.strip().lower().split("?")[0]  # Remove transient tracking params
            identifier = f"{norm_comp}:{norm_title}:{norm_loc}:{norm_url}"

        return hashlib.sha256(identifier.encode("utf-8")).hexdigest()

    @classmethod
    def are_fuzzy_duplicates(cls, job_a: JobPostingCreate, job_b: JobPostingCreate) -> bool:
        """
        Determines if two job postings from different sources/queries represent the same role.
        """
        # Exact source hash check
        if job_a.source_hash == job_b.source_hash:
            return True

        # Normalized company match
        comp_a = re.sub(r"\W+", "", job_a.company.lower())
        comp_b = re.sub(r"\W+", "", job_b.company.lower())
        if not comp_a or not comp_b or comp_a != comp_b:
            return False

        # Normalized title token overlap
        tokens_a = set(re.findall(r"\w+", job_a.title.lower()))
        tokens_b = set(re.findall(r"\w+", job_b.title.lower()))

        if not tokens_a or not tokens_b:
            return False

        intersection = tokens_a.intersection(tokens_b)
        union = tokens_a.union(tokens_b)
        similarity = len(intersection) / len(union)

        # Require high title similarity (> 0.75) for matching
        if similarity < 0.75:
            # Special check for exact same words disregarding order
            if tokens_a != tokens_b:
                return False

        # Location compatibility check (if both specify distinct physical locations)
        loc_a = (job_a.location or "").lower().strip()
        loc_b = (job_b.location or "").lower().strip()

        if loc_a and loc_b:
            if loc_a != "remote" and loc_b != "remote" and loc_a != loc_b:
                # Check if one contains the other (e.g. "San Francisco" in "San Francisco, CA")
                if loc_a not in loc_b and loc_b not in loc_a:
                    return False

        return True

    @classmethod
    def deduplicate_postings(cls, postings: List[JobPostingCreate]) -> Tuple[List[JobPostingCreate], int]:
        """
        Deduplicates a list of job postings, returning (unique_postings, duplicates_removed_count).
        """
        unique_postings: List[JobPostingCreate] = []
        seen_hashes: Set[str] = set()
        duplicates_count = 0

        for posting in postings:
            # 1. Exact hash check
            if posting.source_hash in seen_hashes:
                duplicates_count += 1
                continue

            # 2. Fuzzy match against already accepted postings
            is_dup = False
            for existing in unique_postings:
                if cls.are_fuzzy_duplicates(posting, existing):
                    is_dup = True
                    break

            if is_dup:
                duplicates_count += 1
                continue

            seen_hashes.add(posting.source_hash)
            unique_postings.append(posting)

        return unique_postings, duplicates_count
