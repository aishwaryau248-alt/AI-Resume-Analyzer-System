import io
import os
import re
import zipfile
from datetime import datetime
from fastapi.responses import FileResponse
import pdfplumber
import pytz
import pytesseract
from PIL import Image
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from lxml import etree
from sqlalchemy.orm import Session

from auth import (
    AnalysisResult,
    Resume,
    User,
    get_current_user,
    get_db,
    hash_password,
    require_agent,
    router as auth_router,
)
from recomendation_service import analyze_resume_ai, get_ai_recommendations

# ── Windows: Tesseract binary path ───────────────────────────────────────────
pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)

IST = pytz.timezone("Asia/Kolkata")

app = FastAPI()
app.include_router(auth_router)   # mounts /register /login /verify-email /me etc.

UPLOAD_DIR   = "uploads"
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ================================================================
# TEXT EXTRACTION
# ================================================================

def extract_text_from_pdf(file_path: str) -> str:
    extracted = ""
    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    extracted += page_text + "\n"
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF extraction failed: {e}")
    return extracted


def _pull_w_t_nodes(xml_bytes: bytes) -> list:
    try:
        tree = etree.fromstring(xml_bytes)
        W    = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
        return [t.text for t in tree.iter(f"{{{W}}}t") if t.text]
    except Exception:
        return []


def extract_text_from_docx_bytes(data: bytes) -> str:
    texts = []
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            names = z.namelist()
            if "word/document.xml" in names:
                texts.extend(_pull_w_t_nodes(z.read("word/document.xml")))
            for name in names:
                if re.match(r"word/(header|footer)\d+\.xml", name):
                    texts.extend(_pull_w_t_nodes(z.read(name)))
    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="Corrupted or invalid DOCX file.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DOCX extraction failed: {e}")

    result = " ".join(texts)
    result = re.sub(r"[ \t]+", " ", result)
    result = re.sub(r"\n{3,}", "\n\n", result)
    return result.strip()


def extract_text_from_doc(file_path: str) -> str:
    try:
        import subprocess
        res = subprocess.run(
            ["antiword", file_path], capture_output=True, text=True, timeout=30
        )
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout
    except (FileNotFoundError, Exception):
        pass

    try:
        with open(file_path, "rb") as f:
            raw = f.read()
        strings = re.findall(rb"[\x20-\x7E]{4,}", raw)
        return "\n".join(s.decode("ascii", errors="ignore") for s in strings)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DOC extraction failed: {e}")


def extract_text_from_image(file_path: str) -> str:
    try:
        img = Image.open(file_path)
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        return pytesseract.image_to_string(img, config=r"--oem 3 --psm 3")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image OCR failed: {e}")


def extract_text(file_path: str, extension: str) -> str:
    if extension == ".pdf":
        return extract_text_from_pdf(file_path)
    elif extension == ".docx":
        with open(file_path, "rb") as f:
            return extract_text_from_docx_bytes(f.read())
    elif extension == ".doc":
        return extract_text_from_doc(file_path)
    elif extension in (".png", ".jpg", ".jpeg", ".webp", ".bmp"):
        return extract_text_from_image(file_path)
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {extension}")


# ================================================================
# ATS SCORE
# ================================================================

