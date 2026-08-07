"""Study Buddy AI Agent — Full Streamlit UI"""

from __future__ import annotations
import re
from collections import Counter
from datetime import date, timedelta
from pathlib import Path
import streamlit as st
from pypdf import PdfReader

from utils import clean_text, split_sentences
from agent import (
    process_query,
    get_coach_response,
    generate_quiz
)
from auth import (
    register_user,
    login_user,
    reset_password,
    send_login_otp,
    send_password_reset_otp,
    verify_otp
)

from database import SessionLocal
from models import User

APP_DIR = Path(__file__).parent
DEMO_NOTES = APP_DIR / "data" / "sample_biology_notes.txt"
STOP_WORDS = {"about", "after", "again", "also", "because", "been", "being", 
            "between", "both", "can", "chapter", "each", "from", "have", 
            "into", "more", "most", "notes", "only", "other", "over", 
            "such", "that", "their", "these", "this", "through", "under", 
            "using", "when", "which", "with", "would", "your"}

st.set_page_config(page_title="Study Buddy", page_icon=":material/menu_book:", layout="wide")

def init_state():
    defaults = {
        "notes_text": "",
        "notes_name": "No study material loaded",
        "summary": "",
        "topics": [],
        "flashcards": [],
        "quiz": [],
        "quiz_answers": {},
        "quiz_submitted": False,
        "revision_plan": [],
        "chat_messages": [],
        "user": None,
        "logged_in": False,
        "show_forgot": False,
        "show_otp": False,
        "otp_sent": False,
        "otp_email": "",
        "otp_input": "",
        "reset_otp_sent": False,
        # Progress tracking
        "progress_stage": "Beginner",
        "topics_completed": [],
        "quiz_score": 0,
        "revision_completed": 0,
    }

    for key, value in defaults.items():
        st.session_state.setdefault(key, value)

def pdf_text(file):
    """Extract text from uploaded PDF"""
    return "\n".join(page.extract_text() or "" for page in PdfReader(file).pages)

def topics_from(text, limit=10):
    """Extract topics from text using regex and word frequency"""
    headings = re.findall(r"(?m)^\s*(?:\d+[.)]\s*)?([A-Z][A-Za-z0-9 ,/&()-]{3,70})\s*$", text)
    words = re.findall(r"[A-Za-z][A-Za-z-]{3,}", text.lower())
    ranked = [w.title() for w, _ in Counter(w for w in words if w not in STOP_WORDS).most_common(limit * 2)]
    result = []
    for item in headings + ranked:
        if item.lower() not in [x.lower() for x in result]:
            result.append(clean_text(item))
        if len(result) >= limit:
            break
    return result

def meaning(topic, text):
    """Find the sentence that contains the topic"""
    matches = [s for s in split_sentences(text) if topic.lower() in s.lower()]
    return matches[0] if matches else f"Review the parts of your notes that discuss {topic}."

def summary_from(text):
    """Generate a quick summary using extracted themes and first few sentences"""
    sentences = split_sentences(text)[:5]
    themes = topics_from(text, 6)
    return "**Key themes:** " + ", ".join(themes) + "\n\n" + "\n".join(f"- {s}" for s in sentences)

def load_material(text, name):
    """Load study material into session state"""
    text = clean_text(text)
    if not text:
        st.warning("I could not find readable text in that material.")
        return
    st.session_state.notes_text = text
    st.session_state.notes_name = name
    st.session_state.topics = topics_from(text)
    st.session_state.summary = summary_from(text)
    st.session_state.flashcards = []
    st.session_state.quiz = []
    st.session_state.quiz_answers = {}
    st.session_state.quiz_submitted = False
    st.session_state.revision_plan = []
    st.success(f"Loaded {name} — {len(text):,} characters ready to study.")

def update_progress():

    topics = len(st.session_state.topics)
    flashcards = len(st.session_state.flashcards)
    score = st.session_state.quiz_score
    revision = st.session_state.revision_completed


    if score >= 80 and revision >= 5:
        stage = "Mastered 🟣"

    elif score >= 50 or revision >= 2:
        stage = "Practicing 🔵"

    elif flashcards > 0 or topics > 0:
        stage = "Learning 🟡"

    else:
        stage = "Beginner 🟢"


    st.session_state.progress_stage = stage
# Initialize session state
init_state()

