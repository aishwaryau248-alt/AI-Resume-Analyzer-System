from huggingface_hub import InferenceClient
from dotenv import load_dotenv
import os

load_dotenv()

client = InferenceClient(
    api_key=os.getenv("HF_API_KEY")
)


def get_ai_recommendations(
    role,
    score,
    found_skills,
    missing_skills
):
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
            model="Qwen/Qwen2.5-7B-Instruct",
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
        print("HF ERROR:", str(e))

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