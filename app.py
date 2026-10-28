import streamlit as st
import pandas as pd
from pypdf import PdfReader
from io import BytesIO
from dotenv import load_dotenv
from job_sources import search_jobs
from matcher import score_jobs
from database import init_db, save_job, get_saved_jobs, update_status, delete_saved_job

load_dotenv()
st.set_page_config(page_title="JobPilot AI", page_icon="🌍", layout="wide", initial_sidebar_state="expanded")
init_db()

st.markdown("""
<style>
.block-container {padding-top: 1.5rem; padding-bottom: 2rem; max-width: 1250px;}
.hero {padding: 1.35rem 1.5rem; border-radius: 18px; background: linear-gradient(115deg, rgba(44,91,180,.18), rgba(40,170,150,.12)); border: 1px solid rgba(120,140,170,.25); margin-bottom: 1rem;}
.small-muted {color: var(--text-color); opacity: .72; font-size: .88rem;}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="hero"><h1>🌍 JobPilot AI</h1><p>One CV. Your ideal role. Jobs from multiple countries and remote sources.</p><p class="small-muted">Discover opportunities, understand your match, and keep your applications organized.</p></div>', unsafe_allow_html=True)

country_options = {
    "United States": "us", "United Kingdom": "gb", "Canada": "ca", "Australia": "au",
    "India": "in", "United Arab Emirates": "ae", "Germany": "de", "France": "fr",
    "Netherlands": "nl", "Ireland": "ie", "Singapore": "sg", "New Zealand": "nz",
    "South Africa": "za", "Spain": "es", "Italy": "it", "Poland": "pl",
    "Austria": "at", "Belgium": "be", "Brazil": "br", "Mexico": "mx",
    "Japan": "jp", "Sweden": "se", "Switzerland": "ch", "Portugal": "pt",
    "Czechia": "cz", "Denmark": "dk", "Norway": "no"
}

with st.sidebar:
    st.header("🎯 Search settings")
    search_scope = st.radio("Search scope", ["Choose countries", "Worldwide (configured countries)", "Remote worldwide"], index=0)
    if search_scope == "Choose countries":
        selected_countries = st.multiselect(
            "Countries to search", list(country_options.keys()),
            default=["India", "United Arab Emirates"],
            help="Select one or more countries. Provider coverage varies by country."
        )
    elif search_scope == "Worldwide (configured countries)":
        selected_countries = list(country_options.keys())
        st.success(f"{len(selected_countries)} countries selected")
    else:
        selected_countries = []
        st.info("Remote listings only. Remote eligibility can still vary by country.")
    city = st.text_input("City or region (optional)", placeholder="Dubai, Toronto, Berlin…")
    experience = st.selectbox("Experience level", ["Any", "Internship", "Entry level / Graduate", "1–3 years", "3–5 years", "5+ years"])
    work_type = st.selectbox("Work arrangement", ["Any", "Remote", "Hybrid", "On-site"])
    visa = st.checkbox("Prioritize visa sponsorship")
    max_results = st.slider("Maximum results", 10, 100, 40, step=10)
    st.divider()
    st.caption("API keys are optional for basic feeds. Adzuna and Jooble require credentials.")

tab_search, tab_saved, tab_help = st.tabs(["🔎 Find jobs", "📌 Saved jobs", "ℹ️ Setup & limitations"])

with tab_search:
    left, right = st.columns([1.25, 1])
    with left:
        uploaded_cv = st.file_uploader("1. Upload your CV (PDF)", type=["pdf"], help="Text-based PDFs work best. Scanned-image PDFs need OCR.")
        job_query = st.text_input("2. Desired job or role", placeholder="e.g. Junior Data Analyst, HR Associate, Python Developer")
    with right:
        extra_preferences = st.text_area("3. Preferences (optional)", placeholder="e.g. minimum salary, visa sponsorship, industries, skills, company type", height=100)
        st.caption("Your location is separate from the job location you select in the sidebar.")

    cv_text = ""
    if uploaded_cv:
        try:
            reader = PdfReader(BytesIO(uploaded_cv.getvalue()))
            cv_text = "\n".join(page.extract_text() or "" for page in reader.pages).strip()
            if cv_text:
                st.success(f"CV parsed: approximately {len(cv_text.split())} words extracted.")
                with st.expander("Review extracted CV text"):
                    st.text(cv_text[:5000])
            else:
                st.warning("No selectable text found. This may be a scanned PDF; OCR is not included in this version.")
        except Exception as exc:
            st.error(f"Could not read this PDF: {exc}")

    search_clicked = st.button("🌐 Search and rank jobs", type="primary", use_container_width=True)
    if search_clicked:
        if not uploaded_cv:
            st.error("Upload your CV first.")
        elif not job_query.strip():
            st.error("Enter the job role you want.")
        elif search_scope == "Choose countries" and not selected_countries and work_type != "Remote":
            st.error("Select at least one country or choose Remote worldwide.")
        else:
            country_codes = [country_options[c] for c in selected_countries]
            query_parts = [job_query.strip()]
            if experience != "Any":
                query_parts.append(experience)
            if visa:
                query_parts.append("visa sponsorship")
            if extra_preferences.strip():
                query_parts.append(extra_preferences.strip())
            query = " ".join(query_parts)
            with st.spinner("Searching available job sources, removing duplicates, and ranking results…"):
                results, source_notes = search_jobs(
                    query=query,
                    countries=country_codes,
                    city=city.strip(),
                    remote_only=(search_scope == "Remote worldwide" or work_type == "Remote"),
                    max_results=max_results
                )
                results = score_jobs(results, cv_text, job_query, extra_preferences)
                if work_type in ("Hybrid", "On-site"):
                    wanted = work_type.lower()
                    filtered = [j for j in results if wanted in (j.get("job_type", "") + " " + j.get("description", "")).lower()]
                    if filtered:
                        results = filtered
            st.session_state["jobs"] = results
            st.session_state["source_notes"] = source_notes
            st.session_state["last_search"] = {"role": job_query, "countries": selected_countries, "city": city}

    if "source_notes" in st.session_state:
        with st.expander("Job-source status", expanded=False):
            for note in st.session_state["source_notes"]:
                st.write("• " + note)

    jobs = st.session_state.get("jobs", [])
    if jobs:
        st.subheader(f"Results · {len(jobs)} opportunities")
        sort_mode = st.selectbox("Sort results", ["Best CV match", "Newest not guaranteed — source order", "Company name"], key="sort_mode")
        if sort_mode == "Best CV match":
            jobs = sorted(jobs, key=lambda x: x.get("match_score", 0), reverse=True)
        elif sort_mode == "Company name":
            jobs = sorted(jobs, key=lambda x: x.get("company", "").lower())
        st.caption("Match scores are heuristic estimates from CV, role, and listing text. They are not hiring probabilities.")
        export_df = pd.DataFrame(jobs)
        csv = export_df.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Export results as CSV", data=csv, file_name="jobpilot_results.csv", mime="text/csv")
        min_score = st.slider("Minimum match score", 0, 90, 0, step=5)
        visible_jobs = [j for j in jobs if int(j.get("match_score", 0)) >= min_score]
        st.caption(f"Showing {len(visible_jobs)} jobs above the selected score.")
        for job in visible_jobs:
            with st.container(border=True):
                c1, c2 = st.columns([5, 1])
                with c1:
                    title = job.get("title", "Untitled role")
                    url = job.get("url", "")
                    if url:
                        st.markdown(f"### [{title}]({url})")
                    else:
                        st.markdown(f"### {title}")
                    st.write(f"**{job.get('company', 'Company not listed')}** · {job.get('location', 'Location not listed')}")
                    tags = [job.get("source", ""), job.get("job_type", ""), job.get("salary", "")]
                    st.caption(" · ".join(str(t) for t in tags if t))
                    description = str(job.get("description", "") or "")
                    if description:
                        st.write(description[:500] + ("…" if len(description) > 500 else ""))
                    st.caption("**Match explanation:** " + str(job.get("match_reason", "Broad role match.")))
                with c2:
                    st.metric("CV match", f"{int(job.get('match_score', 0))}%")
                    if st.button("Save", key=f"save_{job.get('id')}"):
                        save_job(job)
                        st.success("Saved")
    elif "jobs" in st.session_state:
        st.warning("No jobs returned. Check source status below, broaden your search, or configure API keys.")

with tab_saved:
    st.subheader("Your saved opportunities")
    saved = get_saved_jobs()
    if saved:
        st.write(f"{len(saved)} saved jobs")
        saved_df = pd.DataFrame(saved)
        st.dataframe(saved_df[["title", "company", "location", "source", "status"]], use_container_width=True, hide_index=True)
        for item in saved:
            with st.expander(f"{item['title']} — {item['company']}"):
                st.write(item.get("location", ""))
                if item.get("url"):
                    st.link_button("Open original listing", item["url"])
                status_options = ["Saved", "Applied", "Interview", "Offer", "Rejected"]
                status = st.selectbox("Status", status_options, index=status_options.index(item["status"]), key=f"status_{item['id']}")
                b1, b2 = st.columns(2)
                with b1:
                    if st.button("Update status", key=f"update_{item['id']}"):
                        update_status(item["id"], status)
                        st.rerun()
                with b2:
                    if st.button("Remove saved job", key=f"delete_{item['id']}"):
                        delete_saved_job(item["id"])
                        st.rerun()
        st.download_button("Export saved jobs CSV", data=saved_df.to_csv(index=False).encode("utf-8"), file_name="jobpilot_saved_jobs.csv", mime="text/csv")
    else:
        st.info("Save a job from the results tab to start tracking applications.")

with tab_help:
    st.subheader("Configure job sources")
    st.markdown("""
**Optional API integrations**
- **Adzuna:** create developer credentials at [developer.adzuna.com](https://developer.adzuna.com/).
- **Jooble:** request an API key at [Jooble API](https://jooble.org/api/about).
- **Arbeitnow:** public feed, with stronger European coverage.
- **Remotive:** remote-job feed.

Create a `.env` file beside `app.py` using `.env.example`, add your keys, and restart the app.

**Limitations**
- This is an MVP, not an exhaustive index of all vacancies worldwide.
- Each provider has its own country coverage, quota, freshness, and usage terms.
- CV match scores are explainable keyword heuristics, not a trained AI model.
- Scanned PDFs need OCR; automatic applications are not performed.
- Always confirm job details on the employer's official application page.
""")
    st.info("Privacy: the app reads CV text in memory and does not save the uploaded CV to the local database. Do not deploy publicly without adding authentication and privacy controls.")

st.divider()
st.caption("JobPilot AI · MVP · Always verify listings before sharing personal information or applying.")
