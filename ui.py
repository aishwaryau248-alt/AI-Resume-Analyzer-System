import streamlit as st
import requests
import pandas as pd

# ── Config ────────────────────────────────────────────────────────────────────

API_BASE = "http://localhost:8000"

ROLES = [
    "Data Scientist", "Data Analyst", "Backend Developer",
    "Frontend Developer", "Full Stack Developer", "AI Engineer",
    "Machine Learning Engineer", "DevOps Engineer", "Cloud Engineer",
    "Cyber Security Analyst", "Software Engineer", "Java Developer",
    "Python Developer", "Mobile App Developer", "Android Developer",
    "iOS Developer", "Database Administrator", "Business Analyst",
    "QA Engineer", "Project Manager",
]

st.set_page_config(
    page_title="Resume Analyzer",
    page_icon="📄",
    layout="wide",
)

# ── Sidebar navigation ────────────────────────────────────────────────────────

st.sidebar.title("📄 Resume Analyzer")
st.sidebar.markdown("---")
page = st.sidebar.radio(
    "Navigate",
    ["Upload Resume", "Analyze Resume", "Analysis History", "View / Delete Resume"],
    label_visibility="collapsed",
)

st.sidebar.markdown("---")
st.sidebar.caption(f"API: `{API_BASE}`")

# health check
try:
    r = requests.get(API_BASE + "/", timeout=3)
    if r.status_code == 200:
        st.sidebar.success("API connected")
    else:
        st.sidebar.error("API error " + str(r.status_code))
except Exception:
    st.sidebar.error("API unreachable")

# ── Helpers ───────────────────────────────────────────────────────────────────

def score_color(score: float) -> str:
    if score >= 70:
        return "normal"
    elif score >= 40:
        return "off"
    return "inverse"


def skill_badges(skills: list, color: str) -> str:
    """Return HTML badge string for a list of skills."""
    bg = "#d4edda" if color == "green" else "#f8d7da"
    fg = "#155724" if color == "green" else "#721c24"
    return " ".join(
        f'<span style="background:{bg};color:{fg};padding:3px 10px;'
        f'border-radius:12px;font-size:13px;margin:2px;display:inline-block">{s}</span>'
        for s in skills
    )

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 1 — Upload Resume
# ══════════════════════════════════════════════════════════════════════════════

if page == "Upload Resume":
    st.title("Upload Resume")
    st.caption("Upload a PDF, DOC, or DOCX resume to extract its text and save it.")

    uploaded_file = st.file_uploader(
        "Choose a resume file",
        type=["pdf", "doc", "docx"],
        help="Max 5 MB. Only PDF, DOC, DOCX accepted.",
    )

    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input("Your name (optional)")
    with col2:
        email = st.text_input("Your email (optional)")

    if st.button("Upload Resume", type="primary", disabled=uploaded_file is None):
        with st.spinner("Uploading and extracting text…"):
            try:
                files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                response = requests.post(API_BASE + "/upload-resume", files=files, timeout=30)

                if response.status_code == 200:
                    data = response.json()
                    st.success(f"Uploaded successfully — Resume ID: **{data['resume_id']}**")
                    st.session_state["last_resume_id"] = data["resume_id"]

                    with st.expander("Extracted text preview", expanded=False):
                        st.text(data.get("text", "")[:1000] + ("…" if len(data.get("text","")) > 1000 else ""))

                    st.info(f"Use Resume ID **{data['resume_id']}** in the Analyze tab.")
                else:
                    st.error(f"Upload failed: {response.json().get('detail', response.text)}")

            except requests.exceptions.ConnectionError:
                st.error("Cannot reach the API. Make sure FastAPI is running on " + API_BASE)
            except Exception as e:
                st.error(f"Error: {e}")

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 2 — Analyze Resume
# ══════════════════════════════════════════════════════════════════════════════

