import streamlit as st
from langchain_core.tools import tool
from config import get_llm
from utils import safe_json_extract, truncate_text, get_notes_context

def notes_context(limit=12000):
    return truncate_text(st.session_state.notes_text, limit)

@tool
def read_pdf(dummy: str = "") -> str:
    """
    Return the content of uploaded PDF/notes.
    Use this when asked about the material or to reference specific content.
    """
    if not st.session_state.notes_text:
        return "No study material has been uploaded yet. Please upload a PDF or paste notes."
    return notes_context()

@tool
def summarize_notes(focus: str = "") -> str:
    """
    Create a summary of the study notes.
    Optionally focus on a specific subtopic.
    """
    if not st.session_state.notes_text:
        return "Please upload study material first."
    
    llm = get_llm(st.session_state.api_key)
    prompt = f"""
    Summarize these study notes.
    {f"Focus on: {focus}" if focus else ""}
    
    NOTES:
    {notes_context()}
    """
    return llm.invoke(prompt).content

@tool
def extract_topics(dummy: str = "") -> str:
    """
    Extract and list all important topics/concepts from the notes.
    """
    if not st.session_state.notes_text:
        return "Please upload study material first."
    
    llm = get_llm(st.session_state.api_key)
    prompt = f"""
    Extract all important topics and concepts from these notes.
    Return as a JSON array of topic names only.
    
    NOTES:
    {notes_context()}
    """
    raw = llm.invoke(prompt).content
    try:
        topics = safe_json_extract(raw)
        st.session_state.topics = topics
        return ", ".join(topics)
    except:
        return raw

@tool
def generate_quiz(num_questions: int = 5, difficulty: str = "Medium") -> str:
    """
    Generate a multiple-choice quiz with specified number of questions and difficulty.
    Options: Easy, Medium, Hard
    """
    if not st.session_state.notes_text:
        return "Please upload study material first."
    
    llm = get_llm(st.session_state.api_key)
    prompt = f"""
    Generate {num_questions} multiple-choice questions at {difficulty} difficulty level.
    Return as JSON array with question, options, answer (A, B, C, D), and explanation.
    
    Format:
    [
      {{
        "question": "What is...",
        "options": ["A) ...", "B) ...", "C) ...", "D) ..."],
        "answer": "A",
        "explanation": "Because..."
      }}
    ]
    
    NOTES:
    {notes_context()}
    """
    raw = llm.invoke(prompt).content
    quiz = safe_json_extract(raw)
    st.session_state.quiz = quiz
    st.session_state.quiz_answers = {}
    st.session_state.quiz_submitted = False
    return f"Generated {len(quiz)} questions at {difficulty} difficulty. Check the Quiz tab!"

@tool
def evaluate_answers(answers: dict) -> str:
    """
    Evaluate quiz answers and provide feedback.
    """
    if not st.session_state.get('quiz'):
        return "No quiz available to evaluate. Please generate a quiz first."
    
    correct = 0
    total = len(st.session_state.quiz)
    feedback = []
    
    for i, q in enumerate(st.session_state.quiz):
        user_answer = answers.get(f'q{i}', '')
        is_correct = user_answer == q['answer']
        if is_correct:
            correct += 1
        feedback.append(f"Q{i+1}: {'✅ Correct' if is_correct else f'❌ Incorrect. Correct answer: {q["answer"]}'}\n{q['explanation']}")
    
    return f"Score: {correct}/{total}\n\n" + "\n\n".join(feedback)

@tool
def generate_flashcards(num_cards: int = 8) -> str:
    """
    Generate flashcards with front/back for active recall practice.
    """
    if not st.session_state.notes_text:
        return "Please upload study material first."
    
    llm = get_llm(st.session_state.api_key)
    prompt = f"""
    Create {num_cards} flashcards for active recall.
    Each flashcard should have a front (question/prompt) and back (answer).
    Return as JSON array.
    
    Format:
    [
      {{"front": "What is...", "back": "It is..."}}
    ]
    
    NOTES:
    {notes_context()}
    """
    raw = llm.invoke(prompt).content
    flashcards = safe_json_extract(raw)
    st.session_state.flashcards = flashcards
    return f"Generated {len(flashcards)} flashcards. Check the Flashcards tab!"

@tool
def revision_planner(days: int = 7) -> str:
    """
    Create a day-by-day revision schedule.
    """
    from datetime import date, timedelta
    
    if not st.session_state.notes_text:
        return "Please upload study material first."
    
    if not st.session_state.get('topics'):
        extract_topics.invoke({})
    
    topics = st.session_state.topics
    if not topics:
        return "No topics available for planning."
    
    plan = []
    for i in range(min(days, 14)):
        study_date = date.today() + timedelta(days=i)
        topic = topics[i % len(topics)]
        plan.append({
            'date': study_date.strftime('%A, %d %B'),
            'topic': topic,
            'suggestion': '25 min study + 5 min recall without notes'
        })
    
    st.session_state.revision_plan = plan
    return f"Created {len(plan)}-day revision plan. Check the Plan tab!"

@tool
def explain_concept(concept: str) -> str:
    """
    Explain a specific concept in simple terms with an analogy.
    """
    if not st.session_state.notes_text:
        return "Please upload study material first."
    
    llm = get_llm(st.session_state.api_key)
    prompt = f"""
    Explain "{concept}" in simple terms with an analogy.
    Base your explanation on the study material.
    
    NOTES:
    {notes_context()}
    """
    return llm.invoke(prompt).content