def calculate_ats_score(resume_text: str, found_skills: list, missing_skills: list):
    text_lower = resume_text.lower()
    score = 0

    total_skills = len(found_skills) + len(missing_skills)
    if total_skills:
        score += round((len(found_skills) / total_skills) * 30)

    sections = ["summary", "profile", "skills", "education",
                "experience", "projects", "certifications"]
    section_count = sum(1 for s in sections if s in text_lower)
    score += round((section_count / len(sections)) * 15)

    if re.search(r"[\w\.-]+@[\w\.-]+\.\w+", resume_text): score += 4
    if re.search(r"[\+\d][\d\s\-\(\)]{8,}", resume_text):  score += 4
    if "linkedin.com" in text_lower:                        score += 2

    project_keywords = [
        "project", "projects", "internship", "experience", "developed",
        "implemented", "created", "built", "designed",
        "dashboard", "api", "application"
    ]
    project_hits = sum(1 for w in project_keywords if w in text_lower)
    if project_hits >= 6:   score += 15
    elif project_hits >= 4: score += 12
    elif project_hits >= 2: score += 8
    elif project_hits >= 1: score += 4

    edu_kw = ["bca", "bsc", "btech", "mca", "msc", "degree", "university", "college"]
    if any(k in text_lower for k in edu_kw):
        score += 5

    ach_words = ["improved", "increased", "reduced", "optimized",
                 "achieved", "boosted", "led", "managed"]
    a_hits  = sum(1 for w in ach_words if w in text_lower)
    p_hits  = len(re.findall(r"\d+%", resume_text))
    total_a = a_hits + p_hits
    if total_a >= 5:   score += 10
    elif total_a >= 3: score += 7
    elif total_a >= 1: score += 4

    wc = len(resume_text.split())
    if   300 <= wc <= 800:  score += 5
    elif 200 <= wc <= 1000: score += 3
    else:                   score += 1

    lines = resume_text.splitlines()
    if len(lines) >= 15:                         score += 3
    if ":" in resume_text:                       score += 2
    if "-" in resume_text or "•" in resume_text: score += 3
    if section_count >= 5:                       score += 2

    score = min(score, 100)

    if score >= 85:   status = "Excellent"
    elif score >= 70: status = "Good"
    elif score >= 50: status = "Average"
    else:             status = "Poor"

    return score, status


# ================================================================
# ANALYSIS
# ================================================================

def run_analysis(resume: Resume) -> dict:
    try:
        ai_result = analyze_resume_ai(resume.extracted_text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI analysis failed: {e}")

    role           = (ai_result.get("predicted_role") or "").strip()
    found_skills   = [s for s in ai_result.get("found_skills",   []) if s]
    missing_skills = [s for s in ai_result.get("missing_skills", []) if s]

    if not role or role.lower() == "unknown":
        return {
            "predicted_role":   "Unknown",
            "ats_score":        0,
            "ats_status":       "Not Available",
            "role_match_score": 0,
            "found_skills":     [],
            "missing_skills":   [],
            "strengths":        [],
            "improvements":     ["Could not confidently identify a role for this resume"],
            "recommendations":  "",
            "summary":          "No role could be confidently predicted from this resume.",
        }

    total_skills     = len(found_skills) + len(missing_skills)
    role_match_score = round((len(found_skills) / total_skills) * 100, 2) if total_skills else 0.0
    ats_score, ats_status = calculate_ats_score(resume.extracted_text, found_skills, missing_skills)

    strengths    = []
    improvements = []

    if found_skills:
        strengths.append(f"Matched {len(found_skills)} relevant skills")
    if "%" in resume.extracted_text:
        strengths.append("Contains quantified achievements")
    if len(resume.extracted_text) > 800:
        strengths.append("Detailed resume content")

    if missing_skills:
        improvements.append(f"Add missing skills: {', '.join(missing_skills)}")
    if "%" not in resume.extracted_text:
        improvements.append("Add measurable achievements using numbers and percentages")
    if len(resume.extracted_text) < 500:
        improvements.append("Add more project and work experience details")

    try:
        recommendations = get_ai_recommendations(role, role_match_score, found_skills, missing_skills)
    except Exception as e:
        recommendations = f"Recommendations unavailable: {e}"

    summary = (
        f"This resume matches {role_match_score}% of the required {role} skills. "
        f"ATS score is {ats_score}%. "
        f"The resume demonstrates {len(found_skills)} matching skills "
        f"and {len(missing_skills)} missing skills."
    )

    return {
        "predicted_role":   role,
        "ats_score":        ats_score,
        "ats_status":       ats_status,
        "role_match_score": role_match_score,
        "found_skills":     found_skills,
        "missing_skills":   missing_skills,
        "strengths":        strengths,
        "improvements":     improvements,
        "recommendations":  recommendations,
        "summary":          summary,
    }


# ================================================================
# ROUTES
# ================================================================

@app.get("/")
def first_start():
    return {"message": "Hi there, Welcome to Resume Analyzer"}


# ── USER: Upload resume (requires login) ─────────────────────────────────────

@app.post("/upload-resume")
async def upload_resume(
    file: UploadFile          = File(...),
    current_user: User        = Depends(get_current_user),   # must be logged in
    db: Session               = Depends(get_db),
):
    ALLOWED   = [".pdf", ".doc", ".docx", ".png", ".jpg", ".jpeg", ".webp", ".bmp"]
    extension = os.path.splitext(file.filename)[1].lower()

    if extension not in ALLOWED:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{extension}'. Allowed: {', '.join(ALLOWED)}"
        )

    content = await file.read()

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File size exceeds the 5 MB limit.")

    file_path = os.path.join(UPLOAD_DIR, os.path.basename(file.filename))
    with open(file_path, "wb") as buffer:
        buffer.write(content)

    extracted_text = (
        extract_text_from_docx_bytes(content)
        if extension == ".docx"
        else extract_text(file_path, extension)
    )

    print("========== EXTRACTED TEXT ==========")
    print(f"Length : {len(extracted_text)} chars")
    print(extracted_text[:3000])
    print("====================================")

    if not extracted_text.strip():
        raise HTTPException(
            status_code=400,
            detail=(
                "Could not extract any text from the file. "
                "For images: ensure text is clearly visible. "
                "Try converting to PDF for best results."
            )
        )

    # Save resume — linked to the authenticated user
    resume = Resume(
        user_id        = current_user.id,
        file_name      = file.filename,
        file_path      = file_path,
        extracted_text = extracted_text,
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)

    result = run_analysis(resume)

    analysis = AnalysisResult(
        resume_id      = resume.id,
        role           = result["predicted_role"],
        score          = result["role_match_score"],
        ats_score      = result["ats_score"],
        ats_status     = result["ats_status"],
        missing_skills = ", ".join(result["missing_skills"]),
        strengths      = ", ".join(result["strengths"]),
        recommendations= result["recommendations"],
    )
    db.add(analysis)
    db.commit()

    return {"resume_id": resume.id, "filename": file.filename, **result}


