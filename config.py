import os
from typing import Optional

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

MODEL_NAME = "gpt-4o-mini"
TEMPERATURE = 0.3


def get_llm(api_key: Optional[str] = None) -> ChatOpenAI:
    """Create the app LLM after confirming that a key is configured."""
    api_key = api_key or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured.")
    return ChatOpenAI(model=MODEL_NAME, temperature=TEMPERATURE, api_key=api_key)


def get_smtp_settings() -> tuple[str, int, str, str, str]:
    """Load mail credentials from environment variables, never source code."""
    host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    port = int(os.getenv("SMTP_PORT", "587"))
    username = os.getenv("SMTP_USERNAME", "")
    password = os.getenv("SMTP_PASSWORD", "")
    sender = os.getenv("SMTP_FROM", username)
    if not all((username, password, sender)):
        raise RuntimeError(
            "SMTP is not configured. Set SMTP_USERNAME, SMTP_PASSWORD, and SMTP_FROM."
        )
    return host, port, username, password, sender
