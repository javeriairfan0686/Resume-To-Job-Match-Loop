"""
Resume to Job Match - Step 1: Input UI
----------------------------------------
This app lets you:
  1. Upload your resume (PDF or DOCX) and extracts the raw text from it.
  2. Provide a Job Description either by pasting text directly or
     uploading a .txt file.

This is the foundation step. Once both texts are extracted, they're
ready to be passed into an LLM for gap analysis / resume tailoring
(that's the next step in the project).

Run with:
    streamlit run app.py
"""

import streamlit as st
import pdfplumber
import docx
import io


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


# ---------------------------------------------------------------------------
# Streamlit UI
# ---------------------------------------------------------------------------

st.set_page_config(page_title="Resume to JD Match - Input", layout="wide")

st.title("Resume to Job Match Loop - Step 1: Inputs")
st.write(
    "Upload your resume and provide a job description. "
    "This step just extracts and shows the raw text - "
    "the next step will send this to an LLM for analysis."
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
# Status / next step placeholder
# ---------------------------------------------------------------------------
st.divider()

if resume_text and jd_text:
    st.success("Both resume and JD are ready. Next step: send these to an LLM for analysis.")
    st.session_state["resume_text"] = resume_text
    st.session_state["jd_text"] = jd_text
else:
    st.info("Upload a resume and provide a job description to continue.")