# ── USER: Own analysis history ────────────────────────────────────────────────

@app.get("/my-history")
def my_history(
    current_user: User = Depends(get_current_user),
    db: Session        = Depends(get_db),
):
    """Returns only the analyses for resumes belonging to the logged-in user."""
    resumes = db.query(Resume).filter(Resume.user_id == current_user.id).all()
    resume_ids = {r.id for r in resumes}

    results = (
        db.query(AnalysisResult)
        .filter(AnalysisResult.resume_id.in_(resume_ids))
        .all()
    )
    return [
        {
            "id":             r.id,
            "resume_id":      r.resume_id,
            "role":           r.role,
            "score":          r.score,
            "ats_score":      r.ats_score,
            "ats_status":     r.ats_status,
            "missing_skills": r.missing_skills,
            "strengths":      r.strengths,
            "recommendations":r.recommendations,
            "created_at":     str(r.created_at),
        }
        for r in results
    ]


# ── USER: Own uploaded resumes ────────────────────────────────────────────────

@app.get("/my-resumes")
def my_resumes(
    current_user: User = Depends(get_current_user),
    db: Session        = Depends(get_db),
):
    """Returns only resumes uploaded by the logged-in user."""
    resumes = db.query(Resume).filter(Resume.user_id == current_user.id).all()
    return [
        {
            "id":          r.id,
            "file_name":   r.file_name,
            "uploaded_at": str(r.uploaded_at),
        }
        for r in resumes
    ]


# ── USER: Get own resume by ID ────────────────────────────────────────────────

@app.get("/resume/{resume_id}")
def get_resume(
    resume_id:    int,
    current_user: User    = Depends(get_current_user),
    db:           Session = Depends(get_db),
):
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    # USER can only view their own; AGENT can view any
    if current_user.role != "AGENT" and resume.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    return {
        "id":             resume.id,
        "file_name":      resume.file_name,
        "uploaded_at":    str(resume.uploaded_at),
        "extracted_text": resume.extracted_text,
    }


# ── USER: Delete own resume ───────────────────────────────────────────────────

@app.delete("/resume/{resume_id}")
def delete_resume(
    resume_id:    int,
    current_user: User    = Depends(get_current_user),
    db:           Session = Depends(get_db),
):
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    if current_user.role != "AGENT" and resume.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    db.delete(resume)
    db.commit()
    return {"message": "Resume deleted successfully"}


# ================================================================
# AGENT-ONLY ROUTES
# ================================================================

