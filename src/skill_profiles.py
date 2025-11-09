from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Tuple

from data_sources import SourceDocument
from skills import COMMON_SKILLS, normalize_skill


@dataclass
class SkillEvidence:
    source: str
    snippet: str


@dataclass
class SkillSignal:
    name: str
    category: str
    signal_type: str  # explicit | implicit
    confidence: float
    sources: List[str] = field(default_factory=list)
    evidence: List[SkillEvidence] = field(default_factory=list)


FORMAL_SKILL_FRAMEWORK = {
    "Technical Foundation": [
        "python",
        "java",
        "javascript",
        "typescript",
        "c++",
        "c#",
        "sql",
        "cloud",
        "aws",
        "azure",
        "gcp",
        "docker",
        "kubernetes",
        "ci/cd",
        "git",
    ],
    "Data & AI": [
        "data analysis",
        "data science",
        "machine learning",
        "deep learning",
        "computer vision",
        "nlp",
        "mlops",
        "pandas",
        "numpy",
        "tensorflow",
        "pytorch",
        "xgboost",
    ],
    "Product & Delivery": [
        "project management",
        "agile",
        "scrum",
        "kanban",
        "product management",
        "stakeholder management",
        "roadmapping",
        "testing",
        "qa",
        "devops",
    ],
    "Leadership & Impact": [
        "leadership",
        "mentorship",
        "communication",
        "strategic planning",
        "problem solving",
        "innovation",
        "change management",
    ],
}

FRAMEWORK_LOOKUP = {
    normalize_skill(skill): category
    for category, skills in FORMAL_SKILL_FRAMEWORK.items()
    for skill in skills
}

IMPLICIT_PATTERNS: Dict[str, List[str]] = {
    "leadership": [r"\bled\b", r"\bmanaged\b", r"\bhead(ed)?\b", r"\bdirected\b"],
    "mentorship": [r"\bmentored\b", r"\bcoached\b", r"\btrained\b"],
    "stakeholder management": [r"\bstakeholder(s)?\b", r"\baligned\b.*\bteam\b"],
    "communication": [r"\bpresented\b", r"\bfacilitated\b", r"\bworkshop\b"],
    "strategic planning": [r"\broadmap\b", r"\bstrategy\b", r"\bvision\b"],
    "problem solving": [r"\broot cause\b", r"\btroubleshoot(ed)?\b", r"\bdebugged\b"],
    "continuous improvement": [r"\bretrospective\b", r"\bcontinuous improvement\b", r"\bkaizen\b"],
    "governance": [r"\baudit(ed)?\b", r"\bcompliance\b", r"\brisk\b"],
    "innovation": [r"\bprototype(d)?\b", r"\bexperiments?\b", r"\bhackathon\b"],
}

IMPLICIT_CATEGORY = {
    "leadership": "Leadership & Impact",
    "mentorship": "Leadership & Impact",
    "stakeholder management": "Product & Delivery",
    "communication": "Leadership & Impact",
    "strategic planning": "Leadership & Impact",
    "problem solving": "Technical Foundation",
    "continuous improvement": "Product & Delivery",
    "governance": "Product & Delivery",
    "innovation": "Leadership & Impact",
}


def _snippet(text: str, start: int, end: int, window: int = 90) -> str:
    left = max(0, start - window)
    right = min(len(text), end + window)
    snippet = text[left:right].replace("\n", " ").strip()
    return snippet


def _register_signal(
    registry: Dict[str, dict],
    name: str,
    category: str,
    signal_type: str,
    source: SourceDocument,
    snippet: Optional[str],
) -> None:
    key = normalize_skill(name)
    entry = registry.setdefault(
        key,
        {
            "name": name,
            "category": category or "Uncategorized",
            "type": signal_type,
            "sources": set(),
            "snippets": [],
            "mentions": 0,
        },
    )
    entry["mentions"] += 1
    entry["sources"].add(source.name)
    if snippet:
        entry["snippets"].append(SkillEvidence(source=source.name, snippet=snippet))


def _finalize_registry(registry: Dict[str, dict]) -> List[SkillSignal]:
    signals: List[SkillSignal] = []
    for entry in registry.values():
        mention_bonus = min(0.35, 0.12 * math.log1p(entry["mentions"]))
        source_bonus = min(0.2, 0.08 * max(0, len(entry["sources"]) - 1))
        base = 0.55 if entry["type"] == "explicit" else 0.45
        confidence = round(min(0.98, base + mention_bonus + source_bonus), 2)
        signals.append(
            SkillSignal(
                name=entry["name"],
                category=entry["category"],
                signal_type=entry["type"],
                confidence=confidence,
                sources=sorted(entry["sources"]),
                evidence=entry["snippets"][:3],
            )
        )
    return sorted(signals, key=lambda s: (s.confidence, s.name), reverse=True)


