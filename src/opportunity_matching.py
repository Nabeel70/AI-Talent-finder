from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from data_sources import SourceDocument
from learning_resources import get_learning_resources
from skill_profiles import as_skill_set, build_skill_profile
from skills import normalize_skill


@dataclass
class JobMatchResult:
    coverage: float
    matched: List[str]
    gaps: List[str]
    recommendations: Dict[str, str]
    raw_job_profile: dict


def match_profile_to_job(skill_profile: dict, job_text: str) -> Optional[JobMatchResult]:
    if not job_text or not job_text.strip():
        return None

    job_source = SourceDocument(
        name="Job Posting",
        kind="job",
        text=job_text.strip(),
        visibility="public",
        origin="manual",
    )
    job_profile = build_skill_profile([job_source])
    candidate_skillset = as_skill_set(skill_profile.get("signals", []))
    job_skillset = as_skill_set(job_profile.get("signals", []))

    if not job_skillset:
        return JobMatchResult(
            coverage=0.0,
            matched=[],
            gaps=[],
            recommendations={},
            raw_job_profile=job_profile,
        )

    matched = [
        job_skillset[key].name
        for key in job_skillset.keys()
        if key in candidate_skillset
    ]
    gaps = [
        job_skillset[key].name
        for key in job_skillset.keys()
        if key not in candidate_skillset
    ]
    coverage = len(matched) / len(job_skillset) if job_skillset else 0
    learning = get_learning_resources(gaps)

    return JobMatchResult(
        coverage=round(coverage, 2),
        matched=sorted(set(matched)),
        gaps=sorted(set(gaps)),
        recommendations=learning,
        raw_job_profile=job_profile,
    )


def parse_team_profiles(raw_text: str) -> List[dict]:
    """
    Parse a lightweight team profile format:
    Each line should look like `Name: skill1, skill2, skill3`.
    """
    profiles: List[dict] = []
    if not raw_text:
        return profiles
    for line in raw_text.splitlines():
        if ":" not in line:
            continue
        name, skills_blob = line.split(":", 1)
        skills = [skill.strip() for skill in skills_blob.split(",") if skill.strip()]
        if not skills:
            continue
        profiles.append({"name": name.strip(), "skills": skills})
    return profiles


def compare_against_team(skill_profile: dict, team_profiles: List[dict]) -> dict:
    candidate_skillset = as_skill_set(skill_profile.get("signals", []))
    candidate_keys = set(candidate_skillset.keys())
    team_skillset = set()
    for member in team_profiles:
        for skill in member.get("skills", []):
            team_skillset.add(normalize_skill(skill))

    unique_strengths = [candidate_skillset[key].name for key in candidate_keys - team_skillset]
    missing_in_team = [skill for skill in team_skillset - candidate_keys]

    return {
        "team_size": len(team_profiles),
        "team_skill_coverage": len(team_skillset),
        "unique_strengths": sorted(unique_strengths),
        "team_gaps": sorted(missing_in_team),
    }


def generate_cv_highlights(skill_profile: dict, limit: int = 4) -> List[str]:
    signals = skill_profile.get("signals", [])
    highlights = []
    for signal in signals[:limit]:
        snippet = signal.evidence[0].snippet if signal.evidence else ""
        bullet = f"{signal.name.title()} ({signal.category}) - confidence {signal.confidence}"
        if snippet:
            bullet += f"; evidence: {snippet[:120]}..."
        highlights.append(bullet)
    return highlights