st.markdown(
"""
<style>

.login-card {

    background:#1e1e26;
    padding:40px;
    border-radius:20px;
    width:450px;
    margin:auto;
    box-shadow:0 8px 30px rgba(0,0,0,0.4);

}

.st-key-forgot_password button {
    background: transparent;
    border: 1px solid #6c7cff;
    border-radius: 999px;
    color: #aeb8ff;
    font-size: 0.65rem;
    font-weight: 600;
    min-height: 1.35rem;
    padding: 0 0.35rem;
    transform: scale(0.84);
    transform-origin: right center;
}

.st-key-forgot_password button:hover {
    background: rgba(108, 124, 255, 0.14);
    border-color: #9aa7ff;
    color: #ffffff;
}

</style>
""",
unsafe_allow_html=True
)

def auth_page():

    st.markdown(
        """
        <h1 style="text-align:center;">
        📚 Study Buddy
        </h1>
        """,
        unsafe_allow_html=True
    )


    left, center, right = st.columns(
        [1,2,1]
    )


    with center:


        tab1, tab2 = st.tabs(
            [
                "Login",
                "Register"
            ]
        )


        # ---------------- LOGIN ----------------

        with tab1:


            email = st.text_input(
                "Email",
                key="login_email"
            )


            password = st.text_input(
                "Password",
                type="password",
                key="login_password"
            )

            # Primary and recovery actions share one compact, spaced row.
            login_column, _, forgot_column = st.columns([1, 1.6, 1])
            with login_column:
                if st.button("Login", key="login_button"):
                    success, result = login_user(email, password)
                    if success:
                        st.session_state.logged_in = True
                        st.session_state.user = result
                        st.rerun()
                    else:
                        st.error(result)

            with forgot_column:
                if st.button("Forgot password?", key="forgot_password"):
                    st.session_state.show_forgot = True
                    st.session_state.show_otp = False
                    st.session_state.reset_otp_sent = False



            st.divider()



            if st.button(
                "🔐 Login with OTP",
                use_container_width=True
            ):

                st.session_state.show_otp=True



            if st.session_state.show_otp:


                otp_email = st.text_input(
                    "Email",
                    key="otp_email"
                )


                if st.button(
                    "Send OTP",
                    key="send_otp"
                ):


                    success,msg = send_login_otp(
                        otp_email
                    )


                    if success:

                        st.session_state.otp_sent=True

                        st.success(
                            msg
                        )

                    else:

                        st.error(msg)



                if st.session_state.otp_sent:


                    otp = st.text_input(
                        "Enter OTP",
                        key="otp_input"
                    )


                    if st.button(
                        "Verify OTP",
                        key="verify_otp"
                    ):


                        verified = verify_otp(
                            otp_email,
                            otp
                        )


                        if verified:


                            db = SessionLocal()


                            user = db.query(User).filter(
                                User.email==otp_email
                            ).first()


                            db.close()



                            st.session_state.logged_in=True

                            st.session_state.user=user


                            st.success(
                                "OTP Login Successful"
                            )


                            st.rerun()


                        else:

                            st.error(
                                "Invalid OTP"
                            )



            if st.session_state.show_forgot:


                reset_email = st.text_input(
                    "Registered email",
                    key="reset_email"
                )

                if st.button("Send reset code", key="send_reset_code"):
                    success, msg = send_password_reset_otp(reset_email)
                    if success:
                        st.session_state.reset_otp_sent = True
                        st.success(msg)
                    else:
                        st.error(msg)

                if st.session_state.reset_otp_sent:
                    reset_code = st.text_input(
                        "Reset code",
                        max_chars=6,
                        key="reset_code",
                    )
                    new_password = st.text_input(
                        "New password (8+ characters, including a letter and number)",
                        type="password",
                        key="new_password"
                    )
                    confirm = st.text_input(
                        "Confirm new password",
                        type="password",
                        key="confirm_password"
                    )

                    if st.button("Update password", key="update_password"):
                        if new_password != confirm:
                            st.error("Passwords do not match.")
                        else:
                            success, msg = reset_password(
                                reset_email, reset_code, new_password
                            )
                            if success:
                                st.session_state.reset_otp_sent = False
                                st.session_state.show_forgot = False
                                st.success(msg)
                            else:
                                st.error(msg)




        # ---------------- REGISTER ----------------


        with tab2:


            name = st.text_input(
                "Name"
            )


            email = st.text_input(
                "Email",
                key="register_email"
            )


            password = st.text_input(
                "Password",
                type="password",
                key="register_password"
            )



            if st.button(
                "Create Account",
                use_container_width=True
            ):


                success,msg = register_user(
                    name,
                    email,
                    password
                )


                if success:

                    st.success(msg)

                else:

                    st.error(msg)




