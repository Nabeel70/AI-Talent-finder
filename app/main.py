import json
import os
import sys

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from data_sources import describe_sources, merge_sources_text, source_from_text, source_from_upload
from learning_resources import get_learning_resources
from opportunity_matching import compare_against_team, generate_cv_highlights, match_profile_to_job, parse_team_profiles
from skill_profiles import build_skill_profile, export_profile

load_dotenv()
st.set_page_config(page_title="SkillSense - Unlock Your Hidden Potential", page_icon=":compass:", layout="wide")

st.title("SkillSense - Unlock Your Hidden Potential")
st.caption("AI copilot for discovering hidden strengths, validating multi-source skills, and activating growth paths.")

st.write(
    "SkillSense aggregates evidence from CVs, public profiles, project logs, and private feedback to build a dynamic "
    "skill graph with confidence scores, evidence trails, and privacy controls."
)

if "skill_profile" not in st.session_state:
    st.session_state["skill_profile"] = None
if "last_source_count" not in st.session_state:
    st.session_state["last_source_count"] = 0

sources = []

st.header("1. Curate Your Data Footprint")
st.info(
    "Load multiple signals (resume, LinkedIn, GitHub, internal reviews) and decide which ones remain private. "
    "Everything is processed locally until you export the profile."
)

doc_col1, doc_col2 = st.columns(2, gap="large")
with doc_col1:
    st.subheader("Structured documents")
    resume_file = st.file_uploader("Primary CV / Resume", type=["pdf", "docx"], key="resume_file")
    share_resume = st.checkbox("Allow resume insights in shareable profile", value=True, key="share_resume")
    if resume_file:
        try:
            sources.append(
                source_from_upload(resume_file, "resume", "public" if share_resume else "private")
            )
            st.success(f"Ingested {resume_file.name}")
        except Exception as exc:
            st.error(f"Resume ingestion failed: {exc}")

with doc_col2:
    st.subheader("Supporting uploads")
    supporting_files = st.file_uploader(
        "Portfolio, certifications, publications, reviews (PDF/DOCX/TXT/MD)",
        type=["pdf", "docx", "txt", "md"],
        accept_multiple_files=True,
        key="supporting_files",
    )
    share_support = st.checkbox("Allow supporting docs in shareable profile", value=False, key="share_support")
    if supporting_files:
        for upload in supporting_files:
            try:
                sources.append(
                    source_from_upload(upload, "supporting", "public" if share_support else "private")
                )
            except Exception as exc:
                st.warning(f"{upload.name}: {exc}")

profile_col1, profile_col2 = st.columns(2, gap="large")
with profile_col1:
    st.subheader("Public narratives")
    linkedin_text = st.text_area(
        "LinkedIn / portfolio / personal bio (paste any relevant summary)",
        height=170,
        key="linkedin_text",
    )
    share_linkedin = st.checkbox("Share LinkedIn / portfolio insights", value=True, key="share_linkedin")
    linkedin_source = source_from_text(
        "LinkedIn Narrative",
        linkedin_text,
        "linkedin",
        "public" if share_linkedin else "private",
    )
    if linkedin_source:
        sources.append(linkedin_source)

with profile_col2:
    st.subheader("Project & GitHub signals")
    github_text = st.text_area(
        "Paste README snippets, project highlights, or blog posts describing your builds",
        height=170,
        key="github_text",
    )
    share_github = st.checkbox("Share GitHub / project insights", value=True, key="share_github")
    github_source = source_from_text(
        "Projects & GitHub",
        github_text,
        "github",
        "public" if share_github else "private",
    )
    if github_source:
        sources.append(github_source)

st.subheader("Internal evidence (kept private by default)")
internal_text = st.text_area(
    "Goals, performance reviews, mentorship feedback, OKRs, internal references",
    height=170,
    key="internal_text",
)
share_internal = st.checkbox("Share internal insights (careful!)", value=False, key="share_internal")
internal_source = source_from_text(
    "Internal Evidence",
    internal_text,
    "internal",
    "public" if share_internal else "private",
)
if internal_source:
    sources.append(internal_source)

if sources:
    stats = describe_sources(sources)
    metrics_col1, metrics_col2, metrics_col3 = st.columns(3)
    metrics_col1.metric("Sources loaded", stats["count"])
    metrics_col2.metric("Avg words per source", stats["avg_words"])
    visibility_str = ", ".join(f"{k}: {v}" for k, v in stats["visibility"].items())
    metrics_col3.metric("Visibility split", visibility_str if visibility_str else "n/a")

    with st.expander("Preview aggregated corpus (public sources only)", expanded=False):
        preview = merge_sources_text(sources, visibility="public")[:1200]
        if preview:
            st.code(preview, language="markdown")
        else:
            st.write("No public content loaded yet.")
else:
    st.warning("Add at least one source to continue.")

st.header("2. Generate and Explore Your Skill Profile")
run_analysis = st.button("Run SkillSense analysis", type="primary", disabled=not sources)

if run_analysis and sources:
    with st.spinner("Discovering explicit and implicit skills..."):
        st.session_state["skill_profile"] = build_skill_profile(sources)
        st.session_state["last_source_count"] = len(sources)

skill_profile = st.session_state.get("skill_profile")
source_mismatch = bool(skill_profile) and st.session_state.get("last_source_count") != len(sources)
if source_mismatch:
    st.warning("Sources changed after the last analysis. Re-run SkillSense to refresh insights.")

profile_tab, opportunity_tab, org_tab = st.tabs(
    ["Skill profile", "Opportunities & gaps", "Org / team view"]
)

