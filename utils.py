import streamlit as st
import json
import re
from pypdf import PdfReader

def extract_pdf_text(uploaded_file):
    reader = PdfReader(uploaded_file)
    pages = []
    for page in reader.pages:
        pages.append(page.extract_text() or "")
    return "\n".join(pages)

def safe_json_extract(raw):
    match = re.search(r"(\[.*\]|\{.*\})", raw, re.DOTALL)
    if not match:
        raise ValueError("No JSON Found")
    return json.loads(match.group(1))

def truncate_text(text, limit=12000):
    if len(text) <= limit:
        return text
    return text[:limit] + "\n...[truncated]..."

def clean_text(text):
    return re.sub(r"\s+", " ", text).strip()

def split_sentences(text):
    return [clean_text(x) for x in re.split(r"(?<=[.!?])\s+|\n+", text) if len(clean_text(x)) > 25]

def get_notes_context(limit=12000):
    """Get current notes from session state"""
    if hasattr(st, 'session_state'):
        return truncate_text(st.session_state.notes_text, limit)
    return ""
