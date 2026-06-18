from datetime import datetime, timezone
import re
import io
import zipfile
import pdfplumber
import pytesseract
pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)
from datetime import datetime
import pytz
from PIL import Image
from lxml import etree
from fastapi import FastAPI, HTTPException, Depends, File, UploadFile
import os
from sqlalchemy import (
    create_engine, Column, Integer, String,
    ForeignKey, Text, DateTime, Float
)
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from recomendation_service import (
    get_ai_recommendations,
    analyze_resume_ai
)

def extract_text_from_image(file_path: str) -> str:
    try:
        img = Image.open(file_path)

        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")

        custom_config = r'--oem 3 --psm 3'
        return pytesseract.image_to_string(img, config=custom_config)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image OCR failed: {str(e)}")

# ---------------- DATABASE ---------------------------------

DATABASE_URL = "mysql+pymysql://root:1234@localhost/resume_ai_db"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ---------------- TABLES ----------------
IST = pytz.timezone("Asia/Kolkata")
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100))
    email = Column(String(255), unique=True, index=True)

    created_at = Column(
        DateTime,
        default=lambda: datetime.now(IST)
    )

class Resume(Base):
    __tablename__ = "resumes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    file_name = Column(String(255))
    extracted_text = Column(Text)
    uploaded_at = Column(DateTime, default=lambda: datetime.now(IST))


class AnalysisResult(Base):
    __tablename__ = "analysis_results"

    id = Column(Integer, primary_key=True, index=True)
    resume_id = Column(Integer, ForeignKey("resumes.id"))
    role = Column(String(100))
    score = Column(Float)
    missing_skills = Column(Text)
    strengths = Column(Text)
    recommendations = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(IST))


Base.metadata.create_all(bind=engine)

app = FastAPI()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ================================================================
# TEXT EXTRACTION
# ================================================================

# Word processing XML namespace
W_NS = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}


def extract_text_from_pdf(file_path: str) -> str:
    """Extract text from PDF using pdfplumber."""
    extracted = ""
    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    extracted += page_text + "\n"
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF extraction failed: {str(e)}")
    return extracted


def _pull_w_t_nodes(xml_bytes: bytes) -> list[str]:
    """
    Parse XML and return all <w:t> text values.
    This catches paragraphs, text boxes, shapes, headers — everything.
    """
    try:
        tree = etree.fromstring(xml_bytes)
        return [t.text for t in tree.findall('.//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t') if t.text]
    except Exception:
        return []