with profile_tab:
    if not skill_profile:
        st.info("Load sources and run the analysis to unlock your profile.")
    else:
        st.success(skill_profile["summary"])
        stats = skill_profile["stats"]
        metric_cols = st.columns(4)
        metric_cols[0].metric("Explicit skills", stats["explicit_count"])
        metric_cols[1].metric("Implicit skills", stats["implicit_count"])
        metric_cols[2].metric("Avg confidence", stats["avg_confidence"])
        metric_cols[3].metric(
            "Public sources",
            stats["sources_visibility"].get("public", 0),
            help="Shareable sources that can appear in exported profiles.",
        )

        if stats["category_distribution"]:
            cat_df = pd.DataFrame(
                {
                    "Category": list(stats["category_distribution"].keys()),
                    "Count": list(stats["category_distribution"].values()),
                }
            ).set_index("Category")
            st.bar_chart(cat_df)

        signal_rows = [
            {
                "Skill": signal.name.title(),
                "Type": signal.signal_type,
                "Category": signal.category,
                "Confidence": signal.confidence,
                "Sources": ", ".join(signal.sources),
            }
            for signal in skill_profile["signals"]
        ]
        st.markdown("### Structured skill profile")
        st.dataframe(pd.DataFrame(signal_rows), use_container_width=True, hide_index=True)

        st.markdown("### Evidence trails (top signals)")
        for signal in skill_profile["signals"][:5]:
            label = f"{signal.name.title()} - {signal.signal_type} - confidence {signal.confidence}"
            with st.expander(label):
                if not signal.evidence:
                    st.write("No direct snippet captured.")
                for evidence in signal.evidence:
                    st.write(f"**{evidence.source}:** {evidence.snippet}")

        st.markdown("### Framework alignment (sample)")
        alignment_rows = []
        for category, payload in stats["framework_alignment"].items():
            alignment_rows.append(
                {
                    "Category": category,
                    "Coverage": f"{int(payload['coverage'] * 100)}%",
                    "Skills covered": ", ".join(skill.title() for skill in payload["covered"]) or "--",
                    "Target count": payload["target_total"],
                }
            )
        st.dataframe(pd.DataFrame(alignment_rows), hide_index=True, use_container_width=True)

        st.markdown("### CV-ready highlights")
        highlights = generate_cv_highlights(skill_profile)
        for highlight in highlights:
            st.write(f"- {highlight}")

        development_targets = [
            signal.name for signal in sorted(skill_profile["signals"], key=lambda s: s.confidence) if signal.confidence < 0.65
        ][:5]
        if development_targets:
            st.markdown("### Learning paths to boost lower-confidence skills")
            resources = get_learning_resources(development_targets)
            for skill, url in resources.items():
                st.markdown(f"- **{skill.title()}** -> {url}")

        export_payload = export_profile(skill_profile["signals"])
        st.download_button(
            "Download skill profile (JSON)",
            data=json.dumps(export_payload, indent=2),
            file_name="skillsense_profile.json",
            mime="application/json",
        )

with opportunity_tab:
    if not skill_profile:
        st.info("Generate a skill profile first.")
    else:
        st.markdown("#### Match against opportunities")
        job_file = st.file_uploader(
            "Upload a job description or team brief", type=["pdf", "docx", "txt", "md"], key="job_file"
        )
        job_text_input = st.text_area("Or paste the opportunity text", height=220, key="job_text")
        job_text = job_text_input.strip()

        if job_file:
            try:
                job_source = source_from_upload(job_file, "job", "public")
                job_text = job_source.text
                st.caption(f"Loaded {len(job_text.split())} words from {job_file.name}")
            except Exception as exc:
                st.error(f"Job description parsing failed: {exc}")

        analyze_job = st.button("Analyze opportunity", key="analyze_job", disabled=not job_text)
        if analyze_job and job_text:
            result = match_profile_to_job(skill_profile, job_text)
            if result:
                st.metric("Skill coverage", f"{int(result.coverage * 100)}%")
                st.progress(result.coverage)
                match_col, gap_col = st.columns(2)
                with match_col:
                    st.markdown("**Matched skills**")
                    st.write(", ".join(result.matched) or "None yet.")
                with gap_col:
                    st.markdown("**Gap skills**")
                    st.write(", ".join(result.gaps) or "No gaps detected.")

                if result.recommendations:
                    st.markdown("### Targeted learning to close gaps")
                    for skill, url in result.recommendations.items():
                        st.markdown(f"- **{skill.title()}** -> {url}")
                else:
                    st.info("No learning resources required for this posting.")

with org_tab:
    if not skill_profile:
        st.info("Generate a skill profile first.")
    else:
        st.markdown("#### Compare with team / org skill map")
        st.caption("Format each line as `Name: skill1, skill2`. Example: `Asha: cloud, security`")
        team_blob = st.text_area("Team skill inventory", height=160, key="team_blob")
        compare_team = st.button("Compare against team", key="compare_team", disabled=not team_blob.strip())
        if compare_team and team_blob.strip():
            team_profiles = parse_team_profiles(team_blob)
            if not team_profiles:
                st.warning("No valid team entries detected.")
            else:
                report = compare_against_team(skill_profile, team_profiles)
                org_cols = st.columns(2)
                org_cols[0].metric("Team size", report["team_size"])
                org_cols[1].metric("Unique team skills", report["team_skill_coverage"])

                st.markdown("**Your standout strengths vs. the team**")
                st.write(", ".join(report["unique_strengths"]) or "Add more evidence to highlight unique strengths.")

                st.markdown("**Team gaps you can bridge**")
                st.write(", ".join(report["team_gaps"]) or "Team already covers the skills you surfaced.")
