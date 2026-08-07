# Study Buddy AI Agent

An agentic AI study companion built with **Streamlit + LangChain + OpenAI**.
Upload your notes/PDF and the agent decides which tool to use based on what
you ask — summarize, quiz you, make flashcards, build a revision plan, or
explain a concept.

## Why this is "agentic" (not a chatbot)

The app uses a LangChain **tool-calling agent** (`create_tool_calling_agent`
+ `AgentExecutor`), which means the LLM itself decides *which* tool to call
and *when*, based on your message — it isn't a fixed if/else pipeline. It
also has a real feedback loop: `generate_quiz` → `evaluate_answers` →
`explain_concept`, so it can react to how you performed.

## Required Tools (8, exceeds the 5-tool minimum)

| Tool | What it does |
|---|---|
| `read_pdf` | Surfaces the currently loaded notes to the agent |
| `summarize_notes` | Produces a structured summary (optionally focused on a sub-topic) |
| `extract_topics` | Pulls out key topics/concepts as a list |
| `generate_quiz` | Creates a multiple-choice quiz at a chosen difficulty |
| `evaluate_answers` | Grades submitted quiz answers and gives feedback |
| `generate_flashcards` | Creates front/back flashcards |
| `revision_planner` | Builds a day-by-day revision schedule |
| `explain_concept` | Explains a specific concept in simple terms with an analogy |

## Bonus features included

- **Difficulty levels** — Easy / Medium / Hard slider, fed into quiz generation.
- **Study schedule** — the Revision Plan tab, with real calendar dates.
- Voice mode is not included (would need a TTS/STT integration) — flagged
  below as an easy extension if you want to add it for extra credit.

## Setup

```bash
cd study_buddy
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` file beside `app.py` with your OpenAI key and SMTP credentials:

```dotenv
OPENAI_API_KEY=your_openai_key
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@example.com
SMTP_PASSWORD=your_email_app_password
SMTP_FROM=your_email@example.com
```

Use an email-provider app password for `SMTP_PASSWORD`; do not commit `.env`.

## Run

```bash
streamlit run app.py
```

Then open the local URL Streamlit prints (usually `http://localhost:8501`).

1. Configure your OpenAI API key and SMTP credentials in `.env`.
2. Upload a PDF of your notes, or paste text directly.
3. Use the **Chat** tab to talk to the agent naturally ("quiz me on chapter 3",
   "make 10 flashcards", "explain backpropagation"), or use the dedicated
   Quiz / Flashcards / Revision Plan / Summary tabs directly.

## Project structure

```
study_buddy/
├── app.py             # Full Streamlit app (UI + tools + agent)
├── requirements.txt
└── README.md
```

Everything lives in one file (`app.py`) for simplicity — it's organized into
clear sections: session state, helpers, the 8 tools, agent setup, sidebar,
and one section per tab.

## Ideas to extend for bonus points

- **Voice mode**: add `streamlit-webrtc` or `st.audio_input` + Whisper for
  input, and OpenAI TTS for spoken answers.
- **Persistence**: swap the in-memory `st.session_state` for a small SQLite
  DB so quiz history and flashcards survive a restart.
- **RAG over long notes**: if your PDFs are large, chunk + embed them with
  `langchain`'s vector store tools instead of truncating to `notes_context()`,
  and add a `search_notes` tool for the agent to query.
- **Local models**: swap `ChatOpenAI` for `ChatOllama` to run fully offline,
  matching the "Ollama/OpenAI" tech stack line in the assignment brief.