def _match_skill_occurrences(text: str, skill: str) -> Iterable[Tuple[int, int]]:
    pattern = re.compile(rf"\b{re.escape(skill)}\b", flags=re.IGNORECASE)
    for match in pattern.finditer(text):
        yield match.start(), match.end()


def build_skill_profile(sources: Iterable[SourceDocument]) -> dict:
    sources = [src for src in sources if src and src.text.strip()]
    registry: Dict[str, dict] = {}

    for source in sources:
        text = source.text
        for skill in COMMON_SKILLS:
            for start, end in _match_skill_occurrences(text, skill):
                snippet = _snippet(text, start, end)
                category = FRAMEWORK_LOOKUP.get(normalize_skill(skill), "Technical Foundation")
                _register_signal(registry, skill, category, "explicit", source, snippet)

        lowered = text.lower()
        for implicit_skill, patterns in IMPLICIT_PATTERNS.items():
            for pattern in patterns:
                for match in re.finditer(pattern, lowered, flags=re.IGNORECASE):
                    snippet = _snippet(text, match.start(), match.end())
                    category = IMPLICIT_CATEGORY.get(implicit_skill, "Leadership & Impact")
                    _register_signal(
                        registry,
                        implicit_skill,
                        category,
                        "implicit",
                        source,
                        snippet,
                    )

    signals = _finalize_registry(registry)
    stats = _profile_stats(signals, sources)
    summary = summarize_profile(signals, stats)
    return {"signals": signals, "stats": stats, "summary": summary}


def _profile_stats(signals: List[SkillSignal], sources: List[SourceDocument]) -> dict:
    explicit = sum(1 for s in signals if s.signal_type == "explicit")
    implicit = sum(1 for s in signals if s.signal_type == "implicit")
    by_category = Counter(s.category for s in signals)
    framework_alignment = {}
    for category, skills in FORMAL_SKILL_FRAMEWORK.items():
        normalized_targets = {normalize_skill(skill) for skill in skills}
        covered = {normalize_skill(s.name) for s in signals if s.category == category}
        coverage = len(covered & normalized_targets) / len(normalized_targets) if normalized_targets else 0
        framework_alignment[category] = {
            "covered": sorted({s for s in covered if s in normalized_targets}),
            "coverage": round(coverage, 2),
            "target_total": len(normalized_targets),
        }

    avg_conf = round(sum(s.confidence for s in signals) / len(signals), 2) if signals else 0

    return {
        "source_count": len(sources),
        "explicit_count": explicit,
        "implicit_count": implicit,
        "category_distribution": dict(by_category),
        "framework_alignment": framework_alignment,
        "avg_confidence": avg_conf,
        "sources_visibility": Counter(src.visibility for src in sources),
        "top_sources": [src.name for src in sources[:3]],
    }


def summarize_profile(signals: List[SkillSignal], stats: dict) -> str:
    if not signals:
        return "No skills detected yet. Add more sources to unlock hidden strengths."
    top = ", ".join(signal.name.title() for signal in signals[:5])
    categories = ", ".join(
        f"{cat} ({count})" for cat, count in stats["category_distribution"].items()
    )
    return (
        f"Identified {stats['explicit_count']} explicit and {stats['implicit_count']} implicit skills "
        f"across {stats['source_count']} sources. Top strengths: {top}. "
        f"Coverage spans {categories} with an average confidence of {stats['avg_confidence']}."
    )


def export_profile(signals: List[SkillSignal]) -> List[dict]:
    """Return a JSON-serializable version of the skill profile."""
    payload = []
    for signal in signals:
        payload.append(
            {
                "name": signal.name,
                "category": signal.category,
                "type": signal.signal_type,
                "confidence": signal.confidence,
                "sources": signal.sources,
                "evidence": [{"source": e.source, "snippet": e.snippet} for e in signal.evidence],
            }
        )
    return payload


def as_skill_set(signals: List[SkillSignal]) -> Dict[str, SkillSignal]:
    """Return a mapping useful for comparisons."""
    return {normalize_skill(signal.name): signal for signal in signals}