init_state()



if not st.session_state.logged_in:

    auth_page()

    st.stop()
           
# Sidebar
with st.sidebar:

    st.title("📚 Study Buddy")

    if st.session_state.user:
        st.write(
            f"👋 {st.session_state.user.name}"
        )


    if st.button("Logout"):

        st.session_state.logged_in = False
        st.session_state.user = None
        st.rerun()


    st.divider()

    st.caption(
        "Learn from your own notes, one active-recall step at a time."
    )

    st.badge(
        "Local-first",
        icon=":material/lock:",
        color="green"
    )


    # Study material upload
    st.subheader("📖 Study Material")


    upload = st.file_uploader(
        "Upload notes or a PDF",
        type=["pdf", "txt"]
    )


    if upload:

        if st.button(
            "Load uploaded material",
            icon=":material/upload_file:"
        ):

            try:

                if upload.name.lower().endswith(".pdf"):

                    text = pdf_text(upload)

                else:

                    text = upload.getvalue().decode(
                        "utf-8",
                        errors="ignore"
                    )


                load_material(
                    text,
                    upload.name
                )


            except Exception as exc:

                st.error(
                    f"File reading error: {exc}"
                )


    st.divider()


    pasted = st.text_area(
        "Paste your notes",
        height=150,
        placeholder="Paste chapter notes here..."
    )


    if st.button(
        "Use pasted notes",
        icon=":material/content_paste:"
    ):

        load_material(
            pasted,
            "Pasted Notes"
        )



    if st.button(
        "Try Demo Lesson",
        icon=":material/play_circle:"
    ):

        if DEMO_NOTES.exists():

            load_material(
                DEMO_NOTES.read_text(
                    encoding="utf-8"
                ),
                "Demo: Cell Biology"
            )

        else:

            st.error(
                "Demo file missing"
            )


    st.divider()


    st.caption(
        f"Current material: {st.session_state.notes_name}"
    )


    if st.button(
        "Clear Study Session",
        icon=":material/delete:"
    ):

        st.session_state.notes_text = ""
        st.session_state.notes_name = "No study material loaded"
        st.session_state.summary = ""
        st.session_state.topics = []
        st.session_state.flashcards = []
        st.session_state.quiz = []

        st.rerun()
# Main content
st.title("Your focused study space")
st.write("Upload a PDF, paste notes, or open the demo lesson. Study Buddy turns it into summaries, recall practice, quizzes, flashcards, and a revision plan.")

# Metrics
a, b, c = st.columns(3)
a.metric("Material", "Ready" if st.session_state.notes_text else "Waiting")
b.metric("Topics found", len(st.session_state.topics))
c.metric("Flashcards", len(st.session_state.flashcards))

# Progress Section

update_progress()

st.subheader("📈 Learning Progress")

p1, p2, p3 = st.columns(3)


p1.metric(
    "Current Stage",
    st.session_state.progress_stage
)


p2.metric(
    "Topics",
    len(st.session_state.topics)
)


p3.metric(
    "Quiz Score",
    f"{st.session_state.quiz_score}%"
)

# Tabs
learn, quiz_tab, cards, plan, progress, coach = st.tabs([
    "📖 Learn",
    "📝 Quiz",
    "🗂 Flashcards",
    "📅 Plan",
    "📈 Progress",
    "💬 Coach"
])

with learn:
    if not st.session_state.notes_text:
        st.info("Start by loading material from the sidebar. The built-in demo lesson lets you test the full app right away.", icon=":material/lightbulb:")
    else:
        left, right = st.columns([3, 2])
        with left:
            st.subheader("Smart summary")
            st.markdown(st.session_state.summary)
        with right:
            st.subheader("Key topics")
            for topic in st.session_state.topics[:8]:
                st.badge(topic, icon=":material/sell:", color="blue")
        with st.expander("Read the source notes", icon=":material/description:"):
            st.write(st.session_state.notes_text)

