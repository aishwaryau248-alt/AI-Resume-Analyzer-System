import random
import secrets
from datetime import datetime, timedelta

import pytz
from fastapi import APIRouter, Depends, FastAPI, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import (Boolean, Column, DateTime, Float, ForeignKey,
                        Integer, String, Text, create_engine)
from sqlalchemy.orm import Session, declarative_base, sessionmaker

# ── Constants ─────────────────────────────────────────────────────────────────
SECRET_KEY = "your_secret_key_here"
ALGORITHM  = "HS256"
IST        = pytz.timezone("Asia/Kolkata")

DATABASE_URL = "mysql+pymysql://root:1234@localhost/resume_ai_db"

# ── DB setup (auth.py owns the shared engine/Base) ───────────────────────────
engine       = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base         = declarative_base()

# ── Models ────────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id               = Column(Integer, primary_key=True, index=True)
    name             = Column(String(100))
    email            = Column(String(255), unique=True, index=True)
    password_hash    = Column(String(255))
    role             = Column(String(20), default="USER")
    is_verified      = Column(Boolean, default=False)
    reset_token      = Column(String(255), nullable=True)
    created_at       = Column(DateTime, default=lambda: datetime.now(IST))
    verification_otp = Column(String(6))


class Resume(Base):
    __tablename__ = "resumes"

    id             = Column(Integer, primary_key=True, index=True)
    user_id        = Column(Integer, ForeignKey("users.id"))
    file_name      = Column(String(255))
    extracted_text = Column(Text)
    uploaded_at    = Column(DateTime, default=lambda: datetime.now(IST))
    file_path = Column(String(500))


class AnalysisResult(Base):
    __tablename__ = "analysis_results"

    id             = Column(Integer, primary_key=True, index=True)
    resume_id      = Column(Integer, ForeignKey("resumes.id"))
    role           = Column(String(100))
    score          = Column(Float)
    missing_skills = Column(Text)
    strengths      = Column(Text)
    recommendations= Column(Text)
    ats_score      = Column(Float)
    ats_status     = Column(String(50))
    created_at     = Column(DateTime, default=lambda: datetime.now(IST))


Base.metadata.create_all(bind=engine)

# ── DB dependency ─────────────────────────────────────────────────────────────

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ── Password helpers ──────────────────────────────────────────────────────────

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

# ── JWT helpers ───────────────────────────────────────────────────────────────

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    to_encode["exp"] = datetime.utcnow() + timedelta(days=1)
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# ── Auth dependencies ─────────────────────────────────────────────────────────

def get_current_user(
    token: str  = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def require_agent(current_user: User = Depends(get_current_user)) -> User:
    """Dependency — allows only AGENT role."""
    if current_user.role != "AGENT":
        raise HTTPException(status_code=403, detail="Agent access required")
    return current_user


# ── Auth router (mounted into main.py's app via include_router) ───────────────

router = APIRouter()


@router.post("/register")
def register(
    name: str,
    email: str,
    password: str,
    db: Session = Depends(get_db),
):
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(
            status_code=400,
            detail="Email already exists"
        )

    otp = str(random.randint(100000, 999999))

    user = User(
        name=name,
        email=email,
        password_hash=hash_password(password),
        role="USER",
        is_verified=False,
        verification_otp=otp
    )

    db.add(user)
    db.commit()

    return {
        "message": "Registration successful",
        "otp": otp
    }
    
@router.get("/verify-email/{otp}")
def verify_email(
    otp: str,
    db: Session = Depends(get_db)
):

    user = db.query(User).filter(
        User.verification_otp == otp
    ).first()

    if not user:
        raise HTTPException(
            status_code=400,
            detail="Invalid OTP"
        )

    user.is_verified = True
    user.verification_otp = None

    db.commit()

    return {
        "message": "Email verified successfully"
    }




@router.post("/login")
def login(email: str, password: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email")
    if not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid password")
    if not user.is_verified:
        raise HTTPException(status_code=401, detail="Please verify your email first")

    token = create_access_token({"user_id": user.id, "role": user.role})
    return {"access_token": token}


@router.post("/forgot-password")
def forgot_password(email: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return {"message": "If email exists, reset link sent"}
    otp = str(random.randint(100000, 999999))
    user.reset_token = otp
    db.commit()
    return {"message": "Reset token generated", "otp": otp}


@router.post("/reset-password")
def reset_password(token: str, new_password: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.reset_token == token).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid reset token")
    user.password_hash = hash_password(new_password)
    user.reset_token   = None
    db.commit()
    return {"message": "Password reset successful"}


@router.get("/me")
def me(current_user: User = Depends(get_current_user)):
    return {
        "id":    current_user.id,
        "name":  current_user.name,
        "email": current_user.email,
        "role":  current_user.role,
    }