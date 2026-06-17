from datetime import datetime, timezone
import re
import pdfplumber
from fastapi import FastAPI, HTTPException, Depends, File, UploadFile
import os
from sqlalchemy import (
    create_engine, Column, Integer, String,
    ForeignKey, Text, DateTime, Float, text
)
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from recomendation_service import (
    get_ai_recommendations,
    analyze_resume_ai
)

# ---------------- DATABASE ---------------------------------

DATABASE_URL = "mysql+pymysql://root:1234@localhost/resume_ai_db"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ---------------- TABLES ----------------

class Resume(Base):
    __tablename__ = "resumes"

    id = Column(Integer, primary_key=True, index=True)
    file_name = Column(String(255))
    extracted_text = Column(Text)
    uploaded_at = Column(DateTime, default=datetime.now(timezone.utc))


class AnalysisResult(Base):
    __tablename__ = "analysis_results"

    id = Column(Integer, primary_key=True, index=True)
    resume_id = Column(Integer, ForeignKey("resumes.id"))
    role = Column(String(100))
    score = Column(Float)
    missing_skills = Column(Text)
    strengths = Column(Text)
    recommendations = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


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


def calculate_ats_score(
    resume: Resume,
    found_skills: list,
    missing_skills: list,
) -> tuple[int, str]:

    resume_text = resume.extracted_text
    text_lower = resume_text.lower()

    # 1. SKILL MATCH (50 Points)
    total_skills = len(found_skills) + len(missing_skills)
    skill_ratio = (len(found_skills) / total_skills) if total_skills else 0
    skill_score = round(skill_ratio * 50)

    # 2. SECTION SCORE (15 Points)
    expected_sections = ["skills", "education", "projects", "experience", "certifications"]
    found_sections = sum(1 for section in expected_sections if section in text_lower)
    section_score = round((found_sections / len(expected_sections)) * 15)

    # 3. CONTACT INFORMATION (5 Points)
    contact_score = 0
    has_email = bool(re.search(r'[\w\.-]+@[\w\.-]+\.\w+', resume_text))
    has_phone = bool(re.search(r'[\+\d][\d\s\-\(\)]{8,}', resume_text))
    has_linkedin = "linkedin.com" in text_lower

    if has_email:
        contact_score += 2
    if has_phone:
        contact_score += 2
    if has_linkedin:
        contact_score += 1

    # 4. ACHIEVEMENTS (10 Points)
    achievement_patterns = re.findall(
        r'\d+\s*(%|x|years?|months?|\+)',
        resume_text,
        re.IGNORECASE
    )
    achievement_count = len(achievement_patterns)

    if achievement_count >= 5:
        achievement_score = 10
    elif achievement_count >= 3:
        achievement_score = 8
    elif achievement_count >= 1:
        achievement_score = 5
    else:
        achievement_score = 0

    # 5. RESUME LENGTH (10 Points)
    word_count = len(resume_text.split())

    if word_count >= 500:
        content_score = 10
    elif word_count >= 300:
        content_score = 8
    elif word_count >= 150:
        content_score = 5
    else:
        content_score = 2

    # 6. PROJECTS / EXPERIENCE (10 Points)
    project_keywords = [
        "project", "projects", "internship", "experience",
        "worked", "developed", "implemented"
    ]
    project_hits = sum(1 for keyword in project_keywords if keyword in text_lower)

    if project_hits >= 4:
        project_score = 10
    elif project_hits >= 2:
        project_score = 7
    elif project_hits >= 1:
        project_score = 4
    else:
        project_score = 0

    # FINAL SCORE
    ats_score = (
        skill_score + section_score + contact_score
        + achievement_score + content_score + project_score
    )
    ats_score = min(100, ats_score)

    if ats_score >= 85:
        ats_status = "Excellent"
    elif ats_score >= 70:
        ats_status = "Good"
    elif ats_score >= 50:
        ats_status = "Average"
    else:
        ats_status = "Poor"

    return ats_score, ats_status


