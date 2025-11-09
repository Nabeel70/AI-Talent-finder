# SkillSense - Unlock Your Hidden Potential

SkillSense is an AI copilot for the SAP Corporate Track challenge that discovers explicit and implicit skills hidden across resumes, public profiles, GitHub logs, and internal feedback. The app builds dynamic skill profiles with confidence scores, evidence trails, privacy controls, and downstream use cases such as opportunity matching, learning recommendations, CV-ready highlights, and team gap analysis.

## Why SkillSense

- **Multi-source ingestion** - combine CVs, LinkedIn summaries, GitHub READMEs, blogs, and internal performance notes in one click.
- **Explicit + implicit intelligence** - dictionary and pattern-based NLP surfaces tool skills while semantic cues reveal leadership, stakeholder management, innovation, and more.
- **Formal framework alignment** - every detected skill is mapped to a lightweight skill framework (Technical Foundation, Data & AI, Product & Delivery, Leadership & Impact) for consistent scoring.
- **Evidence-first summaries** - every claim is backed by snippets, source tracking, and confidence scores so hallucinations are filtered out.
- **Actionable follow-ups** - gap analysis, targeted learning resources, CV highlights, and team comparisons keep the profile actionable for individuals and organizations.
- **Privacy aware** - toggle per-source visibility; internal data can stay private while public data flows into exportable profiles.

## Architecture

| Layer | Description |
|-------|-------------|
| `app/main.py` | Streamlit experience with SkillSense branding, multi-source onboarding, privacy toggles, profile explorer, opportunity matching, and org/team comparison. |
| `src/data_sources.py` | Normalizes uploads/text inputs into typed `SourceDocument` objects, tracks visibility, and summarizes corpus statistics. |
| `src/skill_profiles.py` | Core intelligence engine: detects explicit skills from curated vocabularies, implicit skills via regex cues, computes confidence, maps to the formal framework, and exports JSON-safe payloads. |
| `src/opportunity_matching.py` | Matches skill profiles against job postings, builds learning plans, generates CV-ready highlights, and compares individuals with simple team inventories. |
| Legacy helpers | `skills.py`, `learning_resources.py`, etc., provide shared vocabularies and curated resource links. Optional LLM utilities are still present but excluded from the MVP flow for offline readiness. |

## Getting Started

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
2. **Launch SkillSense**
   ```bash
   streamlit run app/main.py
   ```
3. (Optional) Create a `.env` with extra environment variables if you later re-enable the legacy OpenAI-powered helpers.

The current MVP runs fully offline - no API keys or outbound requests are required.

## Using SkillSense

1. **Curate your data footprint**
   - Upload CVs or supporting documents (PDF/DOCX/TXT/MD).
   - Paste LinkedIn, portfolio, and GitHub/project narratives.
   - Paste internal artifacts (goals, reviews, peer feedback). Leave them private by default.
   - Use the per-source toggles to decide what can appear in exported skill profiles.

2. **Generate the profile**
   - Click **Run SkillSense analysis** to aggregate sources, detect skills, and calculate confidence.
   - Review explicit vs. implicit skill counts, category coverage, and alignment with the formal framework.
   - Explore evidence trails with per-skill snippets, average confidences, and the shareable JSON export.
   - Capture CV-ready highlights auto-derived from the strongest signals.

3. **Activate outcomes**
   - **Opportunities & gaps** - upload/paste job descriptions, quantify skill coverage, surface gaps, and view curated learning resources to close them.
   - **Learning paths** - the platform automatically suggests Coursera/edX/etc. links for low-confidence or missing skills.
   - **Org/team view** - paste lightweight team inventories (`Name: skill1, skill2`) to identify unique strengths and coverage gaps across a group.

## Privacy & Data Handling

- All processing happens inside Streamlit sessions - no data is uploaded elsewhere unless you export the JSON profile.
- Visibility flags (`public` vs. `private`) travel with every source and determine whether a snippet appears in downloads or previews.
- Internal evidence can be analyzed locally to influence confidence scores without ever being included in shareable exports.

## Extending the MVP

- Plug in additional data sources (e.g., HRIS exports, LMS logs) by creating new `SourceDocument` factories.
- Swap the lightweight framework for SFIA, ESCO, or company-specific taxonomies by editing `FORMAL_SKILL_FRAMEWORK` in `src/skill_profiles.py`.
- Re-enable the legacy LangChain/OpenAI utilities for generative enhancements if API access is available.
- Deploy on Streamlit Community Cloud or any container platform; no special infrastructure is required.

SkillSense reframes the resume - from a static PDF into a living, evidence-backed skill graph that fuels opportunity matching, learning journeys, and organizational insight.
