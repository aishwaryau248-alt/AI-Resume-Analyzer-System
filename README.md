# AI Resume Analyzer System

## Project Overview

AI Resume Analyzer System is a full-stack web application that helps job seekers evaluate their resumes against industry-standard job roles using Artificial Intelligence and NLP techniques.

The system allows users to upload resumes, extract resume text, identify technical skills, calculate role match scores, detect missing skills, and generate AI-powered recommendations.

The application uses FastAPI for backend development, Streamlit for the frontend dashboard, SQLAlchemy ORM for database operations, and Hugging Face Inference API for intelligent career guidance.

---

## Problem Statement

Recruiters receive thousands of resumes for every job opening. Manual resume screening is time-consuming and often inconsistent.

This project automates the resume evaluation process by analyzing candidate skills, comparing them against job role requirements, and providing actionable recommendations to improve employability.

---

## Objectives

* Upload resumes in PDF, DOC, and DOCX formats
* Extract text from resumes
* Identify technical skills
* Match resumes with target job roles
* Calculate resume scores
* Detect missing skills
* Generate AI-based recommendations
* Store analysis history
* Visualize results through an interactive dashboard

---

## Features

### Resume Upload

* Upload PDF resumes
* Upload DOC resumes
* Upload DOCX resumes
* Automatic text extraction
* File validation

### Resume Analysis

* Skill extraction
* Missing skill identification
* Resume score calculation
* Role matching

### AI Features

* AI-powered recommendations
* Career guidance
* Skill improvement suggestions
* Certification recommendations

### Dashboard Features

* Resume upload interface
* Analysis dashboard
* History tracking
* Score visualization
* Resume management

### Database Features

* Resume storage
* Analysis result storage
* User information storage
* Historical analysis tracking

---

## Technology Stack

### Backend

* Python
* FastAPI
* SQLAlchemy ORM
* Pydantic

### Frontend

* Streamlit

### Database
* MySQL 

### AI / NLP

* Hugging Face Inference API
* Qwen2.5-7B-Instruct
* NLP Keyword Matching

### Libraries

* pdfplumber
* pandas
* requests
* python-dotenv
* passlib
* jose

---

## System Architecture

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
                +--------+---------+
                         |
      +------------------+------------------+
      |                  |                  |
      v                  v                  v
+-------------+  +--------------+  +------------------+
| Resume      |  | Skill        |  | AI Recommendation|
| Upload      |  | Matching     |  | Module           |
| Module      |  | Module       |  | (Hugging Face)   |
+-------------+  +--------------+  +------------------+
                         |
                         v
                +------------------+
                | MySQL Database   |
                +------------------+
