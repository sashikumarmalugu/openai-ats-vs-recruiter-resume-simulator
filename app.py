import streamlit as st
import pdfplumber
import os
from openai import OpenAI
from dotenv import load_dotenv
import re

# ---------------- CONFIG ----------------
st.set_page_config(
    page_title="ATS vs Recruiter Resume Simulator",
    layout="wide",
    page_icon="📄"
)

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ---------------- HELPERS ----------------
def extract_resume_text(pdf_file):
    text = ""
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ""
    return text


def extract_keywords(jd_text):
    words = re.findall(r"\b[A-Za-z]{3,}\b", jd_text.lower())
    return list(set(words))


def ats_score(resume_text, jd_text):
    jd_keywords = extract_keywords(jd_text)
    matched = [kw for kw in jd_keywords if kw in resume_text.lower()]
    score = int((len(matched) / max(len(jd_keywords), 1)) * 100)

    return {
        "score": min(score, 95),
        "matched": matched[:15],
        "missing": list(set(jd_keywords) - set(matched))[:15],
    }


def openai_analysis(prompt):
    response = client.chat.completions.create(
        model="gpt-5-nano",
        messages=[{"role": "user", "content": prompt}]    )
    return response.choices[0].message.content


# ---------------- UI ----------------
st.title("🧠 ATS vs Recruiter Resume Simulator")
st.caption("See *why* your resume passes machines but fails humans (or vice versa)")

col1, col2 = st.columns(2)

with col1:
    resume_file = st.file_uploader("Upload Resume (PDF)", type=["pdf"])

with col2:
    jd_text = st.text_area("Paste Job Description", height=200)

if resume_file and jd_text:
    resume_text = extract_resume_text(resume_file)

    with st.spinner("Analyzing resume..."):
        ats = ats_score(resume_text, jd_text)

        ats_prompt = f"""
        You are an ATS system.
        Resume:
        {resume_text}

        Job Description:
        {jd_text}

        Evaluate ATS compatibility, section structure, and rejection risk.
        Give bullet-point feedback.
        """

        recruiter_prompt = f"""
        You are a senior recruiter scanning this resume for 30 seconds.

        Resume:
        {resume_text}

        Job Description:
        {jd_text}

        Answer:
        - Hire / Maybe / Reject
        - Why
        - Red flags
        - 3 improvements
        """

        ats_feedback = openai_analysis(ats_prompt)
        recruiter_feedback = openai_analysis(recruiter_prompt)

    st.divider()

    left, right = st.columns(2)

    # -------- ATS VIEW --------
    with left:
        st.subheader("🤖 ATS System View")

        st.metric("ATS Score", f"{ats['score']}%")

        st.progress(ats["score"] / 100)

        st.markdown("**✅ Matched Keywords**")
        st.write(", ".join(ats["matched"]) or "None")

        st.markdown("**❌ Missing Keywords**")
        st.write(", ".join(ats["missing"]) or "None")

        st.markdown("**ATS Feedback**")
        st.info(ats_feedback)

    # -------- RECRUITER VIEW --------
    with right:
        st.subheader("👩‍💼 Recruiter View")

        st.warning("30-Second Human Judgment")

        st.success(recruiter_feedback)