elif page == "Analyze Resume":
    st.title("Analyze Resume")
    st.caption("Enter a resume ID and target role to get a skill match score and AI recommendations.")

    default_id = st.session_state.get("last_resume_id", 1)

    col1, col2 = st.columns([1, 2])
    with col1:
        resume_id = st.number_input("Resume ID", min_value=1, value=default_id, step=1)
    with col2:
        role = st.selectbox("Target role", ROLES)

    if st.button("Run Analysis", type="primary"):
        with st.spinner("Analyzing resume with AI…"):
            try:
                response = requests.post(
                    f"{API_BASE}/analyze/{resume_id}",
                    params={"role": role},
                    timeout=60,
                )

                if response.status_code == 200:
                    data = response.json()
                    score = round(data["score"])
                    found = data.get("found_skills", [])
                    missing = data.get("missing_skills", [])
                    reco = data.get("recommendations", "")

                    # Score cards
                    st.markdown("### Results")
                    m1, m2, m3 = st.columns(3)
                    m1.metric("Match Score", f"{score}%")
                    m2.metric("Skills Found", len(found))
                    m3.metric("Skills Missing", len(missing))

                    # Score bar
                    bar_color = "green" if score >= 70 else ("orange" if score >= 40 else "red")
                    st.markdown(
    f'''
    <div style="
        background:#1E293B;
        color:#FFFFFF;
        border-left:4px solid #7F77DD;
        padding:15px;
        border-radius:8px;
        font-size:16px;
        line-height:1.8;
        white-space:pre-wrap;
    ">
        {reco}
    </div>
    ''',
    unsafe_allow_html=True
)

                    # Skills breakdown
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.markdown("**Found skills**")
                        if found:
                            st.markdown(skill_badges(found, "green"), unsafe_allow_html=True)
                        else:
                            st.caption("None detected")

                    with col_b:
                        st.markdown("**Missing skills**")
                        if missing:
                            st.markdown(skill_badges(missing, "red"), unsafe_allow_html=True)
                        else:
                            st.caption("None — great match!")

                    # AI recommendations
                    st.markdown("### AI Recommendations")
                    st.markdown(
                        f'<div style="background:#f8f9fa;border-left:3px solid #7F77DD;padding:12px 16px;'
                        f'border-radius:4px;font-size:14px;line-height:1.7;white-space:pre-wrap">{reco}</div>',
                        unsafe_allow_html=True,
                    )

                elif response.status_code == 404:
                    st.error("Resume not found. Check the ID.")
                elif response.status_code == 400:
                    st.error(f"Bad request: {response.json().get('detail')}")
                else:
                    st.error(f"Error {response.status_code}: {response.text}")

            except requests.exceptions.ConnectionError:
                st.error("Cannot reach the API. Make sure FastAPI is running on " + API_BASE)
            except Exception as e:
                st.error(f"Error: {e}")

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 3 — Analysis History
# ══════════════════════════════════════════════════════════════════════════════

elif page == "Analysis History":
    st.title("Analysis History")
    st.caption("All past resume analyses stored in the database.")

    if st.button("Refresh", type="secondary"):
        st.rerun()

    try:
        response = requests.get(API_BASE + "/analysis-history", timeout=10)

        if response.status_code == 200:
            data = response.json()

            if not data:
                st.info("No analyses yet. Upload and analyze a resume first.")
            else:
                # Summary metrics
                scores = [round(r.get("score", 0)) for r in data]
                m1, m2, m3 = st.columns(3)
                m1.metric("Total analyses", len(data))
                m2.metric("Average score", f"{round(sum(scores)/len(scores))}%")
                m3.metric("Best score", f"{max(scores)}%")

                st.markdown("---")

                # Table
                rows = []
                for r in reversed(data):
                    sc = round(r.get("score", 0))
                    rows.append({
                        "Resume ID": r.get("resume_id"),
                        "Role": r.get("role"),
                        "Score": f"{sc}%",
                        "Strengths": r.get("strengths", ""),
                        "Missing": r.get("missing_skills", ""),
                        "Date": r.get("created_at", "")[:10] if r.get("created_at") else "—",
                    })

                df = pd.DataFrame(rows)
                st.dataframe(df, use_container_width=True, hide_index=True)

                # Score chart
                st.markdown("### Score trend")
                chart_data = pd.DataFrame({
                    "Analysis": [f"#{i+1}" for i in range(len(scores))],
                    "Score (%)": scores,
                })
                st.bar_chart(chart_data.set_index("Analysis"))

        else:
            st.error(f"Failed to load history: {response.status_code}")

    except requests.exceptions.ConnectionError:
        st.error("Cannot reach the API. Make sure FastAPI is running on " + API_BASE)
    except Exception as e:
        st.error(f"Error: {e}")

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 4 — View / Delete Resume
# ══════════════════════════════════════════════════════════════════════════════

elif page == "View / Delete Resume":
    st.title("View / Delete Resume")
    st.caption("Fetch resume details by ID or permanently delete a resume.")

    resume_id = st.number_input("Resume ID", min_value=1, step=1)

    col1, col2 = st.columns([1, 4])
    fetch = col1.button("Fetch", type="primary")
    delete = col2.button("Delete", type="secondary")

    if fetch:
        try:
            response = requests.get(f"{API_BASE}/resume/{resume_id}", timeout=10)
            if response.status_code == 200:
                data = response.json()
                st.success(f"**{data['file_name']}** — ID {data['id']}")
                st.caption(f"Uploaded: {data.get('uploaded_at', '—')}")
                with st.expander("Extracted text", expanded=True):
                    st.text(
                        (data.get("extracted_text") or "No text extracted.")[:1500]
                        + ("…" if len(data.get("extracted_text") or "") > 1500 else "")
                    )
            elif response.status_code == 404:
                st.error("Resume not found.")
            else:
                st.error(f"Error {response.status_code}")
        except requests.exceptions.ConnectionError:
            st.error("Cannot reach the API.")
        except Exception as e:
            st.error(f"Error: {e}")

    if delete:
        confirm = st.warning(f"Are you sure you want to delete resume #{resume_id}? This cannot be undone.")
        if st.button("Yes, delete", type="primary"):
            try:
                response = requests.delete(f"{API_BASE}/resume/{resume_id}", timeout=10)
                if response.status_code == 200:
                    st.success("Resume deleted successfully.")
                elif response.status_code == 404:
                    st.error("Resume not found.")
                else:
                    st.error(f"Error {response.status_code}")
            except requests.exceptions.ConnectionError:
                st.error("Cannot reach the API.")
            except Exception as e:
                st.error(f"Error: {e}")