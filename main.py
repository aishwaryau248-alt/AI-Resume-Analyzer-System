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

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100))
    email = Column(String(255), unique=True, index=True)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))


class Resume(Base):
    __tablename__ = "resumes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
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
    created_at = Column(DateTime, default=datetime.now(timezone.utc))


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


# ---------------- ATS SCORE ----------------

def calculate_ats_score(resume_text: str, found_skills: list, missing_skills: list):

    text_lower = resume_text.lower()
    score = 0

    # 1. Skills Score (30)
    total_skills = len(found_skills) + len(missing_skills)
    if total_skills:
        skill_ratio = len(found_skills) / total_skills
        score += round(skill_ratio * 30)

    # 2. Resume Sections (15)
    sections = ["summary", "profile", "skills", "education", "experience", "projects", "certifications"]
    section_count = sum(1 for section in sections if section in text_lower)
    score += round((section_count / len(sections)) * 15)

    # 3. Contact Information (10)
    contact_score = 0
    has_email = bool(re.search(r'[\w\.-]+@[\w\.-]+\.\w+', resume_text))
    has_phone = bool(re.search(r'[\+\d][\d\s\-\(\)]{8,}', resume_text))
    has_linkedin = "linkedin.com" in text_lower

    if has_email:
        contact_score += 4
    if has_phone:
        contact_score += 4
    if has_linkedin:
        contact_score += 2
    score += contact_score

    # 4. Projects / Experience (15)
    project_keywords = [
        "project", "projects", "internship", "experience", "developed",
        "implemented", "created", "built", "designed", "dashboard", "api", "application"
    ]
    project_hits = sum(1 for word in project_keywords if word in text_lower)
    if project_hits >= 6:
        score += 15
    elif project_hits >= 4:
        score += 12
    elif project_hits >= 2:
        score += 8
    elif project_hits >= 1:
        score += 4

    # 5. Education (5)
    education_keywords = ["bca", "bsc", "btech", "mca", "msc", "degree", "university", "college"]
    if any(keyword in text_lower for keyword in education_keywords):
        score += 5

    # 6. Achievements (10)
    achievement_words = ["improved", "increased", "reduced", "optimized", "achieved", "boosted", "led", "managed"]
    achievement_hits = sum(1 for word in achievement_words if word in text_lower)
    percentage_hits = len(re.findall(r'\d+%', resume_text))
    achievement_total = achievement_hits + percentage_hits

    if achievement_total >= 5:
        score += 10
    elif achievement_total >= 3:
        score += 7
    elif achievement_total >= 1:
        score += 4

    # 7. Resume Length (5)
    word_count = len(resume_text.split())
    if 300 <= word_count <= 800:
        score += 5
    elif 200 <= word_count <= 1000:
        score += 3
    else:
        score += 1

    # 8. Formatting Quality (10)
    formatting_score = 0
    lines = resume_text.splitlines()
    if len(lines) >= 15:
        formatting_score += 3
    if ":" in resume_text:
        formatting_score += 2
    if "-" in resume_text or "•" in resume_text:
        formatting_score += 3
    if section_count >= 5:
        formatting_score += 2
    score += formatting_score

    score = min(score, 100)

    if score >= 85:
        status = "Excellent"
    elif score >= 70:
        status = "Good"
    elif score >= 50:
        status = "Average"
    else:
        status = "Poor"

    return score, status


# ---------------- ANALYSIS ----------------

def run_analysis(resume: Resume) -> dict:

    # STEP 1: AI ROLE + SKILL DETECTION
    ai_result = analyze_resume_ai(resume.extracted_text)

    role = (ai_result.get("predicted_role") or "").strip()
    found_skills = [s for s in ai_result.get("found_skills", []) if s]
    missing_skills = [s for s in ai_result.get("missing_skills", []) if s]

    # STEP 2: NO ROLE FOUND
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

    # STEP 3: SCORE CALCULATION
    total_skills = len(found_skills) + len(missing_skills)
    role_match_score = round((len(found_skills) / total_skills) * 100, 2) if total_skills else 0.0
    ats_score, ats_status = calculate_ats_score(resume.extracted_text, found_skills, missing_skills)

    # STRENGTHS
    strengths = []
    if found_skills:
        strengths.append(f"Matched {len(found_skills)} relevant skills")
    if "%" in resume.extracted_text:
        strengths.append("Contains quantified achievements")
    if len(resume.extracted_text) > 800:
        strengths.append("Detailed resume content")

    # IMPROVEMENTS
    improvements = []
    if missing_skills:
        improvements.append(f"Add missing skills: {', '.join(missing_skills)}")
    if "%" not in resume.extracted_text:
        improvements.append("Add measurable achievements using numbers and percentages")
    if len(resume.extracted_text) < 500:
        improvements.append("Add more project and work experience details")

    # AI RECOMMENDATIONS
    recommendations = get_ai_recommendations(role, role_match_score, found_skills, missing_skills)

    summary = (
        f"This resume matches {role_match_score}% of the required {role} skills. "
        f"ATS score is {ats_score}%. The resume demonstrates {len(found_skills)} matching skills "
        f"and {len(missing_skills)} missing skills."
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
    name: str,
    email: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    allowed_extensions = [".pdf", ".doc", ".docx", ".png"]
    extension = os.path.splitext(file.filename)[1].lower()

    if extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail="Only PDF, DOC, DOCX and PNG files are allowed"
        )

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

    # Upsert user
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(name=name, email=email)
        db.add(user)
        db.commit()
        db.refresh(user)

    # Save resume
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

    return {
        "resume_id": resume.id,
        "filename": file.filename,
        **result,
    }


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