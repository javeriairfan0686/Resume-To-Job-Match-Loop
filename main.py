"""
Resume to Job Match - Step 1 & 2: Input + LLM Analysis
--------------------------------------------------------
This app lets you:
  1. Upload your resume (PDF or DOCX) and extracts the raw text from it.
  2. Provide a Job Description either by pasting text directly or
     uploading a .txt file.
  3. Send both to Claude for a gap analysis:
       - skills/keywords missing from the resume
       - resume bullet points that already match well
       - suggested rewrites for specific bullet points

Requires an Anthropic API key (https://console.anthropic.com).
Set it as an environment variable ANTHROPIC_API_KEY, or paste it
into the sidebar field when running the app.

Run with:
    streamlit run app.py
"""

import streamlit as st
import pdfplumber
import docx
import io
import json
import os
import anthropic


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract all text from a PDF file given as bytes."""
    text_parts = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    return "\n".join(text_parts)


def extract_text_from_docx(file_bytes: bytes) -> str:
    """Extract all text from a DOCX file given as bytes."""
    document = docx.Document(io.BytesIO(file_bytes))
    paragraphs = [para.text for para in document.paragraphs if para.text.strip()]
    return "\n".join(paragraphs)


def extract_resume_text(uploaded_file) -> str:
    """Detect file type (PDF or DOCX) and extract text accordingly."""
    file_bytes = uploaded_file.read()
    filename = uploaded_file.name.lower()

    if filename.endswith(".pdf"):
        return extract_text_from_pdf(file_bytes)
    elif filename.endswith(".docx"):
        return extract_text_from_docx(file_bytes)
    else:
        raise ValueError("Unsupported file type. Please upload a PDF or DOCX file.")


def build_analysis_prompt(resume_text: str, jd_text: str) -> str:
    """Build the prompt that asks Claude to compare resume vs JD."""
    return f"""You are an expert resume reviewer and career coach.

Compare the RESUME and JOB DESCRIPTION below and produce an analysis.

RESUME:
\"\"\"
{resume_text}
\"\"\"

JOB DESCRIPTION:
\"\"\"
{jd_text}
\"\"\"

Do the following:
1. "missing_skills": List important skills, tools, or requirements from the
   job description that are missing or weak in the resume.
2. "strong_matches": List resume bullet points or experiences that already
   align well with this job description.
3. "suggested_rewrites": For 3-5 resume bullet points, suggest an improved
   version that better aligns with the job description. Do NOT invent new
   experience, skills, or job titles - only rephrase, reorder, or emphasize
   what is already present in the resume. Each item should have "original"
   and "rewrite" fields.

Respond with ONLY a valid JSON object (no markdown fences, no extra text)
using exactly this structure:

