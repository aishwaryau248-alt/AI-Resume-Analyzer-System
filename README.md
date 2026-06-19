# AI Resume Analyzer System

## Project Overview

AI Resume Analyzer System is a full-stack web application that helps job seekers evaluate their resumes against industry-standard job roles using Artificial Intelligence, OCR, and NLP techniques.

The system allows users to register/login, upload resumes (PDF, DOC, DOCX, or image), extract resume text, detect the most likely job role, identify technical skills, calculate ATS and role-match scores, detect missing skills, and generate AI-powered recommendations. An AGENT role has full visibility across all users, resumes, and analysis history.

The application uses FastAPI for backend development, Streamlit for the frontend dashboard, SQLAlchemy ORM (MySQL) for database operations, JWT-based authentication, and Hugging Face's Mistral-7B-Instruct model for AI-driven career guidance.

---

## Problem Statement

Recruiters receive thousands of resumes for every job opening. Manual resume screening is time-consuming and often inconsistent.

This project automates the resume evaluation process by extracting resume content from multiple file formats, detecting the candidate's likely role, comparing their skills against role requirements, scoring the resume for ATS-friendliness, and providing actionable AI-generated recommendations to improve employability.

---

## Objectives

* Register and authenticate users with JWT + OTP email verification
* Upload resumes in PDF, DOC, DOCX, and image (PNG/JPG/JPEG/WEBP/BMP) formats
* Extract text from resumes (including OCR for images)
* Detect the candidate's most likely job role
* Identify technical skills and missing skills
* Calculate ATS score and role-match score
* Generate AI-based recommendations
* Store per-user analysis history
* Provide an AGENT dashboard with full visibility across all users/resumes
* Visualize results through an interactive Streamlit dashboard

---

## Features

### Authentication

* User registration with OTP email verification
* JWT-based login
* Forgot password / reset password flow
* Role-based access control (`USER` vs `AGENT`)

### Resume Upload

* Upload PDF resumes
* Upload DOC resumes
* Upload DOCX resumes (parsed directly via ZIP/XML, including headers/footers and text boxes)
* Upload image resumes (PNG, JPG, JPEG, WEBP, BMP) via Tesseract OCR
* File type and 5 MB size validation
* Empty-text detection and rejection

### Resume Analysis

* AI-driven role prediction
* Skill extraction (found vs. missing)
* ATS score calculation (rule-based, multi-factor)
* Role-match score calculation
* Strengths and improvement suggestions

### AI Features

* AI-powered recommendations via Hugging Face's `mistralai/Mistral-7B-Instruct-v0.3`
* Role-specific fallback content (certifications, projects, roadmap) for 20 curated roles
* Career guidance and skill-improvement suggestions

### Dashboard Features (USER)

* Resume upload & analysis interface
* ATS score ring and role-match visualization
* Tabbed results: Skills / Strengths & Improvements / AI Recommendations
* Personal analysis history with score trend chart

### Dashboard Features (AGENT)

* View all registered users
* View all uploaded resumes (with role, ATS score, role-match score)
* Search resumes by predicted role
* Download any user's original resume file
* View all analysis results across all users
* Recommendation viewer per analysis

### Database Features

* User storage with verification/reset tokens
* Resume storage with extracted text and file path
* Analysis result storage (role, score, ATS score/status, skills, recommendations)
* Per-user and global historical analysis tracking

---

## Technology Stack

### Backend

* Python
* FastAPI
* SQLAlchemy ORM
* Pydantic
* python-jose (JWT)
* passlib + bcrypt (password hashing)

### Frontend

* Streamlit

### Database

* MySQL (via PyMySQL)

### AI / NLP

* Hugging Face Inference API
* `mistralai/Mistral-7B-Instruct-v0.3`
* Rule-based NLP keyword/regex matching for skills and ATS scoring
* ESCO CSV dataset + curated 20-role mapping for role detection

### Text Extraction Libraries

* pdfplumber (PDF)
* lxml (DOCX — direct ZIP/XML parsing)
* pytesseract + Pillow (image OCR)
* antiword (legacy `.doc`, with raw-byte fallback)

### Other Libraries

* pandas, requests, python-dotenv, pytz

---

## System Architecture

```text
                +------------------+
                |      User        |
                +--------+---------+
                         |
                         v
                +------------------+
                | Streamlit UI     |
                | (Frontend)       |
                +--------+---------+
                         |
                         v
                +------------------+
                | FastAPI Backend  |
                | (Auth + Main)    |
                +--------+---------+
                         |
      +------------------+------------------+------------------+
      |                  |                  |                  |
      v                  v                  v                  v
+-------------+  +--------------+  +------------------+  +-------------+
| Resume      |  | Role/Skill   |  | AI Recommendation|  | Auth Module |
| Upload &    |  | Detection &  |  | Module            |  | (JWT, OTP,  |
| Extraction  |  | ATS Scoring  |  | (Hugging Face)    |  | Role-based) |
| Module      |  | Module       |  |                   |  |             |
+-------------+  +--------------+  +------------------+  +-------------+
                         |
                         v
                +------------------+
                | MySQL Database   |
                +------------------+
```