def extract_text_from_docx_bytes(data: bytes) -> str:
    """
    Extract ALL text from a DOCX file (given as raw bytes) by reading
    directly from the ZIP archive XML.

    Covers:
      - Normal paragraphs
      - Text boxes and drawing shapes (wps:txbx, mc:AlternateContent)
      - Table cells
      - Headers and footers
      - SmartArt fallback text

    python-docx's .paragraphs only covers normal paragraphs and misses
    everything inside text boxes, which most resume templates use heavily.
    """
    texts = []

    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            names = z.namelist()

            # Main document body
            if 'word/document.xml' in names:
                texts.extend(_pull_w_t_nodes(z.read('word/document.xml')))

            # Headers and footers
            for name in names:
                if re.match(r'word/(header|footer)\d+\.xml', name):
                    texts.extend(_pull_w_t_nodes(z.read(name)))

    except zipfile.BadZipFile:
        raise HTTPException(
            status_code=400,
            detail="The DOCX file appears to be corrupted or is not a valid DOCX file."
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DOCX extraction failed: {str(e)}")

    result = " ".join(texts)

    # Normalise whitespace
    result = re.sub(r'[ \t]+', ' ', result)
    result = re.sub(r'\n{3,}', '\n\n', result)
    return result.strip()


def extract_text_from_docx(file_path: str) -> str:
    """Read file from disk and delegate to byte-based extractor."""
    with open(file_path, "rb") as f:
        data = f.read()
    return extract_text_from_docx_bytes(data)


def extract_text_from_doc(file_path: str) -> str:
    """
    Extract text from legacy .doc files.
    Tries antiword first; falls back to raw printable-byte extraction.
    """
    try:
        import subprocess
        result = subprocess.run(
            ["antiword", file_path],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout
    except FileNotFoundError:
        pass  # antiword not installed — fall through to raw extraction
    except Exception:
        pass

    # Raw byte fallback: pull ASCII printable strings (length >= 4)
    try:
        with open(file_path, "rb") as f:
            raw = f.read()
        strings = re.findall(rb'[\x20-\x7E]{4,}', raw)
        return "\n".join(s.decode("ascii", errors="ignore") for s in strings)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DOC extraction failed: {str(e)}")


def extract_text_from_image(file_path: str) -> str:
    """
    Extract text from image files (PNG, JPG, JPEG, WEBP, BMP)
    using Tesseract OCR.
    """
    try:
        img = Image.open(file_path)

        # Tesseract works best on RGB or grayscale
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")

        # oem 3 = LSTM engine, psm 3 = fully automatic page segmentation
        custom_config = r'--oem 3 --psm 3'
        return pytesseract.image_to_string(img, config=custom_config)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image OCR failed: {str(e)}")


def extract_text(file_path: str, extension: str) -> str:
    """Route to the correct extractor based on file extension."""
    if extension == ".pdf":
        return extract_text_from_pdf(file_path)
    elif extension == ".docx":
        return extract_text_from_docx(file_path)
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

    # 1. Skills Score (30)
    total_skills = len(found_skills) + len(missing_skills)
    if total_skills:
        score += round((len(found_skills) / total_skills) * 30)

    # 2. Resume Sections (15)
    sections = ["summary", "profile", "skills", "education",
                "experience", "projects", "certifications"]
    section_count = sum(1 for s in sections if s in text_lower)
    score += round((section_count / len(sections)) * 15)

    # 3. Contact Information (10)
    if re.search(r'[\w\.-]+@[\w\.-]+\.\w+', resume_text):
        score += 4
    if re.search(r'[\+\d][\d\s\-\(\)]{8,}', resume_text):
        score += 4
    if "linkedin.com" in text_lower:
        score += 2

    # 4. Projects / Experience (15)
    project_keywords = [
        "project", "projects", "internship", "experience", "developed",
        "implemented", "created", "built", "designed", "dashboard", "api", "application"
    ]
    project_hits = sum(1 for w in project_keywords if w in text_lower)
    if project_hits >= 6:   score += 15
    elif project_hits >= 4: score += 12
    elif project_hits >= 2: score += 8
    elif project_hits >= 1: score += 4

    # 5. Education (5)
    edu_keywords = ["bca", "bsc", "btech", "mca", "msc", "degree", "university", "college"]
    if any(k in text_lower for k in edu_keywords):
        score += 5

    # 6. Achievements (10)
    achievement_words = ["improved", "increased", "reduced", "optimized",
                         "achieved", "boosted", "led", "managed"]
    a_hits = sum(1 for w in achievement_words if w in text_lower)
    p_hits = len(re.findall(r'\d+%', resume_text))
    total_a = a_hits + p_hits
    if total_a >= 5:   score += 10
    elif total_a >= 3: score += 7
    elif total_a >= 1: score += 4

    # 7. Resume Length (5)
    wc = len(resume_text.split())
    if 300 <= wc <= 800:   score += 5
    elif 200 <= wc <= 1000: score += 3
    else:                   score += 1

    # 8. Formatting Quality (10)
    lines = resume_text.splitlines()
    if len(lines) >= 15:          score += 3
    if ":" in resume_text:        score += 2
    if "-" in resume_text or "•" in resume_text: score += 3
    if section_count >= 5:        score += 2

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

    ai_result = analyze_resume_ai(resume.extracted_text)

    role = (ai_result.get("predicted_role") or "").strip()
    found_skills   = [s for s in ai_result.get("found_skills",   []) if s]
    missing_skills = [s for s in ai_result.get("missing_skills", []) if s]

    if not role or role.lower() == "unknown":
        return {
            "predicted_role": "Unknown",
            "ats_score": 0,
            "ats_status": "Not Available",
            "role_match_score": 0,
            "found_skills": [],
            "missing_skills": [],
            "strengths": [],
            "improvements": ["Could not confidently identify a role for this resume"],
            "recommendations": "",
            "summary": "No role could be confidently predicted from this resume."
        }

    total_skills     = len(found_skills) + len(missing_skills)
    role_match_score = round((len(found_skills) / total_skills) * 100, 2) if total_skills else 0.0
    ats_score, ats_status = calculate_ats_score(resume.extracted_text, found_skills, missing_skills)

    strengths = []
    if found_skills:                        strengths.append(f"Matched {len(found_skills)} relevant skills")
    if "%" in resume.extracted_text:        strengths.append("Contains quantified achievements")
    if len(resume.extracted_text) > 800:    strengths.append("Detailed resume content")

    improvements = []
    if missing_skills:
        improvements.append(f"Add missing skills: {', '.join(missing_skills)}")
    if "%" not in resume.extracted_text:
        improvements.append("Add measurable achievements using numbers and percentages")
    if len(resume.extracted_text) < 500:
        improvements.append("Add more project and work experience details")

    recommendations = get_ai_recommendations(
        role, role_match_score, found_skills, missing_skills
    )

    summary = (
        f"This resume matches {role_match_score}% of the required {role} skills. "
        f"ATS score is {ats_score}%. The resume demonstrates {len(found_skills)} matching skills "
        f"and {len(missing_skills)} missing skills."
    )

    return {
        "predicted_role":  role,
        "ats_score":       ats_score,
        "ats_status":      ats_status,
        "role_match_score": role_match_score,
        "found_skills":    found_skills,
        "missing_skills":  missing_skills,
        "strengths":       strengths,
        "improvements":    improvements,
        "recommendations": recommendations,
        "summary":         summary,
    }


# ================================================================
# ROUTES
# ================================================================

@app.get("/")
def first_start():
    return {"message": "Hi there, Welcome to Resume Analyzer"}


@app.post("/upload-resume")
async def upload_resume(
    name: str,
    email: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    ALLOWED = [".pdf", ".doc", ".docx", ".png", ".jpg", ".jpeg", ".webp", ".bmp"]
    extension = os.path.splitext(file.filename)[1].lower()

    if extension not in ALLOWED:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{extension}'. Allowed: {', '.join(ALLOWED)}"
        )

   # Save to disk
    file_path = os.path.join(UPLOAD_DIR, os.path.basename(file.filename))
    content = await file.read()

# File size validation (5 MB)
    MAX_FILE_SIZE = 5 * 1024 * 1024

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
        status_code=400,
        detail="File size exceeds 5MB limit"
    )

    with open(file_path, "wb") as buffer:
        buffer.write(content)

    # Extract text — for DOCX pass raw bytes directly (avoids re-read issues)
    if extension == ".docx":
        extracted_text = extract_text_from_docx_bytes(content)
    else:
        extracted_text = extract_text(file_path, extension)

    print("========== EXTRACTED TEXT ==========")
    print(f"Length: {len(extracted_text)} chars")
    print(extracted_text[:3000])
    print("====================================")

    if not extracted_text.strip():
        raise HTTPException(
            status_code=400,
            detail=(
                "Could not extract any text from the file. "
                "For DOCX: ensure it's a real Word document, not renamed. "
                "For images: ensure text is clearly visible and not handwritten. "
                "Try converting to PDF for best results."
            )
        )

    # Upsert user
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(name=name, email=email)
        db.add(user)
        db.commit()
        db.refresh(user)

    # Save resume record
    resume = Resume(user_id=user.id, file_name=file.filename, extracted_text=extracted_text)
    db.add(resume)
    db.commit()
    db.refresh(resume)

    # Run analysis
    result = run_analysis(resume)

    # Save analysis result
    analysis = AnalysisResult(
        resume_id=resume.id,
        role=result["predicted_role"],
        score=result["role_match_score"],
        missing_skills=", ".join(result["missing_skills"]),
        strengths=", ".join(result["strengths"]),
        recommendations=result["recommendations"],
    )
    db.add(analysis)
    db.commit()

    return {"resume_id": resume.id, "filename": file.filename, **result}


@app.get("/analysis-history")
def get_analysis_history(db: Session = Depends(get_db)):
    results = db.query(AnalysisResult).all()
    return [
        {
            "id": r.id,
            "resume_id": r.resume_id,
            "role": r.role,
            "score": r.score,
            "missing_skills": r.missing_skills,
            "strengths": r.strengths,
            "recommendations": r.recommendations,
            "created_at": str(r.created_at),
        }
        for r in results
    ]


@app.get("/resume/{resume_id}")
def get_resume(resume_id: int, db: Session = Depends(get_db)):
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    return {
        "id": resume.id,
        "file_name": resume.file_name,
        "uploaded_at": resume.uploaded_at,
        "extracted_text": resume.extracted_text,
    }


@app.delete("/resume/{resume_id}")
def delete_resume(resume_id: int, db: Session = Depends(get_db)):
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    db.delete(resume)
    db.commit()
    return {"message": "Resume deleted successfully"}