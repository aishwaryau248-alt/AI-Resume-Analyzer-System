import streamlit as st
import requests
import pandas as pd

API_BASE = "http://localhost:8000"

st.set_page_config(
    page_title="Resume Analyzer",
    page_icon="📄",
    layout="wide",
)

# ── Global Styles ──────────────────────────────────────────────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

.stApp {
    background: #0F1117;
    color: #E2E8F0;
}

[data-testid="stSidebar"] {
    background: #161B27 !important;
    border-right: 1px solid #2D3748;
}

header[data-testid="stHeader"] { background: transparent; }

.card {
    background: #1A2133;
    border: 1px solid #2D3748;
    border-radius: 12px;
    padding: 20px 24px;
    margin-bottom: 16px;
}

.card-accent {
    background: linear-gradient(135deg, #1A2133 0%, #1E2A44 100%);
    border: 1px solid #3B4F72;
    border-radius: 12px;
    padding: 20px 24px;
    margin-bottom: 16px;
}

.badge-found {
    display: inline-block;
    background: rgba(34,197,94,0.15);
    color: #86EFAC;
    border: 1px solid rgba(34,197,94,0.3);
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 500;
    margin: 3px;
}
.badge-missing {
    display: inline-block;
    background: rgba(239,68,68,0.15);
    color: #FCA5A5;
    border: 1px solid rgba(239,68,68,0.3);
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 500;
    margin: 3px;
}

[data-testid="stFileUploader"] {
    background: #1A2133;
    border: 2px dashed #3B4F72;
    border-radius: 12px;
    padding: 12px;
}

.metric-box {
    background: #1A2133;
    border: 1px solid #2D3748;
    border-radius: 10px;
    padding: 16px 20px;
    text-align: center;
}
.metric-label { font-size: 12px; color: #94A3B8; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 6px; }
.metric-value { font-size: 26px; font-weight: 700; color: #F1F5F9; }
.metric-sub   { font-size: 12px; color: #64748B; margin-top: 4px; }

.section-head {
    font-size: 13px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #64748B;
    margin: 24px 0 12px 0;
}

.progress-track {
    background: #2D3748;
    border-radius: 6px;
    height: 8px;
    width: 100%;
    margin-top: 6px;
}
.progress-fill {
    height: 8px;
    border-radius: 6px;
}

.reco-box {
    background: #0D1424;
    border-left: 3px solid #6366F1;
    border-radius: 0 10px 10px 0;
    padding: 16px 20px;
    font-size: 14px;
    line-height: 1.9;
    color: #CBD5E1;
    white-space: pre-wrap;
}

.item-row {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    padding: 8px 0;
    border-bottom: 1px solid #1E2A3A;
    font-size: 14px;
    color: #CBD5E1;
}
.item-row:last-child { border-bottom: none; }

.pill {
    display: inline-block;
    padding: 3px 14px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 600;
}
.pill-excellent { background: rgba(34,197,94,0.2); color: #86EFAC; }
.pill-good      { background: rgba(245,158,11,0.2); color: #FDE68A; }
.pill-average   { background: rgba(249,115,22,0.2); color: #FDBA74; }
.pill-poor      { background: rgba(239,68,68,0.2); color: #FCA5A5; }

/* Input fields */
[data-testid="stTextInput"] input {
    background: #1A2133 !important;
    border: 1px solid #2D3748 !important;
    border-radius: 8px !important;
    color: #F1F5F9 !important;
    padding: 10px 14px !important;
}
[data-testid="stTextInput"] input:focus {
    border-color: #6366F1 !important;
    box-shadow: 0 0 0 2px rgba(99,102,241,0.2) !important;
}
[data-testid="stTextInput"] label {
    color: #94A3B8 !important;
    font-size: 13px !important;
    font-weight: 500 !important;
}

.stButton > button {
    background: linear-gradient(135deg, #6366F1, #8B5CF6);
    color: white;
    border: none;
    border-radius: 8px;
    padding: 10px 28px;
    font-weight: 600;
    font-size: 15px;
    width: 100%;
    transition: opacity 0.2s;
}
.stButton > button:hover { opacity: 0.88; }

.stTabs [data-baseweb="tab-list"] {
    background: #161B27;
    border-radius: 8px;
    padding: 4px;
    gap: 4px;
}
.stTabs [data-baseweb="tab"] {
    background: transparent;
    color: #64748B;
    border-radius: 6px;
    font-weight: 500;
}
.stTabs [aria-selected="true"] {
    background: #1A2133 !important;
    color: #F1F5F9 !important;
}

/* Warning / error box overrides */
[data-testid="stAlert"] {
    border-radius: 10px !important;
}
</style>
""", unsafe_allow_html=True)


# ── Helpers ────────────────────────────────────────────────────────────────────

def score_class(score):
    if score >= 85: return "excellent"
    if score >= 70: return "good"
    if score >= 50: return "average"
    return "poor"

def score_color(score):
    if score >= 85: return "#22C55E"
    if score >= 70: return "#F59E0B"
    if score >= 50: return "#F97316"
    return "#EF4444"

def pill(label, cls):
    return f'<span class="pill pill-{cls}">{label}</span>'

def badges(skills, kind="found"):
    cls = "badge-found" if kind == "found" else "badge-missing"
    return " ".join(f'<span class="{cls}">{s}</span>' for s in skills)

def progress_bar(pct, color):
    return f"""
    <div class="progress-track">
      <div class="progress-fill" style="width:{pct}%;background:{color}"></div>
    </div>"""

def score_ring_html(score, label):
    color = score_color(score)
    pct_deg = f"{score * 3.6}deg"
    return f"""
    <div style="text-align:center">
      <div style="
        width:110px;height:110px;border-radius:50%;margin:0 auto 8px;
        background: conic-gradient({color} {pct_deg}, #2D3748 0);
        display:flex;align-items:center;justify-content:center;
        box-shadow: 0 0 20px {color}40;
      ">
        <div style="
          width:82px;height:82px;border-radius:50%;background:#0F1117;
          display:flex;align-items:center;justify-content:center;
          font-size:22px;font-weight:700;color:{color}
        ">{score}%</div>
      </div>
      <div style="font-size:12px;color:#94A3B8;text-transform:uppercase;letter-spacing:.08em">{label}</div>
    </div>"""


# ── Sidebar ────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## 📄 Resume Analyzer")
    st.markdown("---")
    page = st.radio("", ["Upload & Analyze", "History"], label_visibility="collapsed")
    st.markdown("---")

    try:
        r = requests.get(API_BASE + "/", timeout=3)
        if r.status_code == 200:
            st.success("API connected")
        else:
            st.error(f"API error {r.status_code}")
    except Exception:
        st.error("API unreachable")

    st.caption(f"`{API_BASE}`")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 1 — Upload & Analyze
# ══════════════════════════════════════════════════════════════════════════════

if page == "Upload & Analyze":

    st.markdown("# Resume Analyzer")
    st.markdown(
        '<p style="color:#64748B;margin-top:-12px">'
        'Drop your resume — get role detection, ATS score, and AI recommendations instantly.'
        '</p>',
        unsafe_allow_html=True
    )
    st.markdown("---")

    # ── User Info Fields ──
    col_name, col_email = st.columns(2)
    with col_name:
        user_name = st.text_input("Full Name", placeholder="e.g. Elon Musk")
    with col_email:
        user_email = st.text_input("Email Address", placeholder="e.g. elon@musk.com")

    st.markdown("<div style='margin-top:8px'></div>", unsafe_allow_html=True)

    # ── File Uploader ──
    uploaded_file = st.file_uploader(
        "Drop your resume here (PDF, DOC, DOCX)",
        type=["pdf", "doc", "docx"],
    )

    if uploaded_file:
        st.markdown(
            f'<div style="color:#94A3B8;font-size:13px;margin:6px 0 16px">'
            f'📎 {uploaded_file.name} — {round(len(uploaded_file.getvalue())/1024, 1)} KB'
            f'</div>',
            unsafe_allow_html=True
        )

        analyze_btn = st.button("Analyze Resume →", type="primary")

        if analyze_btn:
            # Validate inputs
            if not user_name.strip():
                st.warning("Please enter your full name before analyzing.")
            elif not user_email.strip():
                st.warning("Please enter your email address before analyzing.")
            elif "@" not in user_email or "." not in user_email:
                st.warning("Please enter a valid email address.")
            else:
                with st.spinner("Analyzing your resume…"):
                    try:
                        response = requests.post(
                            API_BASE + "/upload-resume",
                            params={
                                "name": user_name.strip(),
                                "email": user_email.strip()
                            },
                            files={
                                "file": (
                                    uploaded_file.name,
                                    uploaded_file.getvalue(),
                                    uploaded_file.type
                                )
                            },
                            timeout=60,
                        )

                        if response.status_code == 200:
                            d = response.json()
                            st.session_state["result"] = d
                            st.session_state["analyzed_name"] = user_name.strip()
                        else:
                            try:
                                err = response.json().get("detail", response.text)
                            except Exception:
                                err = response.text
                            st.error(f"API Error: {err}")

                    except requests.exceptions.ConnectionError:
                        st.error(f"Cannot reach API at {API_BASE}. Make sure FastAPI is running.")
                    except requests.exceptions.Timeout:
                        st.error("Request timed out. The server may be busy — try again.")
                    except Exception as e:
                        st.error(f"Unexpected error: {e}")

    # ── Results ──
    if "result" in st.session_state:
        d = st.session_state["result"]
        ats = d["ats_score"]
        role_match = d["role_match_score"]
        status = d["ats_status"]
        cls = score_class(ats)
        analyzed_name = st.session_state.get("analyzed_name", "")

        st.markdown("---")

        # Greeting
        if analyzed_name:
            st.markdown(
                f'<div style="font-size:14px;color:#64748B;margin-bottom:4px">'
                f'Results for <span style="color:#818CF8;font-weight:600">{analyzed_name}</span>'
                f'</div>',
                unsafe_allow_html=True
            )

        # Role + Status
        col_role, col_status = st.columns([3, 1])
        with col_role:
            st.markdown(
                f'<div style="font-size:22px;font-weight:700;color:#F1F5F9">'
                f'Detected Role: <span style="color:#818CF8">{d["predicted_role"]}</span>'
                f'</div>',
                unsafe_allow_html=True
            )
        with col_status:
            st.markdown(
                f'<div style="text-align:right;padding-top:4px">{pill(status, cls)}</div>',
                unsafe_allow_html=True
            )

        st.markdown(
            f'<div style="color:#64748B;font-size:14px;margin:8px 0 20px">{d["summary"]}</div>',
            unsafe_allow_html=True
        )

        # ── Score Row ──
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(score_ring_html(ats, "ATS Score"), unsafe_allow_html=True)
        with c2:
            st.markdown(score_ring_html(int(role_match), "Role Match"), unsafe_allow_html=True)
        with c3:
            found = len(d["found_skills"])
            total = found + len(d["missing_skills"])
            ratio_pct = int(found / total * 100) if total else 0
            st.markdown(f"""
            <div style="text-align:center;padding-top:16px">
              <div style="font-size:32px;font-weight:700;color:#F1F5F9">
                {found}<span style="font-size:16px;color:#64748B">/{total}</span>
              </div>
              <div style="font-size:12px;color:#94A3B8;text-transform:uppercase;letter-spacing:.08em;margin-top:4px">
                Skills Matched
              </div>
              {progress_bar(ratio_pct, score_color(ratio_pct))}
            </div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Tabs ──
        tab1, tab2, tab3 = st.tabs(["  Skills  ", "  Strengths & Improvements  ", "  AI Recommendations  "])

        with tab1:
            sc1, sc2 = st.columns(2)
            with sc1:
                st.markdown('<div class="section-head">✅ Found Skills</div>', unsafe_allow_html=True)
                if d["found_skills"]:
                    st.markdown(f'<div class="card">{badges(d["found_skills"], "found")}</div>', unsafe_allow_html=True)
                else:
                    st.markdown('<div class="card" style="color:#64748B">No matching skills detected.</div>', unsafe_allow_html=True)
            with sc2:
                st.markdown('<div class="section-head">❌ Missing Skills</div>', unsafe_allow_html=True)
                if d["missing_skills"]:
                    st.markdown(f'<div class="card">{badges(d["missing_skills"], "missing")}</div>', unsafe_allow_html=True)
                else:
                    st.markdown('<div class="card" style="color:#86EFAC">All required skills found!</div>', unsafe_allow_html=True)

        with tab2:
            sc1, sc2 = st.columns(2)
            with sc1:
                st.markdown('<div class="section-head">💪 Strengths</div>', unsafe_allow_html=True)
                items = "".join(
                    f'<div class="item-row"><span style="color:#22C55E">▸</span>{s}</div>'
                    for s in d.get("strengths", [])
                )
                st.markdown(
                    f'<div class="card">{items or "<span style=color:#64748B>None identified</span>"}</div>',
                    unsafe_allow_html=True
                )
            with sc2:
                st.markdown('<div class="section-head">🔧 Improvements</div>', unsafe_allow_html=True)
                items = "".join(
                    f'<div class="item-row"><span style="color:#F59E0B">▸</span>{s}</div>'
                    for s in d.get("improvements", [])
                )
                st.markdown(
                    f'<div class="card">{items or "<span style=color:#64748B>None — great resume!</span>"}</div>',
                    unsafe_allow_html=True
                )

        with tab3:
            st.markdown('<div class="section-head">🤖 AI Recommendations</div>', unsafe_allow_html=True)
            reco = d.get("recommendations") or "No recommendations generated."
            st.markdown(f'<div class="reco-box">{reco}</div>', unsafe_allow_html=True)

    elif not uploaded_file:
        st.markdown("""
        <div style="text-align:center;padding:60px 20px;color:#334155">
          <div style="font-size:48px;margin-bottom:16px">📄</div>
          <div style="font-size:16px;font-weight:600;color:#475569">Upload your resume to get started</div>
          <div style="font-size:14px;margin-top:8px">Fill in your name and email, then select a PDF, DOC, or DOCX file</div>
        </div>
        """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 2 — History
# ══════════════════════════════════════════════════════════════════════════════

elif page == "History":
    st.markdown("# Analysis History")
    st.markdown(
        '<p style="color:#64748B;margin-top:-12px">All past resume analyses.</p>',
        unsafe_allow_html=True
    )
    st.markdown("---")

    col_refresh, _ = st.columns([1, 5])
    with col_refresh:
        if st.button("↺ Refresh"):
            st.rerun()

    try:
        response = requests.get(API_BASE + "/analysis-history", timeout=10)

        if response.status_code == 200:
            data = response.json()

            if not data:
                st.markdown("""
                <div style="text-align:center;padding:60px;color:#334155">
                  <div style="font-size:40px">📭</div>
                  <div style="margin-top:12px;font-size:15px;color:#475569">
                    No analyses yet. Upload a resume first.
                  </div>
                </div>""", unsafe_allow_html=True)
            else:
                scores = [round(r.get("score", 0)) for r in data]

                m1, m2, m3 = st.columns(3)
                with m1:
                    st.markdown(
                        f'<div class="metric-box">'
                        f'<div class="metric-label">Total Analyses</div>'
                        f'<div class="metric-value">{len(data)}</div>'
                        f'</div>',
                        unsafe_allow_html=True
                    )
                with m2:
                    avg = round(sum(scores) / len(scores))
                    st.markdown(
                        f'<div class="metric-box">'
                        f'<div class="metric-label">Average Score</div>'
                        f'<div class="metric-value" style="color:{score_color(avg)}">{avg}%</div>'
                        f'</div>',
                        unsafe_allow_html=True
                    )
                with m3:
                    best = max(scores)
                    st.markdown(
                        f'<div class="metric-box">'
                        f'<div class="metric-label">Best Score</div>'
                        f'<div class="metric-value" style="color:{score_color(best)}">{best}%</div>'
                        f'</div>',
                        unsafe_allow_html=True
                    )

                st.markdown("<br>", unsafe_allow_html=True)

                rows = []
                for r in reversed(data):
                    sc = round(r.get("score", 0))
                    rows.append({
                        "Resume ID": r.get("resume_id"),
                        "Role": r.get("role"),
                        "Score": f"{sc}%",
                        "Missing Skills": r.get("missing_skills") or "—",
                        "Date": (r.get("created_at") or "")[:10] or "—",
                    })

                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

                st.markdown("### Score Trend")
                chart_data = pd.DataFrame({
                    "Analysis": [f"#{i+1}" for i in range(len(scores))],
                    "Score (%)": scores,
                })
                st.bar_chart(chart_data.set_index("Analysis"))

        else:
            st.error(f"Failed to load history: {response.status_code}")

    except requests.exceptions.ConnectionError:
        st.error(f"Cannot reach API at {API_BASE}.")
    except Exception as e:
        st.error(f"Error: {e}")