## Project Structure

```text
resume_ai_system/
│
├── backend/
│   ├── main.py                  # FastAPI app, routes, extraction, ATS scoring
│   ├── auth.py                  # Models, JWT auth, OTP, password reset
│   ├── recomendation_service.py # AI role detection + recommendations
│   └── uploads/                 # Stored original resume files
│
├── frontend/
│   └── app.py                   # Streamlit dashboard (Auth/User/Agent views)
│
├── requirements.txt
├── README.md
├── .env
└── .gitignore
```

## Database Design

### Database Name

`resume_ai_db`

### Users Table

| Column           | Type     |
| ---------------- | -------- |
| id                | Integer  |
| name              | String   |
| email             | String   |
| password_hash     | String   |
| role              | String   |
| is_verified       | Boolean  |
| reset_token       | String   |
| verification_otp  | String   |
| created_at        | DateTime |

### Resumes Table

| Column         | Type     |
| -------------- | -------- |
| id             | Integer  |
| user_id        | Integer  |
| file_name      | String   |
| file_path      | String   |
| extracted_text | Text     |
| uploaded_at    | DateTime |

### Analysis Results Table

| Column          | Type     |
| --------------- | -------- |
| id              | Integer  |
| resume_id       | Integer  |
| role            | String   |
| score           | Float    |
| ats_score       | Float    |
| ats_status      | String   |
| missing_skills  | Text     |
| strengths       | Text     |
| recommendations | Text     |
| created_at      | DateTime |

---

## Setup Instructions

### Step 1: Clone Repository

```
git clone https://github.com/yourusername/resume-ai-system.git
cd resume-ai-system
```

### Step 2: Create Virtual Environment

Windows
```
python -m venv venv
venv\Scripts\activate
```

Linux / Mac
```
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies

```
pip install -r requirements.txt
```

### Step 4: Install Tesseract OCR (required for image resumes)

Windows: install Tesseract and ensure the path in `main.py` (`pytesseract.pytesseract.tesseract_cmd`) matches your install location.

Linux:
```
sudo apt-get install tesseract-ocr
```

### Step 5 (Optional): Install antiword for legacy `.doc` extraction

If `antiword` is not available, `.doc` files fall back to a raw-byte text scan.

---

## Environment Variables

Create a `.env` file:

```
HF_API_KEY=your_huggingface_api_key
DATABASE_URL=mysql+pymysql://root:1234@localhost/resume_ai_db
SECRET_KEY=your_secret_key_here
```

---

## Database Setup

Create Database:

```sql
CREATE DATABASE resume_ai_db;
```

Run the application and SQLAlchemy will automatically create the `users`, `resumes`, and `analysis_results` tables.

---

## API Setup

Start FastAPI Server

```
uvicorn main:app --reload
```

Server URL: `http://localhost:8000`

Swagger Documentation: `http://localhost:8000/docs`

ReDoc Documentation: `http://localhost:8000/redoc`

---

## API Endpoints

### Auth

| Method | Endpoint                     | Description                          |
| ------ | ----------------------------- | ------------------------------------ |
| POST   | `/register`                   | Register a new user, returns OTP     |
| GET    | `/verify-email/{otp}`         | Verify account using OTP              |
| POST   | `/login`                      | Login, returns JWT access token       |
| POST   | `/forgot-password`            | Generate password reset token          |
| POST   | `/reset-password`             | Reset password using token             |
| GET    | `/me`                         | Get current authenticated user info   |

### User (requires login)

| Method | Endpoint               | Description                                   |
| ------ | ----------------------- | ---------------------------------------------- |
| POST   | `/upload-resume`        | Upload resume, extract text, run full analysis |
| GET    | `/my-history`           | Get the logged-in user's analysis history       |
| GET    | `/my-resumes`           | Get the logged-in user's uploaded resumes        |
| GET    | `/resume/{resume_id}`   | Get a resume's details (own resume, or any if AGENT) |
| DELETE | `/resume/{resume_id}`   | Delete own resume (or any if AGENT)              |

### Agent-only (requires AGENT role)

| Method | Endpoint                       | Description                                  |
| ------ | -------------------------------- | --------------------------------------------- |
| GET    | `/agent/users`                   | View all registered users                      |
| GET    | `/agent/resumes`                 | View every uploaded resume with analysis data   |
| GET    | `/agent/search-role`             | Search resumes by predicted role                |
| GET    | `/agent/analysis-history`        | View all analysis results across all users       |
| GET    | `/agent/download/{resume_id}`    | Download a resume's original file               |

---

## Streamlit Execution Steps

Navigate to frontend folder
```
cd frontend
```

Run Streamlit
```
streamlit run app.py
```

Open Browser: `http://localhost:8501`

