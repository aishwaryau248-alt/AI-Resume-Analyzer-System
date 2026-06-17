import os
import json
import re
from dotenv import load_dotenv
from huggingface_hub import InferenceClient

load_dotenv()

client = InferenceClient(
    api_key=os.getenv("HF_API_KEY")
)

MODEL_NAME = "Qwen/Qwen2.5-7B-Instruct"


def _clean_json_text(raw: str) -> str:
    """
    The model is asked for raw JSON, but it sometimes wraps the answer in
    ```json ... ``` fences or adds a short preamble/postamble. This strips
    that noise down to the outermost {...} object so json.loads() succeeds.
    """
    cleaned = raw.strip()
    cleaned = re.sub(r'^```(?:json)?', '', cleaned).strip()
    cleaned = re.sub(r'```$', '', cleaned).strip()

    match = re.search(r'\{.*\}', cleaned, re.DOTALL)
    if match:
        cleaned = match.group(0)

    return cleaned


def _normalize_skill_list(skills) -> list:
    """Lowercase, strip, and de-duplicate a list of skill strings."""
    cleaned = []
    seen = set()

    if not isinstance(skills, list):
        return cleaned

    for skill in skills:
        if not isinstance(skill, str):
            continue
        name = skill.strip().lower()
        if name and name not in seen:
            seen.add(name)
            cleaned.append(name)

    return cleaned


def analyze_resume_ai(resume_text: str) -> dict:
    """
    Uses the Hugging Face hosted model to predict:
      - the single most likely job role for the resume
      - the skills the resume already demonstrates ("found_skills")
      - the skills typically required for that role that are missing

    This replaces the old CSV (ESCO) lookup and the hand-curated
    ROLE_SKILLS keyword dictionary - everything is now inferred by the
    model directly from the resume text.

    Returns a dict: {"predicted_role": str, "found_skills": [...], "missing_skills": [...]}
    On any failure (network error, malformed JSON, etc.) it returns a safe
    "Unknown" result instead of raising, so the caller can handle it cleanly.
    """

    prompt = f"""You are an expert technical recruiter and ATS system.

Read the resume text below and respond with ONLY a single JSON object.
Do not include any preamble, explanation, or markdown code fences - just
the raw JSON object, with exactly this shape:

{{
    "predicted_role": "<the single most likely job role for this candidate>",
    "found_skills": ["<skill the resume already demonstrates>", "..."],
    "missing_skills": ["<important skill for the predicted role that is NOT in the resume>", "..."]
}}

Rules:
- "predicted_role" must be a single, specific job title (e.g. "Data Analyst", "Backend Developer", "Machine Learning Engineer").
- If you cannot confidently identify a role from the resume, set "predicted_role" to "Unknown" and leave both skill lists empty.
- "found_skills" should only list concrete technical/professional skills you can see clear evidence of in the resume.
- "missing_skills" should list important, commonly-expected skills for the predicted role that are absent from the resume. Suggest 5-10 of these.
- Keep each skill name short (1-4 words) and lowercase. No duplicates between the two lists.

Resume:
\"\"\"
{resume_text[:4000]}
\"\"\"
"""

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            max_tokens=1000,
            temperature=0
        )

        raw_content = response.choices[0].message.content
        cleaned = _clean_json_text(raw_content)
        data = json.loads(cleaned)

        predicted_role = str(data.get("predicted_role") or "Unknown").strip()
        if not predicted_role:
            predicted_role = "Unknown"

        found_skills = _normalize_skill_list(data.get("found_skills"))
        missing_skills = _normalize_skill_list(data.get("missing_skills"))

        # a skill shouldn't be listed as both found and missing
        missing_skills = [s for s in missing_skills if s not in found_skills]

        return {
            "predicted_role": predicted_role,
            "found_skills": found_skills,
            "missing_skills": missing_skills,
        }

    except Exception as e:
        print("HF ANALYZE ERROR:", str(e))
        return {
            "predicted_role": "Unknown",
            "found_skills": [],
            "missing_skills": [],
        }


def get_ai_recommendations(role, score, found_skills, missing_skills):
    prompt = f"""
You are an expert resume reviewer and career advisor.

Target Role: {role}
Resume Match Score: {score:.1f}%

Detected Skills:
{', '.join(found_skills) if found_skills else 'None detected'}

Missing Skills:
{', '.join(missing_skills) if missing_skills else 'None'}

Provide:

1. Resume strengths
2. Resume weaknesses
3. Skills to learn
4. Recommended certifications
5. Project ideas
6. Final career advice

Keep the response professional, concise, and actionable.
"""

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            max_tokens=500
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        print("HF RECOMMEND ERROR:", str(e))

        return _fallback_recommendations(
            role,
            score,
            found_skills,
            missing_skills
        )


def _fallback_recommendations(
    role,
    score,
    found_skills,
    missing_skills
):
    tips = []

    if score < 40:
        tips.append(
            "Your resume needs significant improvement for this role."
        )
    elif score < 70:
        tips.append(
            "Good foundation. Focus on closing the skill gaps."
        )
    else:
        tips.append(
            "Strong match. Improve presentation and start applying."
        )

    if missing_skills:
        tips.append(
            f"Learn these missing skills: {', '.join(missing_skills)}."
        )

        tips.append(
            "Build practical projects demonstrating these skills."
        )

    tips.append(
        f"Look for {role} certifications on Coursera, Udemy, or LinkedIn Learning."
    )

    return "\n".join(tips)