def run_analysis(resume: Resume) -> dict:

    # ---------------------------
    # STEP 1: AI ROLE + SKILL DETECTION (Hugging Face)
    # ---------------------------

    ai_result = analyze_resume_ai(resume.extracted_text)

    role = (ai_result.get("predicted_role") or "").strip()
    found_skills = [s for s in ai_result.get("found_skills", []) if s]
    missing_skills = [s for s in ai_result.get("missing_skills", []) if s]

    # ---------------------------
    # STEP 2: NO ROLE FOUND
    # ---------------------------

    if not role or role.lower() == "unknown":
        return {
            "predicted_role": "Unknown",
            "ats_score": 0,
            "ats_status": "Not Available",
            "role_match_score": 0,
            "found_skills": [],
            "missing_skills": [],
            "strengths": [],
            "improvements": [
                "Could not confidently identify a role for this resume"
            ],
            "recommendations": "",
            "summary": "No role could be confidently predicted from this resume."
        }

    # ---------------------------
    # STEP 3: SCORE CALCULATION
    # ---------------------------

    total_skills = len(found_skills) + len(missing_skills)
    role_match_score = round((len(found_skills) / total_skills) * 100, 2) if total_skills else 0.0

    ats_score, ats_status = calculate_ats_score(resume, found_skills, missing_skills)

    # ---------------------------
    # STRENGTHS
    # ---------------------------

    strengths = []

    if found_skills:
        strengths.append(f"Matched {len(found_skills)} relevant skills")

    if "%" in resume.extracted_text:
        strengths.append("Contains quantified achievements")

    if len(resume.extracted_text) > 800:
        strengths.append("Detailed resume content")

    # ---------------------------
    # IMPROVEMENTS
    # ---------------------------

    improvements = []

    if missing_skills:
        improvements.append(f"Add missing skills: {', '.join(missing_skills)}")

    if "%" not in resume.extracted_text:
        improvements.append("Add measurable achievements using numbers and percentages")

    if len(resume.extracted_text) < 500:
        improvements.append("Add more project and work experience details")

    # ---------------------------
    # AI RECOMMENDATIONS
    # ---------------------------

    recommendations = get_ai_recommendations(
        role,
        role_match_score,
        found_skills,
        missing_skills
    )

    summary = (
        f"This resume matches "
        f"{role_match_score}% of the required "
        f"{role} skills. ATS score is "
        f"{ats_score}%. The resume demonstrates "
        f"{len(found_skills)} matching skills and "
        f"{len(missing_skills)} missing skills."
    )

    return {
        "predicted_role": role,
        "ats_score": ats_score,
        "ats_status": ats_status,
        "role_match_score": role_match_score,
        "found_skills": found_skills,
        "missing_skills": missing_skills,
        "strengths": strengths,
        "improvements": improvements,
        "recommendations": recommendations,
        "summary": summary,
    }


# ---------------- ROUTES ----------------

@app.get("/")
def first_start():
    return {"message": "Hi there, Welcome to Resume Analyzer"}


@app.post("/upload-resume")
async def upload_resume(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    allowed_extensions = [".pdf", ".doc", ".docx", ".png"]
    extension = os.path.splitext(file.filename)[1].lower()

    if extension not in allowed_extensions:
        raise HTTPException(status_code=400, detail="Only PDF, DOC, DOCX and PNG files are allowed")

    file_path = os.path.join(UPLOAD_DIR, os.path.basename(file.filename))
    content = await file.read()

    with open(file_path, "wb") as buffer:
        buffer.write(content)

    # Extract text
    extracted_text = ""
    if extension == ".pdf":
        try:
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        extracted_text += page_text + "\n"
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"PDF extraction failed: {str(e)}")

    if not extracted_text.strip():
        raise HTTPException(
            status_code=400,
            detail="Could not extract text from the file."
        )

    print("========== EXTRACTED TEXT ==========")
    print(extracted_text[:3000])

    # Save resume
    resume = Resume(
        file_name=file.filename,
        extracted_text=extracted_text
    )

    db.add(resume)
    db.commit()
    db.refresh(resume)

    # Auto analyze (Hugging Face powered)
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

    return {
        "resume_id": resume.id,
        "filename": file.filename,
        **result,
    }


@app.get("/analysis-history")
def get_analysis_history(db: Session = Depends(get_db)):
    return db.query(AnalysisResult).all()


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