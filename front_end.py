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

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

.stApp { background: #0F1117; color: #E2E8F0; }

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
.progress-fill { height: 8px; border-radius: 6px; }

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
.pill-excellent { background: rgba(34,197,94,0.2);  color: #86EFAC; }
.pill-good      { background: rgba(245,158,11,0.2); color: #FDE68A; }
.pill-average   { background: rgba(249,115,22,0.2); color: #FDBA74; }
.pill-poor      { background: rgba(239,68,68,0.2);  color: #FCA5A5; }
.pill-agent     { background: rgba(99,102,241,0.2); color: #A5B4FC; }

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

[data-testid="stAlert"] { border-radius: 10px !important; }
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
    color    = score_color(score)
    pct_deg  = f"{score * 3.6}deg"
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

def auth_headers():
    token = st.session_state.get("token", "")
    return {"Authorization": f"Bearer {token}"} if token else {}


# ── Session state init ─────────────────────────────────────────────────────────

if "token"     not in st.session_state: st.session_state["token"]     = ""
if "user_role" not in st.session_state: st.session_state["user_role"] = ""
if "user_name" not in st.session_state: st.session_state["user_name"] = ""


# ── Sidebar ────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## 📄 Resume Analyzer")
    st.markdown("---")

    # ── Auth state ──
    if st.session_state["token"]:
        role  = st.session_state["user_role"]
        uname = st.session_state["user_name"]
        role_badge = pill("AGENT", "agent") if role == "AGENT" else pill("USER", "good")

        st.markdown(
            f'<div style="font-size:14px;color:#CBD5E1">👤 <b>{uname}</b><br>'
            f'<span style="font-size:12px">{role_badge}</span></div>',
            unsafe_allow_html=True
        )
        st.markdown("")

        if role == "AGENT":
            page_options = ["Upload & Analyze", "My History", "Agent Dashboard"]
        else:
            page_options = ["Upload & Analyze", "My History"]

        page = st.radio("", page_options, label_visibility="collapsed")
        st.markdown("---")

        if st.button("🚪 Logout"):
            st.session_state["token"]     = ""
            st.session_state["user_role"] = ""
            st.session_state["user_name"] = ""
            st.session_state.pop("result", None)
            st.rerun()
    else:
        page = "Auth"
        st.markdown('<div style="color:#64748B;font-size:13px">Login to continue</div>', unsafe_allow_html=True)

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
# AUTH PAGE (Login / Register / Forgot Password)
# ══════════════════════════════════════════════════════════════════════════════

if page == "Auth":
    st.markdown("# Welcome to Resume Analyzer")
    st.markdown('<p style="color:#64748B;margin-top:-12px">Login or create an account to get started.</p>', unsafe_allow_html=True)
    st.markdown("---")

    auth_tab1, auth_tab2, auth_tab3 = st.tabs(["  Login  ", "  Register  ", "  Forgot Password  "])

    # ── Login ──
    with auth_tab1:
        st.markdown("### Login")
        login_email    = st.text_input("Email", placeholder="you@example.com", key="login_email")
        login_password = st.text_input("Password", type="password", key="login_password")

        if st.button("Login →", key="login_btn"):
            if not login_email or not login_password:
                st.warning("Enter both email and password.")
            else:
                try:
                    resp = requests.post(
                        API_BASE + "/login",
                        params={"email": login_email, "password": login_password},
                        timeout=10,
                    )
                    if resp.status_code == 200:
                        token = resp.json()["access_token"]
                        st.session_state["token"] = token

                        # Fetch user info
                        me_resp = requests.get(
                            API_BASE + "/me",
                            headers={"Authorization": f"Bearer {token}"},
                            timeout=10,
                        )
                        if me_resp.status_code == 200:
                            me = me_resp.json()
                            st.session_state["user_role"] = me["role"]
                            st.session_state["user_name"] = me["name"]

                        st.success("Logged in!")
                        st.rerun()
                    else:
                        err = resp.json().get("detail", resp.text)
                        st.error(f"Login failed: {err}")
                except Exception as e:
                    st.error(f"Error: {e}")

        st.markdown("")
        st.markdown(
            '<div style="font-size:13px;color:#64748B">Forgot password? Use the "Forgot Password" tab above.</div>',
            unsafe_allow_html=True
        )

    # ── Register ──
    with auth_tab2:
        # State init for register flow
        if "reg_otp"      not in st.session_state: st.session_state["reg_otp"]      = ""
        if "reg_verified" not in st.session_state: st.session_state["reg_verified"] = False

        if not st.session_state["reg_otp"]:
            # ── Step 1: Fill in details ──
            st.markdown("### Create Account")
            reg_name     = st.text_input("Full Name",         placeholder="Your Name",       key="reg_name")
            reg_email    = st.text_input("Email",             placeholder="you@example.com", key="reg_email")
            reg_password = st.text_input("Password",          type="password",               key="reg_password")
            reg_confirm  = st.text_input("Confirm Password",  type="password",               key="reg_confirm")

            if st.button("Register →", key="reg_btn"):
                if not all([reg_name, reg_email, reg_password, reg_confirm]):
                    st.warning("Fill in all fields.")
                elif reg_password != reg_confirm:
                    st.error("Passwords do not match.")
                elif "@" not in reg_email:
                    st.warning("Enter a valid email.")
                else:
                    try:
                        resp = requests.post(
                            API_BASE + "/register",
                            params={"name": reg_name, "email": reg_email, "password": reg_password},
                            timeout=10,
                        )
                        if resp.status_code == 200:
                            data = resp.json()
                            st.session_state["reg_otp"] = data.get("otp", "")
                            st.rerun()
                        else:
                            try:
                                detail = resp.json().get("detail", "Registration failed")
                            except Exception:
                                detail = resp.text
                            st.error(detail)
                    except Exception as e:
                        st.error(f"Error: {e}")

        elif not st.session_state["reg_verified"]:
            # ── Step 2: Verify OTP ──
            st.markdown("### Verify Email")
            st.success(
                f"Registered! Your OTP is: **{st.session_state['reg_otp']}**  \n"
                "Enter it below to activate your account."
            )
            otp_input = st.text_input("OTP Code", placeholder="6-digit code", key="otp_input")

            col_v, col_b = st.columns([2, 1])
            with col_v:
                if st.button("Verify OTP →", key="verify_btn"):
                    if not otp_input.strip():
                        st.warning("Enter the OTP.")
                    else:
                        try:
                            v = requests.get(API_BASE + f"/verify-email/{otp_input.strip()}", timeout=10)
                            if v.status_code == 200:
                                st.session_state["reg_verified"] = True
                                st.rerun()
                            else:
                                try:
                                    detail = v.json().get("detail", "Invalid OTP")
                                except Exception:
                                    detail = v.text
                                st.error(detail)
                        except Exception as e:
                            st.error(f"Error: {e}")
            with col_b:
                if st.button("← Back", key="reg_back"):
                    st.session_state["reg_otp"] = ""
                    st.rerun()

        else:
            # ── Step 3: Done ──
            st.markdown("### ✅ Email Verified")
            st.success("Your account is active. Switch to the Login tab to sign in.")
            if st.button("Register another account", key="reg_again"):
                st.session_state["reg_otp"]      = ""
                st.session_state["reg_verified"] = False
                st.rerun()

    # ── Forgot Password ──
    with auth_tab3:
        # State init for forgot-password flow
        if "fp_token"   not in st.session_state: st.session_state["fp_token"]   = ""
        if "fp_done"    not in st.session_state: st.session_state["fp_done"]    = False

        if not st.session_state["fp_token"] and not st.session_state["fp_done"]:
            # ── Step 1: Enter email, request reset token ──
            st.markdown("### Forgot Password")
            st.markdown(
                '<div style="font-size:13px;color:#64748B;margin-bottom:8px">'
                'Enter the email linked to your account. We\'ll generate a reset code.'
                '</div>',
                unsafe_allow_html=True
            )
            fp_email = st.text_input("Email", placeholder="you@example.com", key="fp_email")

            if st.button("Send Reset Code →", key="fp_send_btn"):
                if not fp_email.strip():
                    st.warning("Enter your email.")
                else:
                    try:
                        resp = requests.post(
                            API_BASE + "/forgot-password",
                            params={"email": fp_email.strip()},
                            timeout=10,
                        )
                        if resp.status_code == 200:
                            data = resp.json()
                            otp = data.get("otp", "")
                            if otp:
                                st.session_state["fp_token"] = otp
                                st.rerun()
                            else:
                                # Backend returned the generic "if email exists" message
                                # (no matching user) — nothing to do but inform the user.
                                st.info(data.get("message", "If email exists, reset link sent."))
                        else:
                            try:
                                detail = resp.json().get("detail", "Request failed")
                            except Exception:
                                detail = resp.text
                            st.error(detail)
                    except Exception as e:
                        st.error(f"Error: {e}")

        elif st.session_state["fp_token"] and not st.session_state["fp_done"]:
            # ── Step 2: Enter token + new password ──
            st.markdown("### Reset Password")
            st.success(f"Reset code generated: **{st.session_state['fp_token']}**")

            fp_token_input = st.text_input(
                "Reset Code", value=st.session_state["fp_token"], key="fp_token_input"
            )
            fp_new_pw      = st.text_input("New Password", type="password", key="fp_new_pw")
            fp_confirm_pw  = st.text_input("Confirm New Password", type="password", key="fp_confirm_pw")

            col_r, col_b = st.columns([2, 1])
            with col_r:
                if st.button("Reset Password →", key="fp_reset_btn"):
                    if not fp_token_input.strip() or not fp_new_pw or not fp_confirm_pw:
                        st.warning("Fill in all fields.")
                    elif fp_new_pw != fp_confirm_pw:
                        st.error("Passwords do not match.")
                    else:
                        try:
                            resp = requests.post(
                                API_BASE + "/reset-password",
                                params={
                                    "token": fp_token_input.strip(),
                                    "new_password": fp_new_pw,
                                },
                                timeout=10,
                            )
                            if resp.status_code == 200:
                                st.session_state["fp_done"]  = True
                                st.session_state["fp_token"] = ""
                                st.rerun()
                            else:
                                try:
                                    detail = resp.json().get("detail", "Reset failed")
                                except Exception:
                                    detail = resp.text
                                st.error(detail)
                        except Exception as e:
                            st.error(f"Error: {e}")
            with col_b:
                if st.button("← Back", key="fp_back"):
                    st.session_state["fp_token"] = ""
                    st.rerun()

        else:
            # ── Step 3: Done ──
            st.markdown("### ✅ Password Reset")
            st.success("Your password has been reset. Switch to the Login tab to sign in.")
            if st.button("Reset another password", key="fp_again"):
                st.session_state["fp_token"] = ""
                st.session_state["fp_done"]  = False
                st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# PAGE — Upload & Analyze  (USER + AGENT)
# ══════════════════════════════════════════════════════════════════════════════

elif page == "Upload & Analyze":

    st.markdown("# Resume Analyzer")
    st.markdown(
        '<p style="color:#64748B;margin-top:-12px">'
        'Drop your resume — get role detection, ATS score, and AI recommendations instantly.'
        '</p>',
        unsafe_allow_html=True
    )
    st.markdown("---")

    uploaded_file = st.file_uploader(
        "Drop your resume here (PDF, DOC, DOCX, PNG, JPG)",
        type=["pdf", "doc", "docx", "png", "jpg", "jpeg", "webp", "bmp"],
    )

    if uploaded_file:
        st.markdown(
            f'<div style="color:#94A3B8;font-size:13px;margin:6px 0 16px">'
            f'📎 {uploaded_file.name} — {round(len(uploaded_file.getvalue())/1024, 1)} KB'
            f'</div>',
            unsafe_allow_html=True
        )

        if st.button("Analyze Resume →", type="primary"):
            with st.spinner("Analyzing your resume…"):
                try:
                    response = requests.post(
                        API_BASE + "/upload-resume",
                        headers=auth_headers(),
                        files={
                            "file": (
                                uploaded_file.name,
                                uploaded_file.getvalue(),
                                uploaded_file.type,
                            )
                        },
                        timeout=60,
                    )

                    if response.status_code == 200:
                        st.session_state["result"] = response.json()
                    elif response.status_code == 401:
                        st.error("Session expired. Please login again.")
                    else:
                        err = response.json().get("detail", response.text)
                        st.error(f"API Error: {err}")

                except requests.exceptions.ConnectionError:
                    st.error(f"Cannot reach API at {API_BASE}. Make sure FastAPI is running.")
                except requests.exceptions.Timeout:
                    st.error("Request timed out. Try again.")
                except Exception as e:
                    st.error(f"Unexpected error: {e}")

    # ── Results ──
    if "result" in st.session_state:
        d        = st.session_state["result"]
        ats      = d["ats_score"]
        role_match = d["role_match_score"]
        status   = d["ats_status"]
        cls      = score_class(ats)

        st.markdown("---")

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
          <div style="font-size:14px;margin-top:8px">Select a PDF, DOC, DOCX, or image file</div>
        </div>
        """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE — My History  (USER sees own only)
# ══════════════════════════════════════════════════════════════════════════════

elif page == "My History":
    st.markdown("# My Analysis History")
    st.markdown('<p style="color:#64748B;margin-top:-12px">Your past resume analyses.</p>', unsafe_allow_html=True)
    st.markdown("---")

    col_refresh, _ = st.columns([1, 5])
    with col_refresh:
        if st.button("↺ Refresh"):
            st.rerun()

    try:
        response = requests.get(
            API_BASE + "/my-history",
            headers=auth_headers(),
            timeout=10,
        )

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
                scores = [round(r.get("score") or 0) for r in data]

                m1, m2, m3 = st.columns(3)
                with m1:
                    st.markdown(
                        f'<div class="metric-box">'
                        f'<div class="metric-label">Total Analyses</div>'
                        f'<div class="metric-value">{len(data)}</div>'
                        f'</div>', unsafe_allow_html=True
                    )
                with m2:
                    avg = round(sum(scores) / len(scores))
                    st.markdown(
                        f'<div class="metric-box">'
                        f'<div class="metric-label">Average Score</div>'
                        f'<div class="metric-value" style="color:{score_color(avg)}">{avg}%</div>'
                        f'</div>', unsafe_allow_html=True
                    )
                with m3:
                    best = max(scores)
                    st.markdown(
                        f'<div class="metric-box">'
                        f'<div class="metric-label">Best Score</div>'
                        f'<div class="metric-value" style="color:{score_color(best)}">{best}%</div>'
                        f'</div>', unsafe_allow_html=True
                    )

                st.markdown("<br>", unsafe_allow_html=True)

                rows = []
                for r in reversed(data):
                    sc = round(r.get("score") or 0)
                    rows.append({
                        "Resume ID":      r.get("resume_id"),
                        "Role":           r.get("role"),
                        "Role Match":     f"{sc}%",
                        "ATS Score":      f"{round(r.get('ats_score') or 0)}%",
                        "ATS Status":     r.get("ats_status") or "—",
                        "Missing Skills": r.get("missing_skills") or "—",
                        "Date":           (r.get("created_at") or "")[:10] or "—",
                    })

                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

                st.markdown("### Score Trend")
                chart_data = pd.DataFrame({
                    "Analysis": [f"#{i+1}" for i in range(len(scores))],
                    "Score (%)": scores,
                })
                st.bar_chart(chart_data.set_index("Analysis"))

        elif response.status_code == 401:
            st.error("Session expired. Please login again.")
        else:
            st.error(f"Failed to load history: {response.status_code}")

    except requests.exceptions.ConnectionError:
        st.error(f"Cannot reach API at {API_BASE}.")
    except Exception as e:
        st.error(f"Error: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE — Agent Dashboard  (AGENT only)
# ══════════════════════════════════════════════════════════════════════════════

elif page == "Agent Dashboard":

    if st.session_state.get("user_role") != "AGENT":
        st.error("Access denied. Agent role required.")
        st.stop()

    st.markdown("# Agent Dashboard")
    st.markdown('<p style="color:#64748B;margin-top:-12px">Full visibility across all users and resumes.</p>', unsafe_allow_html=True)
    st.markdown("---")

    col_refresh, _ = st.columns([1, 5])
    with col_refresh:
        if st.button("↺ Refresh"):
            st.rerun()

    agent_tab1, agent_tab2, agent_tab3 = st.tabs(["  All Users  ", "  All Resumes  ", "  All Analyses  "])

    # ── All Users ──
    with agent_tab1:
        st.markdown('<div class="section-head">Registered Users</div>', unsafe_allow_html=True)
        try:
            resp = requests.get(API_BASE + "/agent/users", headers=auth_headers(), timeout=10)
            if resp.status_code == 200:
                users = resp.json()
                if users:
                    rows = [
                        {
                            "ID":       u["id"],
                            "Name":     u["name"],
                            "Email":    u["email"],
                            "Role":     u["role"],
                            "Verified": "✅" if u["is_verified"] else "❌",
                            "Joined":   (u.get("created_at") or "")[:10],
                        }
                        for u in users
                    ]
                    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

                    m1, m2 = st.columns(2)
                    with m1:
                        st.markdown(
                            f'<div class="metric-box">'
                            f'<div class="metric-label">Total Users</div>'
                            f'<div class="metric-value">{len(users)}</div>'
                            f'</div>', unsafe_allow_html=True
                        )
                    with m2:
                        verified = sum(1 for u in users if u["is_verified"])
                        st.markdown(
                            f'<div class="metric-box">'
                            f'<div class="metric-label">Verified</div>'
                            f'<div class="metric-value" style="color:#22C55E">{verified}</div>'
                            f'</div>', unsafe_allow_html=True
                        )
                else:
                    st.info("No users found.")
            else:
                st.error(f"Error {resp.status_code}: {resp.json().get('detail', '')}")
        except Exception as e:
            st.error(f"Error: {e}")

    # ── All Resumes ──
    with agent_tab2:
        st.markdown('<div class="section-head">All Uploaded Resumes</div>', unsafe_allow_html=True)

        def _clear_role_search():
            st.session_state["agent_role_search"] = ""

        search_col, clear_col = st.columns([4, 1])
        with search_col:
            role_query = st.text_input(
                "Search by predicted role (e.g. Teacher, Data Analyst)",
                key="agent_role_search",
                placeholder="Type a role and press Enter…",
            )
        with clear_col:
            st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
            st.button("✕ Clear", key="clear_role_search", on_click=_clear_role_search)

        try:
            if role_query.strip():
                # ── Search mode: only resumes whose predicted role matches ──
                resp = requests.get(
                    API_BASE + "/agent/search-role",
                    params={"role": role_query.strip()},
                    headers=auth_headers(),
                    timeout=10,
                )
            else:
                # ── Default: show every resume any user has uploaded ──
                resp = requests.get(
                    API_BASE + "/agent/resumes",
                    headers=auth_headers(),
                    timeout=10,
                )

            if resp.status_code == 200:
                resumes = resp.json()

                if role_query.strip():
                    st.caption(f"🔎 {len(resumes)} resume(s) matched role “{role_query.strip()}”")
                else:
                    st.caption(f"📂 {len(resumes)} resume(s) total")

                if resumes:
                    m1, m2 = st.columns(2)
                    with m1:
                        st.markdown(
                            f'<div class="metric-box" style="max-width:220px">'
                            f'<div class="metric-label">Showing</div>'
                            f'<div class="metric-value">{len(resumes)}</div>'
                            f'</div>', unsafe_allow_html=True
                        )

                    st.markdown("<br>", unsafe_allow_html=True)

                    for idx, r in enumerate(resumes):
                        ats   = r.get("ats_score")
                        match = r.get("role_match_score")
                        ats_disp   = f"{round(ats)}%"   if ats   is not None else "—"
                        match_disp = f"{round(match)}%" if match is not None else "—"
                        ats_cls    = score_class(ats) if ats is not None else "poor"

                        # Unique suffix per row — guards against duplicate resume_id
                        # values being returned in the same list from the API.
                        row_key = f"{r.get('resume_id', 'na')}_{idx}"

                        with st.container():
                            c1, c2, c3, c4, c5 = st.columns([2.2, 1.6, 1, 1, 1.2])
                            with c1:
                                st.markdown(
                                    f'<div style="font-weight:600;color:#F1F5F9">{r["file_name"]}</div>'
                                    f'<div style="font-size:12px;color:#64748B">Resume ID {r["resume_id"]} · User {r.get("user_id","—")} · {r.get("uploaded_at","")[:16]}</div>',
                                    unsafe_allow_html=True
                                )
                            with c2:
                                st.markdown(
                                    f'<div style="color:#818CF8;font-weight:600">{r.get("predicted_role") or "—"}</div>',
                                    unsafe_allow_html=True
                                )
                            with c3:
                                st.markdown(
                                    f'<div style="text-align:center">{pill(ats_disp, ats_cls)}</div>',
                                    unsafe_allow_html=True
                                )
                            with c4:
                                st.markdown(
                                    f'<div style="text-align:center;color:#CBD5E1">{match_disp}</div>',
                                    unsafe_allow_html=True
                                )
                            with c5:
                                dl_key = f"dl_{row_key}"
                                if st.button("⬇ Download", key=dl_key):
                                    try:
                                        file_resp = requests.get(
                                            f"{API_BASE}/agent/download/{r['resume_id']}",
                                            headers=auth_headers(),
                                            timeout=20,
                                        )
                                        if file_resp.status_code == 200:
                                            st.session_state[f"file_bytes_{row_key}"] = file_resp.content
                                        else:
                                            st.error(f"Download failed: {file_resp.status_code}")
                                    except Exception as e:
                                        st.error(f"Error: {e}")

                                # Once fetched, show the real download button (works for
                                # pdf/doc/docx/png/jpg/etc — raw bytes, browser handles it)
                                if st.session_state.get(f"file_bytes_{row_key}"):
                                    st.download_button(
                                        "Save file",
                                        data=st.session_state[f"file_bytes_{row_key}"],
                                        file_name=r["file_name"],
                                        key=f"save_{row_key}",
                                    )
                        st.markdown('<hr style="border-color:#1E2A3A;margin:6px 0">', unsafe_allow_html=True)
                else:
                    st.info("No resumes match." if role_query.strip() else "No resumes uploaded yet.")
            else:
                st.error(f"Error {resp.status_code}: {resp.json().get('detail', '')}")
        except Exception as e:
            st.error(f"Error: {e}")

    # ── All Analyses ──
    with agent_tab3:
        st.markdown('<div class="section-head">All Analysis Results</div>', unsafe_allow_html=True)
        try:
            resp = requests.get(API_BASE + "/agent/analysis-history", headers=auth_headers(), timeout=10)

            if resp.status_code == 200:
                analyses = resp.json()
                st.caption(f"📊 {len(analyses)} analysis record(s) total")

                if analyses:
                    scores = [round(a.get("score") or 0) for a in analyses]

                    m1, m2, m3 = st.columns(3)
                    with m1:
                        st.markdown(
                            f'<div class="metric-box">'
                            f'<div class="metric-label">Total Analyses</div>'
                            f'<div class="metric-value">{len(analyses)}</div>'
                            f'</div>', unsafe_allow_html=True
                        )
                    with m2:
                        avg = round(sum(scores) / len(scores)) if scores else 0
                        st.markdown(
                            f'<div class="metric-box">'
                            f'<div class="metric-label">Average Role Match</div>'
                            f'<div class="metric-value" style="color:{score_color(avg)}">{avg}%</div>'
                            f'</div>', unsafe_allow_html=True
                        )
                    with m3:
                        best = max(scores) if scores else 0
                        st.markdown(
                            f'<div class="metric-box">'
                            f'<div class="metric-label">Best Role Match</div>'
                            f'<div class="metric-value" style="color:{score_color(best)}">{best}%</div>'
                            f'</div>', unsafe_allow_html=True
                        )

                    st.markdown("<br>", unsafe_allow_html=True)

                    rows = []
                    for a in reversed(analyses):
                        sc = round(a.get("score") or 0)
                        rows.append({
                            "Analysis ID":    a.get("id"),
                            "Resume ID":      a.get("resume_id"),
                            "Role":           a.get("role"),
                            "Role Match":     f"{sc}%",
                            "ATS Score":      f"{round(a.get('ats_score') or 0)}%",
                            "ATS Status":     a.get("ats_status") or "—",
                            "Missing Skills": a.get("missing_skills") or "—",
                            "Strengths":      a.get("strengths") or "—",
                            "Date":           (a.get("created_at") or "")[:10] or "—",
                        })

                    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

                    st.markdown("### Role Match Trend (all users)")
                    chart_data = pd.DataFrame({
                        "Analysis": [f"#{i+1}" for i in range(len(scores))],
                        "Score (%)": scores,
                    })
                    st.bar_chart(chart_data.set_index("Analysis"))

                    st.markdown("### Recommendations by Analysis")
                    for a in reversed(analyses):
                        reco = a.get("recommendations") or "No recommendations generated."
                        with st.expander(f"Analysis #{a.get('id')} · Resume {a.get('resume_id')} · {a.get('role') or '—'}"):
                            st.markdown(f'<div class="reco-box">{reco}</div>', unsafe_allow_html=True)
                else:
                    st.markdown("""
                    <div style="text-align:center;padding:60px;color:#334155">
                      <div style="font-size:40px">📭</div>
                      <div style="margin-top:12px;font-size:15px;color:#475569">
                        No analyses recorded yet.
                      </div>
                    </div>""", unsafe_allow_html=True)
            elif resp.status_code == 401:
                st.error("Session expired. Please login again.")
            else:
                try:
                    detail = resp.json().get("detail", "")
                except Exception:
                    detail = resp.text
                st.error(f"Error {resp.status_code}: {detail}")
        except requests.exceptions.ConnectionError:
            st.error(f"Cannot reach API at {API_BASE}.")
        except Exception as e:
            st.error(f"Error: {e}")