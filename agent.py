from __future__ import annotations

"""Agent core logic for Study Buddy (Gemini version)"""

import os
import re
import streamlit as st

from dotenv import load_dotenv
from google import genai
from google.genai import types

from prompt import SYSTEM_PROMPT

# Load .env file
load_dotenv()


def _get_api_key(api_key: str | None = None) -> str:
    """
    Get Gemini API key.

    Priority:
    1. Function argument
    2. Streamlit secrets
    3. .env / environment variable
    """

    if api_key:
        return api_key.strip()

    # Streamlit Cloud
    try:
        key = st.secrets.get("GEMINI_API_KEY", "")
        if key:
            return str(key).strip()
    except Exception:
        pass

    # Local .env fallback
    return os.getenv("GEMINI_API_KEY", "").strip()


def _build_prompt(query: str, notes_text: str) -> str:

    return f"""
{SYSTEM_PROMPT or "You are a helpful study assistant."}

You are given study notes from a student.

Rules:
- Answer only from the notes.
- Do not invent information.
- If the answer is not available, say that it is not in the notes.
- Keep explanations clear and useful.

STUDY NOTES:
----------------
{notes_text}
----------------

QUESTION:
{query}
"""


def process_query(
    query: str,
    api_key: str | None = None,
    chat_history: list | None = None,
) -> str:
    """
    Send query to Gemini.
    """

    gemini_key = _get_api_key(api_key)

    if not gemini_key:
        return (
            "❌ Gemini API key not found. "
            "Please check your .env file."
        )


    notes_text = st.session_state.get(
        "notes_text",
        ""
    )

    if not notes_text:
        return (
            "📚 Please upload study material first. "
            "I need notes before answering."
        )


    try:

        client = genai.Client(
            api_key=gemini_key
        )


        prompt = _build_prompt(
            query,
            notes_text
        )


        response = client.models.generate_content(
            model="gemini-3.5-flash-lite",
            contents=prompt,
            config=types.GenerateContentConfig(
                max_output_tokens=700,
            ),
        )


        if response.text:
            return response.text.strip()


        return "No response generated."


    except Exception as e:

        return f"❌ Gemini Error: {str(e)}"

def generate_quiz(count: int, difficulty: str):
    """
    Generate structured quiz from notes.
    """

    notes_text = st.session_state.get("notes_text", "")

    if not notes_text:
        return []


    client = genai.Client(
        api_key=_get_api_key()
    )


    prompt = f"""
Create a {difficulty} level multiple choice quiz.

Use ONLY these notes:

{notes_text}


Return ONLY JSON format:

[
 {{
  "question": "question text",
  "options": [
      "option A",
      "option B",
      "option C",
      "option D"
  ],
  "answer": "correct option exactly"
 }}
]

Create {count} questions.
"""


    response = client.models.generate_content(
        model="gemini-3.5-flash-lite",
        contents=prompt
    )


    import json

    try:
        return json.loads(response.text)

    except:
        return []

def get_coach_response(query: str) -> str:
    """
    Offline fallback.
    """

    notes_text = st.session_state.get(
        "notes_text",
        ""
    )


    if not notes_text:
        return (
            "📚 Load study material first."
        )


    lowered = query.lower()


    if any(
        word in lowered
        for word in [
            "summary",
            "summarize",
            "summarise"
        ]
    ):

        return st.session_state.get(
            "summary",
            "No summary available."
        )


    if "topic" in lowered:

        topics = st.session_state.get(
            "topics",
            []
        )

        if topics:
            return (
                "Key topics:\n\n"
                +
                "\n".join(
                    f"• {t}"
                    for t in topics
                )
            )


    from utils import split_sentences


    STOP_WORDS = {
        "about",
        "after",
        "again",
        "also",
        "because",
        "been",
        "being",
        "between",
        "both",
        "can",
        "chapter",
        "each",
        "from",
        "have",
        "into",
        "more",
        "most",
        "notes",
        "only",
        "other",
        "over",
        "such",
        "that",
        "their",
        "these",
        "this",
        "through",
        "under",
        "using",
        "when",
        "which",
        "with",
        "would",
        "your",
    }


    terms = (
        set(
            re.findall(
                r"[a-z]{4,}",
                lowered
            )
        )
        -
        STOP_WORDS
    )


    for sentence in split_sentences(notes_text):

        words = set(
            re.findall(
                r"[a-z]{4,}",
                sentence.lower()
            )
        )

        if terms & words:

            return (
                "Relevant idea from your notes:\n\n"
                f"{sentence}\n\n"
                "Try explaining it in your own words."
            )


    return (
        "I couldn't find this in your notes. "
        "Try using different keywords."
    )