---

## Dashboard Modules

### Auth

* Login
* Register with OTP verification
* Forgot / reset password

### Upload & Analyze (USER + AGENT)

* Upload resume file
* View detected role, ATS score, role-match score
* View found/missing skills, strengths, improvements
* View AI-generated recommendations

### My History (USER + AGENT)

* View own past analyses
* Score trend chart
* Average/best score metrics

### Agent Dashboard (AGENT only)

* All registered users
* All uploaded resumes (with search by role, download original file)
* All analysis results with recommendations, across all users

---

## AI / NLP Techniques Used

### Role Detection

Role prediction is performed by the AI recommendation service, using ESCO CSV data as the primary role source alongside a curated 20-role mapping, with title-extraction from resume headers as an additional signal.

### Skill Extraction

Regex word-boundary keyword matching identifies found and missing skills against the detected role's skill list.

### Resume Scoring

```
Role Match Score = (Found Skills / Total Required Skills) × 100
```

### ATS Score

A weighted, rule-based score (0–100) combining:

* Skill match ratio (up to 30 pts)
* Resume section coverage — summary, skills, education, experience, projects, certifications (up to 15 pts)
* Contact info presence — email, phone, LinkedIn (up to 10 pts)
* Project/experience keyword density (up to 15 pts)
* Education keywords (5 pts)
* Quantified achievements — % figures, action verbs (up to 10 pts)
* Word count / structure / formatting signals (up to remaining pts)

Status bands: Excellent (≥85), Good (≥70), Average (≥50), Poor (<50)

### AI Recommendations

Uses Hugging Face Inference API with `mistralai/Mistral-7B-Instruct-v0.3` to generate role-specific:

* Certifications
* Project suggestions
* Career roadmap
* Strength/weakness-aware advice

Falls back to curated role-specific content for 20 mapped roles if the AI call fails.

---

## Validation Implemented

### File Validation

* Accepts PDF, DOC, DOCX, PNG, JPG, JPEG, WEBP, BMP
* Rejects unsupported file types
* Rejects files over 5 MB

### User Validation

* Email format and duplicate-account prevention
* Email verification via OTP before login is allowed

### Resume Validation

* Empty/unreadable extracted text detection
* Missing resume handling on lookups

---

## Error Handling

Handles:

* Invalid or unsupported file uploads
* Corrupted DOCX files
* Empty extracted text
* Missing resumes/users
* Invalid or expired JWT tokens
* Invalid OTP / reset tokens
* Database failures
* Hugging Face API exceptions / failures (falls back to curated recommendations)

---

## Features Implemented

### Core Features

✔ User Registration & OTP Email Verification

✔ JWT Authentication & Role-Based Access (USER / AGENT)

✔ Resume Upload (PDF, DOC, DOCX, Image)

✔ Multi-format Text Extraction (incl. OCR)

✔ AI Role Detection

✔ Skill Detection (Found / Missing)

✔ ATS Score Calculation

✔ Role Match Score Calculation

✔ AI Recommendations (with fallback content)

✔ Per-user Analysis History

✔ Agent Dashboard (Users / Resumes / Analyses / Downloads)

✔ Interactive Streamlit Dashboard

---

## Challenges Solved

### Resume Parsing

Different resume formats (PDF, DOC, DOCX, images) resulted in inconsistent text extraction — solved with format-specific extractors, including direct ZIP/XML parsing for DOCX (to capture text boxes) and Tesseract OCR for images.

### Skill Matching

Skills were represented in multiple formats and abbreviations — addressed with regex word-boundary matching and normalization.

### AI API Integration

Handling Hugging Face rate limits and API failures — solved with try/except fallbacks to curated role-specific recommendation content.

### Database Relationships

Maintaining relationships between users, resumes, and analysis results via foreign keys and outer joins (so unanalyzed resumes are never hidden from agents).

### Access Control

Ensuring users can only view/delete their own resumes while agents retain full visibility, enforced via FastAPI dependencies (`get_current_user`, `require_agent`).

---

## Future Enhancements

* Resume Ranking System
* Multi-Role Comparison
* TF-IDF / BERT Embedding Similarity Matching
* PDF Report Generation
* Email Notifications (real OTP delivery instead of in-response OTP)
* Refresh tokens / token revocation
* Admin analytics dashboard

---

## Conclusion

The AI Resume Analyzer System automates resume evaluation by combining multi-format text extraction (including OCR), AI-driven role detection, rule-based ATS scoring, AI-generated recommendations, JWT-secured role-based access, and database-driven history tracking. The project demonstrates practical implementation of FastAPI, Streamlit, SQLAlchemy, JWT authentication, and external AI services in solving real-world recruitment screening challenges.

---

## Author

Name: AISHWARYA UNNIKRISHNAN

Email: [aishwaryau248@gmail.com](mailto:aishwaryau248@gmail.com)

GitHub: https://github.com/aishwaryau248-alt