with quiz_tab:

    st.subheader("📝 Test your recall")


    count = st.slider(
        "Questions",
        3,
        10,
        5
    )


    difficulty = st.selectbox(
        "Difficulty",
        [
            "Easy",
            "Medium",
            "Hard"
        ]
    )


    # Generate quiz

    if st.button(
        "Generate Quiz",
        type="primary"
    ):


        if not st.session_state.notes_text:

            st.warning(
                "Load study material first."
            )

        else:

            with st.spinner(
                "Creating quiz..."
            ):

                quiz = generate_quiz(
                    count,
                    difficulty
                )


                if quiz:

                    st.session_state.quiz = quiz
                    st.session_state.quiz_answers = {}
                    st.session_state.quiz_submitted = False

                    st.success(
                        "Quiz created!"
                    )

                    st.rerun()

                else:

                    st.error(
                        "Could not create quiz."
                    )



    # Display quiz


    if st.session_state.quiz:


        st.divider()

        st.subheader(
            "Answer the questions"
        )


        with st.form(
            "quiz_form"
        ):

            answers = {}


            for i, q in enumerate(
                st.session_state.quiz
            ):

                st.write(
                    f"**{i+1}. {q['question']}**"
                )


                answers[i] = st.radio(
                    "Choose answer:",
                    q["options"],
                    key=f"quiz_{i}"
                )


            submitted = st.form_submit_button(
                "Submit Quiz"
            )



        if submitted:


            score = 0


            total = len(
                st.session_state.quiz
            )


            for i, q in enumerate(
                st.session_state.quiz
            ):

                if answers[i] == q["answer"]:
                    score += 1



            percentage = int(
                (score / total) * 100
            )


            st.session_state.quiz_score = percentage


            st.success(
                f"""
🎉 Quiz Completed!

Score: {score}/{total}

Percentage: {percentage}%
"""
            )


            # Progress update

            if percentage >= 80:

                st.session_state.revision_completed += 1


            update_progress()



            # Show answers

            with st.expander(
                "See correct answers"
            ):

                for q in st.session_state.quiz:

                    st.write(
                        "Question:",
                        q["question"]
                    )

                    st.write(
                        "Correct answer:",
                        q["answer"]
                    )
    with cards:
        st.subheader("Flashcards for Active Recall")

        amount = st.slider("Cards", 4, 12, 8)

        if st.button(
            "Generate Flashcards",
            type="primary",
            icon=":material/style:",
        ):

            if not st.session_state.notes_text:
                st.warning("Load study material first.")

            else:

                with st.spinner("Generating flashcards..."):

                    response = process_query(
                        f"""
    Generate {amount} flashcards.

    Format:

    Q:
    A:

    Only use the uploaded study notes.
    """
                    )

                    
                    st.session_state.flashcards.append(response)
                    update_progress()
                    st.markdown(response)
                    
with plan:
    st.subheader("Revision Planner")

    days = st.slider(
        "Plan Length (days)",
        3,
        14,
        7,
    )

    if st.button(
        "Build My Study Plan",
        type="primary",
        icon=":material/calendar_add_on:",
    ):

        if not st.session_state.notes_text:
            st.warning("Load study material first.")

        else:

            with st.spinner("Creating revision plan..."):

                response = process_query(
                    f"""
Create a {days}-day revision plan.

Only use the uploaded notes.

Return the plan day by day.
"""
                )

                st.markdown(response)
                
with progress:

    st.subheader("📈 Your Learning Journey")


    stages = [
        "Beginner 🟢",
        "Learning 🟡",
        "Practicing 🔵",
        "Mastered 🟣"
    ]


    current = st.session_state.progress_stage


    for stage in stages:

        if stage == current:
            st.success(
                f"➡️ {stage} (Current Stage)"
            )

        else:
            st.write(stage)


    st.divider()


    st.write(
        f"""
        **Topics discovered:** {len(st.session_state.topics)}

        **Flashcards created:** {len(st.session_state.flashcards)}

        **Quiz performance:** {st.session_state.quiz_score}%

        **Revision sessions completed:** {st.session_state.revision_completed}
        """
    )
    
with coach:
    st.subheader("Ask your Study Coach")
    st.caption(
        "Try asking: 'summarize this', 'what are the topics?', "
        "'explain photosynthesis', or 'quiz me on chapter 3'."
    )

    # Display previous chat messages
    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Chat input
    prompt = st.chat_input("Ask about your study material...")

    if prompt:
        # Show user message
        st.session_state.chat_messages.append(
            {"role": "user", "content": prompt}
        )

        with st.chat_message("user"):
            st.markdown(prompt)

        # Generate AI response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    response = process_query(
                        query=prompt,
                        chat_history=st.session_state.chat_messages[:-1]
                    )
                except Exception:
                    response = get_coach_response(prompt)

                st.markdown(response)

        # Save assistant response
        st.session_state.chat_messages.append(
            {"role": "assistant", "content": response}
        )

        st.rerun()
