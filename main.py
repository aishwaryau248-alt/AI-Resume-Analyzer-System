from datetime import datetime, timezone
import pdfplumber
from fastapi import FastAPI, HTTPException, Depends, File, UploadFile
import os
from sqlalchemy import (
    create_engine, Column, Integer, String,
    ForeignKey, Text, DateTime, Float
)
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from recomendation_service import get_ai_recommendations

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

# ---------------- ROLE SKILLS ----------------

ROLE_SKILLS = {
    "Data Scientist": ["python", "sql", "machine learning", "pandas", "numpy", "statistics", "tensorflow"],
    "Data Analyst": ["excel", "sql", "power bi", "tableau", "python", "statistics"],
    "Backend Developer": ["python", "fastapi", "postgresql", "docker", "api"],
    "Frontend Developer": ["html", "css", "javascript", "react", "bootstrap"],
    "Full Stack Developer": ["html", "css", "javascript", "react", "python", "sql"],
    "AI Engineer": ["python", "tensorflow", "pytorch", "nlp", "llm"],
    "Machine Learning Engineer": ["python", "scikit-learn", "tensorflow", "pandas", "numpy"],
    "DevOps Engineer": ["docker", "kubernetes", "aws", "linux", "jenkins"],
    "Cloud Engineer": ["aws", "azure", "gcp", "docker", "linux"],
    "Cyber Security Analyst": ["network security", "ethical hacking", "siem", "linux", "firewall"],
    "Software Engineer": ["python", "java", "sql", "git", "algorithms"],
    "Java Developer": ["java", "spring boot", "hibernate", "mysql", "maven"],
    "Python Developer": ["python", "django", "flask", "sql", "api"],
    "Mobile App Developer": ["android", "kotlin", "java", "flutter", "firebase"],
    "Android Developer": ["android", "java", "kotlin", "sqlite", "firebase"],
    "iOS Developer": ["swift", "ios", "xcode", "objective-c", "api"],
    "Database Administrator": ["sql", "mysql", "postgresql", "backup", "performance tuning"],
    "Business Analyst": ["excel", "sql", "power bi", "communication", "requirements gathering"],
    "QA Engineer": ["selenium", "testing", "automation", "jira", "api testing"],
    "Project Manager": ["agile", "scrum", "jira", "leadership", "risk management"],
}

# ---------------- HELPERS ----------------

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def detect_role(resume_text: str) -> str:
    text = resume_text.lower()
    role_scores = {
        role: sum(1 for skill in skills if skill.lower() in text)
        for role, skills in ROLE_SKILLS.items()
    }
    return max(role_scores, key=role_scores.get)

def extract_skills(text: str, required_skills: list) -> list:
    return [skill for skill in required_skills if skill.lower() in text.lower()]
def calculate_ats_score(resume: Resume, found_skills: list, missing_skills: list, required_skills: list) -> tuple[int, str]:
    resume_text = resume.extracted_text
    text_lower = resume_text.lower()
    ats_score = 100

    # --- SKILL COVERAGE (max -40) ---
    skill_ratio = len(found_skills) / len(required_skills) if required_skills else 0

    if skill_ratio < 0.4:
        ats_score -= 40
    elif skill_ratio < 0.6:
        ats_score -= 25
    elif skill_ratio < 0.75:
        ats_score -= 15
    elif skill_ratio < 0.9:
        ats_score -= 5

    # --- MISSING SKILLS PENALTY (max -20) ---
    if len(missing_skills) >= 5:
        ats_score -= 20
    elif len(missing_skills) >= 4:
        ats_score -= 15
    elif len(missing_skills) >= 3:
        ats_score -= 10
    elif len(missing_skills) >= 2:
        ats_score -= 5

    # --- CONTENT LENGTH (max -15) ---
    word_count = len(resume_text.split())
    if word_count < 150:
        ats_score -= 15
    elif word_count < 300:
        ats_score -= 10
    elif word_count < 500:
        ats_score -= 5

    # --- QUANTIFIED ACHIEVEMENTS (max -10) ---
    import re
    quantifiers = re.findall(r'\d+\s*(%|x|years?|months?|\+)', resume_text, re.IGNORECASE)
    if len(quantifiers) == 0:
        ats_score -= 10
    elif len(quantifiers) < 3:
        ats_score -= 5

    # --- SECTION HEADERS (max -10) ---
    expected_sections = ["experience", "education", "skills", "projects"]
    found_sections = sum(1 for s in expected_sections if s in text_lower)
    if found_sections < 2:
        ats_score -= 10
    elif found_sections < 3:
        ats_score -= 5

    # --- CONTACT INFO (max -5) ---
    has_email = bool(re.search(r'[\w\.-]+@[\w\.-]+\.\w+', resume_text))
    has_phone = bool(re.search(r'[\+\d][\d\s\-\(\)]{8,}', resume_text))
    if not has_email:
        ats_score -= 3
    if not has_phone:
        ats_score -= 2

    ats_score = max(0, ats_score)

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
    """Core analysis logic — returns the full result dict."""
    role = detect_role(resume.extracted_text)
    required_skills = ROLE_SKILLS[role]
    found_skills = extract_skills(resume.extracted_text, required_skills)
    missing_skills = [s for s in required_skills if s not in found_skills]

    role_match_score = round((len(found_skills) / len(required_skills)) * 100, 2)
    ats_score, ats_status = calculate_ats_score(resume, found_skills, missing_skills, required_skills)
    # Strengths
    strengths = []
    if found_skills:
        strengths.append(f"Matched {len(found_skills)} required skills")
    if "%" in resume.extracted_text:
        strengths.append("Contains quantified achievements")
    if len(resume.extracted_text) > 800:
        strengths.append("Detailed resume content")

    # Improvements
    improvements = []
    if missing_skills:
        improvements.append(f"Add missing skills: {', '.join(missing_skills)}")
    if "%" not in resume.extracted_text:
        improvements.append("Add measurable achievements using numbers and percentages")
    if len(resume.extracted_text) < 500:
        improvements.append("Add more project and work experience details")

    # AI Recommendations
    recommendations = get_ai_recommendations(role, role_match_score, found_skills, missing_skills)

    summary = (
        f"This resume matches {role_match_score}% of the required {role} skills. "
        f"ATS score is {ats_score}%. "
        f"The resume demonstrates {len(found_skills)} matching skills and {len(missing_skills)} missing skills."
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
    allowed_extensions = [".pdf", ".doc", ".docx"]
    extension = os.path.splitext(file.filename)[1].lower()

    if extension not in allowed_extensions:
        raise HTTPException(status_code=400, detail="Only PDF, DOC, DOCX files are allowed")

    file_path = os.path.join(UPLOAD_DIR, os.path.basename(file.filename))
    content = await file.read()

    with open(file_path, "wb") as buffer:
        buffer.write(content)

    # Extract text
    text = ""
    if extension == ".pdf":
        try:
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"PDF extraction failed: {str(e)}")

    if not text.strip():
        raise HTTPException(status_code=400, detail="Could not extract text from the file.")

    # Save resume
    resume = Resume(file_name=file.filename, extracted_text=text)
    db.add(resume)
    db.commit()
    db.refresh(resume)

    # Auto-analyze
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