{{
  "missing_skills": ["...", "..."],
  "strong_matches": ["...", "..."],
  "suggested_rewrites": [
    {{"original": "...", "rewrite": "..."}}
  ]
}}
"""


def analyze_resume_vs_jd(api_key: str, resume_text: str, jd_text: str) -> dict:
    """Send resume + JD to Claude and return the parsed JSON analysis."""
    client = anthropic.Anthropic(api_key=api_key)

    prompt = build_analysis_prompt(resume_text, jd_text)

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )

    raw_text = response.content[0].text.strip()

    # Defensive cleanup in case the model wraps the JSON in markdown fences
    if raw_text.startswith("```"):
        raw_text = raw_text.strip("`")
        if raw_text.lower().startswith("json"):
            raw_text = raw_text[4:].strip()

    return json.loads(raw_text)


# ---------------------------------------------------------------------------
# Streamlit UI
# ---------------------------------------------------------------------------

st.set_page_config(page_title="Resume to JD Match", layout="wide")

st.title("Resume to Job Match Loop - Step 1 & 2: Inputs + Analysis")
st.write(
    "Upload your resume and provide a job description, then click "
    "'Analyze Match' to get a gap analysis from Claude."
)

with st.sidebar:
    st.header("Settings")
    default_key = os.environ.get("ANTHROPIC_API_KEY", "")
    api_key = st.text_input(
        "Anthropic API Key",
        value=default_key,
        type="password",
        help="Get one at https://console.anthropic.com. "
             "You can also set it as the ANTHROPIC_API_KEY environment variable.",
    )

col1, col2 = st.columns(2)

# ---------------------------------------------------------------------------
# Column 1: Resume upload
# ---------------------------------------------------------------------------
with col1:
    st.header("1. Your Resume")
    resume_file = st.file_uploader(
        "Drop or select your resume (PDF or DOCX)",
        type=["pdf", "docx"],
    )

    resume_text = ""
    if resume_file is not None:
        try:
            resume_text = extract_resume_text(resume_file)
            st.success(f"Extracted text from: {resume_file.name}")
            st.text_area("Extracted Resume Text", resume_text, height=400)
        except Exception as e:
            st.error(f"Could not read resume: {e}")

# ---------------------------------------------------------------------------
# Column 2: Job Description input
# ---------------------------------------------------------------------------
with col2:
    st.header("2. Job Description")

    input_method = st.radio(
        "How do you want to provide the JD?",
        ["Paste text", "Upload .txt file"],
        horizontal=True,
    )

    jd_text = ""
    if input_method == "Paste text":
        jd_text = st.text_area(
            "Paste the job description here", height=400, placeholder="Paste JD text..."
        )
    else:
        jd_file = st.file_uploader("Drop or select a .txt file with the JD", type=["txt"])
        if jd_file is not None:
            jd_text = jd_file.read().decode("utf-8", errors="ignore")
            st.success(f"Loaded JD from: {jd_file.name}")
            st.text_area("Job Description Text", jd_text, height=400)

# ---------------------------------------------------------------------------
# Analysis section
# ---------------------------------------------------------------------------
st.divider()

if resume_text and jd_text:
    st.success("Both resume and JD are ready.")
    st.session_state["resume_text"] = resume_text
    st.session_state["jd_text"] = jd_text

    analyze_clicked = st.button("Analyze Match", type="primary", disabled=not api_key)
    if not api_key:
        st.warning("Enter your Anthropic API key in the sidebar to enable analysis.")

    if analyze_clicked:
        with st.spinner("Analyzing resume against job description..."):
            try:
                analysis = analyze_resume_vs_jd(api_key, resume_text, jd_text)
                st.session_state["analysis"] = analysis
            except json.JSONDecodeError:
                st.error("Claude returned a response that wasn't valid JSON. Try again.")
            except Exception as e:
                st.error(f"Analysis failed: {e}")

    # Display results if available
    analysis = st.session_state.get("analysis")
    if analysis:
        st.subheader("Results")

        res_col1, res_col2 = st.columns(2)

        with res_col1:
            st.markdown("**Missing / Weak Skills**")
            missing = analysis.get("missing_skills", [])
            if missing:
                for item in missing:
                    st.markdown(f"- {item}")
            else:
                st.write("None found.")

        with res_col2:
            st.markdown("**Strong Matches**")
            matches = analysis.get("strong_matches", [])
            if matches:
                for item in matches:
                    st.markdown(f"- {item}")
            else:
                st.write("None found.")

        st.markdown("**Suggested Bullet Point Rewrites**")
        rewrites = analysis.get("suggested_rewrites", [])
        if rewrites:
            for i, item in enumerate(rewrites, start=1):
                with st.expander(f"Rewrite suggestion {i}"):
                    st.markdown("**Original:**")
                    st.write(item.get("original", ""))
                    st.markdown("**Suggested rewrite:**")
                    st.write(item.get("rewrite", ""))
        else:
            st.write("No rewrite suggestions returned.")

else:
    st.info("Upload a resume and provide a job description to continue.")