```
## Project Structure

## Project Structure

```text
resume_ai_system/
│
├── backend/
│   ├── routes/
│   ├── models/
│   ├── schemas/
│   ├── services/
│   ├── database/
│   └── new.py
│
├── frontend/
│   └── ui.py
│
├── ml/
│   ├── skill_extractor/
│   ├── matching/
│   └── scoring/
│
├── uploads/
│
├── requirements.txt
├── README.md
├── .env
└── .gitignore
```

## Database Design

### Database Name

resume_ai_db

### Users Table

| Column     | Type     |
| ---------- | -------- |
| id         | Integer  |
| name       | String   |
| email      | String   |
| created_at | DateTime |

### Resumes Table

| Column         | Type     |
| -------------- | -------- |
| id             | Integer  |
| user_id        | Integer  |
| file_name      | String   |
| extracted_text | Text     |
| uploaded_at    | DateTime |

### Analysis Results Table

| Column          | Type     |
| --------------- | -------- |
| id              | Integer  |
| resume_id       | Integer  |
| role            | String   |
| score           | Float    |
| missing_skills  | Text     |
| strengths       | Text     |
| recommendations | Text     |
| created_at      | DateTime |

---

## Setup Instructions

### Step 1: Clone Repository

git clone https://github.com/yourusername/resume-ai-system.git

cd resume-ai-system

### Step 2: Create Virtual Environment

Windows

python -m venv venv

venv\Scripts\activate

Linux / Mac

python3 -m venv venv

source venv/bin/activate

### Step 3: Install Dependencies

pip install -r requirements.txt

---

## Environment Variables

Create a .env file:

HF_API_KEY=your_huggingface_api_key

DATABASE_URL=postgresql+psycopg2://username:password@localhost/resume_ai_db

---

## Database Setup

Create Database:

CREATE DATABASE resume_ai_db;

Run application and SQLAlchemy will automatically create tables.

---

## API Setup

Start FastAPI Server

uvicorn main:app --reload

Server URL

http://localhost:8000

Swagger Documentation

http://localhost:8000/docs

ReDoc Documentation

http://localhost:8000/redoc

---

## API Endpoints

### Upload Resume

POST /upload-resume

Description:

Uploads resume and extracts text.

---

### Analyze Resume

POST /analyze/{resume_id}

Description:

Analyzes resume against selected role.

---

### Get Resume Details

GET /resume/{resume_id}

Description:

Returns uploaded resume details.

---

### Analysis History

GET /analysis-history

Description:

Returns all analysis records.

---

### Delete Resume

DELETE /resume/{resume_id}

Description:

Deletes resume permanently.

---

## Streamlit Execution Steps

Navigate to frontend folder

cd frontend

Run Streamlit

streamlit run app.py

Open Browser

http://localhost:8501

---

## Dashboard Modules

### Upload Resume

* Upload files
* Extract text
* Save resume

### Analyze Resume

* Select role
* Calculate score
* Display skills
* Generate recommendations

### Analysis History

* View previous analyses
* Track scores
* Visualize trends

### Resume Management

* Fetch resume
* View details
* Delete resume

---

## AI / NLP Techniques Used

### Skill Extraction

The system uses keyword-based NLP matching to identify skills from extracted resume text.

### Resume Scoring

Score Formula:

Match Score = (Detected Skills / Required Skills) × 100

### Job Matching

Compares resume skills against role-specific skill requirements.

### AI Recommendations

Uses Hugging Face Inference API with Qwen2.5-7B-Instruct model to generate:

* Strengths
* Weaknesses
* Missing skills
* Certifications
* Project suggestions
* Career advice

---

## Validation Implemented

### File Validation

* Accepts PDF
* Accepts DOC
* Accepts DOCX
* Rejects unsupported files

### User Validation

* Email validation
* Duplicate prevention

### Resume Validation

* Empty text detection
* Missing resume handling

---

## Error Handling

Handles:

* Invalid file uploads
* Unsupported formats
* Missing resumes
* Database failures
* API failures
* Empty extracted text
* Hugging Face API exceptions

---

## Features Implemented

### Core Features

✔ Resume Upload

✔ Resume Text Extraction

✔ Resume Analysis

✔ Role Matching

✔ Skill Detection

✔ Resume Score Calculation

✔ Missing Skill Detection

✔ AI Recommendations

✔ Analysis History

✔ Resume Management

✔ Interactive Dashboard

---

### Resume Parsing

Different resume formats resulted in inconsistent text extraction.

### Skill Matching

Skills were represented in multiple formats and abbreviations.

### AI API Integration

Handling rate limits and external API failures.

### Database Relationships

Maintaining relationships between resumes and analysis results.

### Error Handling

Managing invalid uploads and missing records.

---
## Demo Video

🎥 Watch the complete project demo:

[https://youtu.be/your_video_link](https://youtu.be/_EoMX2bh0Zw?si=BJz3kfwHjQe1ofL0)

## Future Enhancements

* JWT Authentication
* User Login System
* Resume Ranking System
* Multi-Role Comparison
* TF-IDF Similarity Matching
* BERT Embedding Similarity
* ATS Resume Score
* PDF Report Generation
* Email Notifications
* Admin Dashboard

---

## Conclusion

The AI Resume Analyzer System successfully automates resume evaluation by combining NLP techniques, AI-generated recommendations, role-based matching, and database-driven history tracking. The project demonstrates practical implementation of FastAPI, Streamlit, SQLAlchemy, and external AI services in solving real-world recruitment challenges.

---

## Author

Name: AISHWARYA UNNIKRISHNAN

Email: [aishwaryau248@gmail.com](mailto:aishwaryau248@gmail.com)

GitHub: https://github.com/aishwaryau248-alt