@app.get("/agent/users")
def agent_all_users(
    _:  User    = Depends(require_agent),
    db: Session = Depends(get_db),
):
    """AGENT: view all registered users."""
    users = db.query(User).all()
    return [
        {
            "id":          u.id,
            "name":        u.name,
            "email":       u.email,
            "role":        u.role,
            "is_verified": u.is_verified,
            "created_at":  str(u.created_at),
        }
        for u in users
    ]


@app.get("/agent/resumes")
def agent_all_resumes(
    agent: User = Depends(require_agent),
    db: Session = Depends(get_db)
):
    """AGENT: view EVERY uploaded resume — with predicted role, ATS score and
    role-match score where available. Uses an OUTER JOIN so a resume is never
    hidden just because it hasn't been analysed yet (e.g. analysis failed)."""

    rows = db.query(
        Resume,
        AnalysisResult
    ).outerjoin(
        AnalysisResult,
        Resume.id == AnalysisResult.resume_id
    ).order_by(Resume.uploaded_at.desc()).all()

    data = []
    for resume, analysis in rows:
        data.append({
            "resume_id":        resume.id,
            "user_id":          resume.user_id,
            "file_name":        resume.file_name,
            "predicted_role":   analysis.role if analysis else "Not analyzed",
            "ats_score":        analysis.ats_score if analysis else None,
            "ats_status":       analysis.ats_status if analysis else None,
            "role_match_score": analysis.score if analysis else None,
            "missing_skills":   analysis.missing_skills if analysis else None,
            "uploaded_at":      str(resume.uploaded_at),
        })

    return data


@app.get("/agent/search-role")
def search_role(
    role: str,
    agent: User = Depends(require_agent),
    db: Session = Depends(get_db)
):
    """AGENT: search resumes by the AI's predicted role (e.g. 'teacher').
    Works for ANY source file type — PDF, DOC, DOCX, or image (PNG/JPG/etc),
    since role detection always runs on the OCR/extracted text regardless of
    the original format. Returns everything needed to view/download."""

    results = db.query(
        Resume,
        AnalysisResult
    ).join(
        AnalysisResult,
        Resume.id == AnalysisResult.resume_id
    ).filter(
        AnalysisResult.role.ilike(f"%{role}%")
    ).order_by(Resume.uploaded_at.desc()).all()

    data = []
    for resume, analysis in results:
        data.append({
            "resume_id":        resume.id,
            "user_id":          resume.user_id,
            "file_name":        resume.file_name,
            "predicted_role":   analysis.role,
            "ats_score":        analysis.ats_score,
            "ats_status":       analysis.ats_status,
            "role_match_score": analysis.score,
            "missing_skills":   analysis.missing_skills,
            "uploaded_at":      str(resume.uploaded_at),
        })

    return data


@app.get("/agent/analysis-history")
def agent_all_analysis(
    _:  User    = Depends(require_agent),
    db: Session = Depends(get_db),
):
    """AGENT: view all analysis results across all users."""
    results = db.query(AnalysisResult).all()
    return [
        {
            "id":             r.id,
            "resume_id":      r.resume_id,
            "role":           r.role,
            "score":          r.score,
            "ats_score":      r.ats_score,
            "ats_status":     r.ats_status,
            "missing_skills": r.missing_skills,
            "strengths":      r.strengths,
            "recommendations":r.recommendations,
            "created_at":     str(r.created_at),
        }
        for r in results
    ]


@app.get("/agent/download/{resume_id}")
def download_resume(
    resume_id: int,
    agent: User = Depends(require_agent),
    db: Session = Depends(get_db)
):
    """AGENT: download the ORIGINAL uploaded file for any resume — works for
    PDF, DOC, DOCX, and image formats (PNG/JPG/JPEG/WEBP/BMP) alike, since the
    raw bytes are stored as-is on disk regardless of file type."""

    resume = db.query(Resume).filter(
        Resume.id == resume_id
    ).first()

    if not resume:
        raise HTTPException(
            status_code=404,
            detail="Resume not found"
        )

    file_path = os.path.join(
        UPLOAD_DIR,
        os.path.basename(resume.file_name)
    )

    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=404,
            detail="Original file is missing from storage."
        )

    return FileResponse(
        file_path,
        filename=resume.file_name,
        media_type="application/octet-stream",
    )