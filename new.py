from datetime import datetime, timedelta, timezone
import pdfplumber
from fastapi import FastAPI, HTTPException, Depends,APIRouter,File,UploadFile
from fastapi.security import OAuth2PasswordBearer
import os
from sqlalchemy import (
create_engine,
Column,
Integer,
String,
ForeignKey,
text,Text,
DateTime,
Boolean,
Float
)
from sqlalchemy.orm import declarative_base, sessionmaker,Session
from recomendation_service import get_ai_recommendations
from jose import jwt, JWTError
from pydantic import BaseModel
from passlib.context import CryptContext

# ---------------- DATABASE ---------------------------------

DATABASE_URL = "mysql+pymysql://root:1234@localhost/resume_ai_db"

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(
autocommit=False,
autoflush=False,
bind=engine
)

Base = declarative_base()

# ---------------- TABLES ----------------


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
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
    created_at = Column(DateTime, default=datetime.utcnow)


Base.metadata.create_all(bind=engine)

app = FastAPI()
# WELCOME PAGE



# Create uploads folder
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@app.get("/")
def first_start():
    return {
        "message": "Hi there, Welcome to Resume Analyzer"
    }
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        
@app.post("/upload-resume")
async def upload_resume(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):

    allowed_extensions = [".pdf", ".doc", ".docx"]

    extension = os.path.splitext(
        file.filename
    )[1].lower()

    if extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail="Only PDF, DOC, DOCX allowed"
        )

    # Save uploaded file
    file_path = os.path.join(
        UPLOAD_DIR,
        file.filename
    )

    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)

    # Extract PDF text
    text = ""

    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()

            if page_text:
                text += page_text + "\n"

    # Save into database
    resume = Resume(
        file_name=file.filename,
        extracted_text=text
    )

    db.add(resume)
    db.commit()
    db.refresh(resume)

    return {
        "resume_id": resume.id,
        "message": "File uploaded successfully",
        "filename": file.filename,
        "text": text
    }
    
ROLE_SKILLS = {

    "Data Scientist": [
        "python", "sql", "machine learning",
        "pandas", "numpy", "statistics",
        "tensorflow"
    ],

    "Data Analyst": [
        "excel", "sql", "power bi",
        "tableau", "python", "statistics"
    ],

    "Backend Developer": [
        "python", "fastapi",
        "postgresql", "docker", "api"
    ],

    "Frontend Developer": [
        "html", "css",
        "javascript", "react", "bootstrap"
    ],

    "Full Stack Developer": [
        "html", "css", "javascript",
        "react", "python", "sql"
    ],

    "AI Engineer": [
        "python", "tensorflow",
        "pytorch", "nlp", "llm"
    ],

    "Machine Learning Engineer": [
        "python", "scikit-learn",
        "tensorflow", "pandas", "numpy"
    ],

    "DevOps Engineer": [
        "docker", "kubernetes",
        "aws", "linux", "jenkins"
    ],

    "Cloud Engineer": [
        "aws", "azure",
        "gcp", "docker", "linux"
    ],

    "Cyber Security Analyst": [
        "network security",
        "ethical hacking",
        "siem", "linux", "firewall"
    ],

    "Software Engineer": [
        "python", "java",
        "sql", "git", "algorithms"
    ],

    "Java Developer": [
        "java", "spring boot",
        "hibernate", "mysql", "maven"
    ],

    "Python Developer": [
        "python", "django",
        "flask", "sql", "api"
    ],

    "Mobile App Developer": [
        "android", "kotlin",
        "java", "flutter", "firebase"
    ],

    "Android Developer": [
        "android", "java",
        "kotlin", "sqlite", "firebase"
    ],

    "iOS Developer": [
        "swift", "ios",
        "xcode", "objective-c", "api"
    ],

    "Database Administrator": [
        "sql", "mysql",
        "postgresql", "backup",
        "performance tuning"
    ],

    "Business Analyst": [
        "excel", "sql",
        "power bi", "communication",
        "requirements gathering"
    ],

    "QA Engineer": [
        "selenium", "testing",
        "automation", "jira", "api testing"
    ],

    "Project Manager": [
        "agile", "scrum",
        "jira", "leadership",
        "risk management"
    ]
}
def extract_skills(text, required_skills):
    found_skills = []

    for skill in required_skills:
        if skill.lower() in text.lower():
            found_skills.append(skill)

    return found_skills
ROLE_ALIASES = {
    "Devops Engineer": "DevOps Engineer",
    "Ios Developer": "iOS Developer",
    "Ai Engineer": "AI Engineer",
    "Qa Engineer": "QA Engineer",
}

@app.post("/analyze/{resume_id}")
def analyze_resume(
    resume_id : int,
    role :str,
    db : Session = Depends(get_db)
):
    role = role.strip().title()         
    role = ROLE_ALIASES.get(role, role)
    resume = db.query(Resume).filter(
        Resume.id == resume_id
    ).first()

    if not resume:
        raise HTTPException(
            status_code=404,
            detail="Resume not found"
        )

    if role not in ROLE_SKILLS:
        raise HTTPException(
            status_code=400,
            detail="Invalid role"
        )

    required_skills = ROLE_SKILLS[role]

    found_skills = extract_skills(
        resume.extracted_text,
        required_skills
    )

    missing_skills = list(
        set(required_skills) - set(found_skills)
    )

    score = (
        len(found_skills)
        / len(required_skills)
    ) * 100
    
    recommendations = get_ai_recommendations(
    role,
    score,
    found_skills,
    missing_skills
)
    print("AI Recommendation:", recommendations)

    analysis = AnalysisResult(
    resume_id=resume.id,
    role=role,
    score=score,
    missing_skills=", ".join(missing_skills),
    strengths=", ".join(found_skills),
    recommendations=recommendations
)

    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    return {
       
    "resume_id": resume.id,
    "role": role,
    "score": score,
    "found_skills": found_skills,
    "missing_skills": missing_skills,
    "recommendations": recommendations
}
    
@app.get("/resume/{resume_id}")
def get_resume(
    resume_id: int,
    db: Session = Depends(get_db)
):
    resume = db.query(Resume).filter(
        Resume.id == resume_id
    ).first()

    if not resume:
        raise HTTPException(
            status_code=404,
            detail="Resume not found"
        )

    return {
        "id": resume.id,
        "file_name": resume.file_name,
        "uploaded_at": resume.uploaded_at,
        "extracted_text": resume.extracted_text
    }
    
@app.get("/analysis-history")
def get_analysis_history(
    db: Session = Depends(get_db)
):
    results = db.query(
        AnalysisResult
    ).all()

    return results

@app.delete("/resume/{resume_id}")
def delete_resume(
    resume_id: int,
    db: Session = Depends(get_db)
):
    resume = db.query(Resume).filter(
        Resume.id == resume_id
    ).first()

    if not resume:
        raise HTTPException(
            status_code=404,
            detail="Resume not found"
        )

    db.delete(resume)
    db.commit()

    return {
        "message": "Resume deleted successfully"
    }
    

