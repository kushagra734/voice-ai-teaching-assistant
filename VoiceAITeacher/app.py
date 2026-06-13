"""Streamlit web app — Voice AI Teaching Assistant (CDF Option A)."""

import html
import io
import os
import re
import time
from datetime import datetime

import streamlit as st
from dotenv import load_dotenv

load_dotenv()
try:
    if "GEMINI_API_KEY" in st.secrets:
        os.environ["GEMINI_API_KEY"] = st.secrets["GEMINI_API_KEY"]
except Exception:
    pass

from ai_engine import GeminiEngine
from prompts import LANG_ENGLISH, LANG_HINDI, LANG_HINGLISH
from quiz_parser import QuizParser
from speech_to_text import SpeechEngine
from study_resources import StudyResourceFetcher

# ── Theme colors (match CustomTkinter app) ──
COLOR_BG = "#0c0f1a"
COLOR_CARD = "#1a2236"
COLOR_PURPLE = "#7c3aed"
COLOR_TEXT_MUTED = "#94a3b8"

LANG_MAP = {"English": LANG_ENGLISH, "Hindi": LANG_HINDI, "Hinglish": LANG_HINGLISH}
LANG_LABELS = list(LANG_MAP.keys())

QUICK_TOPICS = ["Photosynthesis", "Water Cycle", "Indian Constitution", "Solar System", "Algebra"]

RESOURCE_DESCRIPTIONS = {
    "Wikipedia (English)": "Read a detailed article in English.",
    "Wikipedia (Hindi)": "हिंदी में विस्तृत जानकारी पढ़ें।",
    "Khan Academy": "Watch free video lessons and practice.",
    "YouTube Lessons": "Find class 6–10 explained videos.",
    "NCERT Notes": "Search NCERT notes and PDFs.",
}


def init_session_state() -> None:
    """Initialize Streamlit session state keys."""
    defaults = {
        "topic": "",
        "language_label": "Hinglish",
        "classroom_mode": True,
        "text_size": 22,
        "voice_slow": False,
        "response_expanded": False,
        "resource_slide": 0,
        "last_output": "",
        "last_mode": "",
        "last_topic": "",
        "parsed_quiz": None,
        "quiz_answers": {},
        "quiz_submitted": False,
        "elapsed": 0.0,
        "history": [],
        "tts_audio": None,
        "tts_error": "",
        "tts_version": 0,
        "speak_requested": False,
        "status_msg": "Ready",
        "last_audio_id": None,
        "last_heard": "",
        "voice_topic": "",
        "pending_clear": False,
        "pending_topic": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def apply_custom_css(text_size: int, classroom: bool) -> None:
    """Inject dashboard styling to match the desktop app."""
    body_size = text_size if classroom else 16
    st.markdown(
        f"""
        <style>
        .stApp {{ background-color: {COLOR_BG}; }}
        div[data-testid="stSidebar"] {{
            background: #111827;
            border-right: 1px solid #2a3550;
        }}
        .main-header {{
            font-size: 1.85rem;
            font-weight: 700;
            color: #f8fafc;
            margin: 0 0 0.15rem 0;
        }}
        .sub-header {{
            color: {COLOR_TEXT_MUTED};
            font-size: 0.95rem;
            margin-bottom: 1.2rem;
        }}
        .stat-card {{
            background: {COLOR_CARD};
            border: 1px solid #2a3550;
            border-radius: 14px;
            padding: 0.9rem 0.5rem;
            text-align: center;
            min-height: 88px;
        }}
        .stat-icon {{ font-size: 1.4rem; }}
        .stat-value {{
            font-size: 1.55rem;
            font-weight: 700;
            color: {COLOR_PURPLE};
            margin: 0.2rem 0;
        }}
        .stat-label {{
            color: {COLOR_TEXT_MUTED};
            font-size: 0.72rem;
        }}
        .panel-card {{
            background: #151c2e;
            border: 1px solid #2a3550;
            border-radius: 16px;
            padding: 1rem 1.1rem;
            margin-bottom: 0.75rem;
        }}
        .panel-title {{
            font-size: 1rem;
            font-weight: 700;
            color: #f8fafc;
            margin-bottom: 0.75rem;
        }}
        .output-box {{
            background: #0f1524;
            border: 1px solid #2a3550;
            border-radius: 12px;
            padding: 1.25rem 1.35rem;
            font-size: {body_size}px;
            line-height: 1.65;
            white-space: pre-wrap;
            color: #f8fafc;
            min-height: 280px;
            max-height: 520px;
            overflow-y: auto;
        }}
        .resource-slide {{
            background: {COLOR_CARD};
            border: 1px solid #2a3550;
            border-radius: 12px;
            padding: 1.5rem 1rem;
            text-align: center;
            min-height: 200px;
        }}
        .resource-icon {{ font-size: 2.4rem; margin-bottom: 0.5rem; }}
        .mic-label {{
            text-align: center;
            color: {COLOR_TEXT_MUTED};
            font-size: 0.85rem;
            font-weight: 600;
            margin-bottom: 0.5rem;
        }}
        div[data-testid="stAudioInput"] {{
            border: 2px dashed {COLOR_PURPLE} !important;
            border-radius: 16px !important;
            padding: 0.85rem !important;
            background: linear-gradient(145deg, #1a1040, #151c2e) !important;
            min-height: 88px !important;
            margin: 0 auto !important;
        }}
        div[data-testid="stAudioInput"] label {{
            font-size: 1rem !important;
            font-weight: 700 !important;
            color: #e9d5ff !important;
        }}
        .stButton > button[kind="primary"] {{
            background: {COLOR_PURPLE} !important;
            border: none !important;
            font-weight: 700 !important;
            height: 3rem !important;
        }}
        .quiz-q {{
            font-size: {max(16, body_size - 2)}px;
            font-weight: 700;
            margin: 1rem 0 0.5rem 0;
        }}
        #MainMenu, footer {{ visibility: hidden; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def apply_pending_input_updates() -> None:
    """Apply topic changes before widgets render (avoids Streamlit widget key errors)."""
    if st.session_state.pop("pending_clear", False):
        st.session_state.topic = ""
        st.session_state.last_heard = ""
        st.session_state.voice_topic = ""
        st.session_state.last_audio_id = None
        st.session_state.last_output = ""
        st.session_state.parsed_quiz = None
        st.session_state.tts_audio = None
        st.session_state.tts_error = ""

    pending_topic = st.session_state.pop("pending_topic", None)
    if pending_topic is not None:
        st.session_state.topic = pending_topic
        st.session_state.last_heard = ""
        st.session_state.voice_topic = ""


def transcribe_audio(audio_bytes: bytes) -> tuple:
    """Transcribe browser-recorded audio."""
    import speech_recognition as sr

    try:
        recognizer = sr.Recognizer()
        # Streamlit audio_input returns WAV bytes
        with sr.AudioFile(io.BytesIO(audio_bytes)) as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.2)
            audio = recognizer.record(source)
        text = recognizer.recognize_google(audio, language="en-IN")
        return text.strip(), ""
    except sr.UnknownValueError:
        return "", "Could not understand speech. Please speak clearly and try again."
    except sr.RequestError:
        return "", "Speech service unavailable. Please type your topic."
    except Exception:
        return "", "Could not process audio. Please type your topic."


def _pick_tts_lang(text: str, language: str) -> str:
    """Pick gTTS language code from output language and script in text."""
    if language == LANG_HINDI:
        return "hi"
    if re.search(r"[\u0900-\u097F]", text):
        return "hi"
    return "en"


def _excerpt_for_speech(text: str, max_chars: int = 650) -> str:
    """Use the opening section for TTS so Google speech API responds faster."""
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if paragraphs:
        excerpt = paragraphs[0]
        if len(paragraphs) > 1 and len(excerpt) < max_chars:
            excerpt = f"{excerpt}\n\n{paragraphs[1]}"
    else:
        excerpt = text.strip()

    excerpt = re.sub(r"[📚🔑📝⭐🎯✅🔊💡═→•]", " ", excerpt)
    excerpt = " ".join(excerpt.split())
    if len(excerpt) > max_chars:
        excerpt = excerpt[:max_chars].rsplit(" ", 1)[0] + "."
    return excerpt


def generate_tts_audio(text: str, language: str, slow: bool = False) -> tuple:
    """
    Generate MP3 bytes for read-aloud.

    Returns:
        Tuple of (audio_bytes or None, error_message).
    """
    try:
        from gtts import gTTS

        cleaned = _excerpt_for_speech(text)
        if not cleaned:
            return None, "Nothing to read aloud."

        lang_code = _pick_tts_lang(cleaned, language)
        tts = gTTS(text=cleaned, lang=lang_code, slow=slow)
        buffer = io.BytesIO()
        tts.write_to_fp(buffer)
        buffer.seek(0)
        return buffer.read(), ""
    except Exception as exc:
        return None, f"Could not generate speech: {exc}"


def request_read_aloud(text: str, language: str) -> None:
    """Generate TTS and store in session so it survives Streamlit reruns."""
    audio_bytes, err = generate_tts_audio(text, language, st.session_state.voice_slow)
    if err:
        st.session_state.tts_audio = None
        st.session_state.tts_error = err
        st.session_state.status_msg = "Speech failed"
    else:
        st.session_state.tts_audio = audio_bytes
        st.session_state.tts_error = ""
        st.session_state.tts_version += 1
        st.session_state.status_msg = "Ready — press ▶ Play below (reads opening section)"


def process_pending_speech(language: str) -> None:
    """Run TTS once at page top so the spinner does not block the whole UI."""
    if not st.session_state.speak_requested or not st.session_state.last_output:
        return

    st.session_state.speak_requested = False
    with st.spinner("Preparing read-aloud audio... Please wait 10–20 seconds."):
        request_read_aloud(st.session_state.last_output, language)


def process_voice_input(audio_bytes: bytes, speech_engine: SpeechEngine) -> None:
    """Transcribe mic audio and sync into the single topic text field."""
    audio_id = hash(audio_bytes)
    if st.session_state.last_audio_id == audio_id:
        return

    st.session_state.last_audio_id = audio_id
    text, err = transcribe_audio(audio_bytes)
    if not text:
        if err:
            st.info(err)
        else:
            st.info("No speech detected. Try again or type your topic.")
        return

    _, extracted = speech_engine.detect_intent(text)
    heard_topic = (extracted or text).strip()
    st.session_state.topic = heard_topic
    st.session_state.last_heard = text.strip()
    st.session_state.voice_topic = heard_topic
    st.rerun()


def get_active_topic() -> str:
    """Return the current topic."""
    return st.session_state.topic.strip()


def render_output(text: str) -> None:
    """Render AI explanation text."""
    safe_text = html.escape(text)
    st.markdown(f'<div class="output-box">{safe_text}</div>', unsafe_allow_html=True)


def render_resource_carousel(topic: str) -> None:
    """Render study links as a carousel like the desktop app."""
    if not topic:
        st.markdown(
            '<div class="resource-slide">'
            '<div class="resource-icon">📚</div>'
            '<strong>Study Resources</strong><br>'
            '<span style="color:#94a3b8;">Generate a topic to see helpful study links here.</span>'
            "</div>",
            unsafe_allow_html=True,
        )
        return

    resources = StudyResourceFetcher().fetch_links(topic)
    slides = [
        {
            "icon": link.icon,
            "title": link.title,
            "desc": RESOURCE_DESCRIPTIONS.get(link.title, link.title),
            "url": link.url,
        }
        for link in resources.links
    ]

    if not slides:
        return

    idx = st.session_state.resource_slide % len(slides)
    slide = slides[idx]

    st.markdown(
        f'<div class="resource-slide">'
        f'<div class="resource-icon">{slide["icon"]}</div>'
        f'<strong>{html.escape(slide["title"])}</strong><br>'
        f'<span style="color:#94a3b8;font-size:0.85rem;">{html.escape(slide["desc"])}</span>'
        f"</div>",
        unsafe_allow_html=True,
    )

    nav1, nav2, nav3 = st.columns([1, 2, 1])
    with nav1:
        if st.button("◀", key="res_prev", use_container_width=True):
            st.session_state.resource_slide = (idx - 1) % len(slides)
            st.rerun()
    with nav2:
        dots = " ".join("●" if i == idx else "○" for i in range(len(slides)))
        st.markdown(f"<div style='text-align:center;color:#8b5cf6;'>{dots}</div>", unsafe_allow_html=True)
    with nav3:
        if st.button("▶", key="res_next", use_container_width=True):
            st.session_state.resource_slide = (idx + 1) % len(slides)
            st.rerun()

    st.link_button("Open Resource  →", slide["url"], use_container_width=True, key="open_resource_btn")


def render_interactive_quiz(parsed, text_size: int) -> None:
    """Render clickable quiz with submit and scoring."""
    parser = QuizParser()
    q_size = max(16, text_size - 2)
    st.markdown(
        f'<p class="quiz-q">📝 Interactive Quiz — {html.escape(parsed.topic)}</p>',
        unsafe_allow_html=True,
    )

    for question in parsed.questions:
        st.markdown(f"**Q{question.number}.** {question.text}")
        options = list(question.options.items()) or [
            ("A", "Option A"), ("B", "Option B"), ("C", "Option C"), ("D", "Option D"),
        ]
        labels = [f"{letter}) {text}" for letter, text in options]
        letters = [letter for letter, _ in options]
        current = st.session_state.quiz_answers.get(question.number)
        index = letters.index(current) if current in letters else None

        choice = st.radio(
            f"Answer Q{question.number}",
            labels,
            index=index,
            key=f"quiz_q_{question.number}",
            disabled=st.session_state.quiz_submitted,
            label_visibility="collapsed",
        )
        if choice:
            st.session_state.quiz_answers[question.number] = choice[0]

    if not st.session_state.quiz_submitted:
        total = len(parsed.questions)
        answered = len(st.session_state.quiz_answers)
        st.caption(f"Answered: {answered}/{total}")
        if st.button("✅ Submit Quiz", type="primary", disabled=answered < total, key="submit_quiz_btn"):
            score = sum(
                1 for q in parsed.questions
                if st.session_state.quiz_answers.get(q.number) == q.correct
            )
            pct = round((score / total) * 100) if total else 0
            st.session_state.quiz_submitted = True
            st.session_state.status_msg = f"Quiz submitted — {score}/{total}"
            msg = "Bahut accha! Great job!" if pct >= 60 else "Practice karo, phir try karo!"
            st.success(f"Score: {score}/{total} ({pct}%) — {msg}")
    else:
        for q in parsed.questions:
            sel = st.session_state.quiz_answers.get(q.number, "")
            if sel == q.correct:
                st.markdown(f"Q{q.number}: ✅ Correct ({q.correct})")
            else:
                st.markdown(f"Q{q.number}: ❌ Your answer: {sel} | Correct: {q.correct}")
        st.download_button(
            "💾 Download Quiz",
            parser.to_display_text(parsed, include_answers=True),
            file_name=f"quiz_{parsed.topic.replace(' ', '_')}.txt",
            key="download_quiz_btn",
        )


def render_stats() -> None:
    """Weekly-style stats row."""
    hist = st.session_state.history
    sessions = len(hist)
    quizzes = sum(1 for h in hist if h["type"] == "quiz")
    topics = len({h["topic"] for h in hist})
    engagement = min(topics * 4 + sessions, 99) if hist else 0

    stats = [
        ("📚", str(sessions), "Sessions This Week"),
        ("📝", str(quizzes), "Quizzes Created"),
        ("👥", str(engagement), "Students Engaged"),
        ("🏆", "—", "Avg. Score"),
    ]
    cols = st.columns(4)
    for col, (icon, val, label) in zip(cols, stats):
        col.markdown(
            f'<div class="stat-card">'
            f'<div class="stat-icon">{icon}</div>'
            f'<div class="stat-value">{val}</div>'
            f'<div class="stat-label">{label}</div>'
            f"</div>",
            unsafe_allow_html=True,
        )


def render_input_card(engine: GeminiEngine, speech_engine: SpeechEngine, quiz_parser: QuizParser) -> None:
    """Input section — one shared topic field for typing and voice."""
    st.markdown('<div class="panel-title">What shall we learn today?</div>', unsafe_allow_html=True)
    apply_pending_input_updates()

    mic_col, input_col, action_col = st.columns([1.1, 3.2, 1.3])

    with mic_col:
        st.markdown('<div class="mic-label">🎤 Voice Input</div>', unsafe_allow_html=True)
        audio = st.audio_input("Click to Speak", key="voice_input")
        if audio is not None:
            process_voice_input(audio.getvalue(), speech_engine)

    with input_col:
        topic = st.text_input(
            "Topic",
            value=st.session_state.topic,
            placeholder="Type or speak your topic here... Example: Photosynthesis, Quadratic Equations, Water Cycle",
            label_visibility="collapsed",
        )
        st.session_state.topic = topic.strip()

        if (
            st.session_state.last_heard
            and st.session_state.get("voice_topic") == topic.strip()
        ):
            st.caption(f"🎤 Heard: {st.session_state.last_heard}")

        util1, util2, _ = st.columns([1, 1, 2])
        with util1:
            if st.button("🗑️ Clear", use_container_width=True, key="btn_clear"):
                st.session_state.pending_clear = True
                st.rerun()
        with util2:
            if st.button("📋 Paste", use_container_width=True, key="btn_paste"):
                st.info("Use Ctrl+V in the topic field above.")

        lang = st.radio(
            "Output Language:",
            LANG_LABELS,
            index=LANG_LABELS.index(st.session_state.language_label),
            horizontal=True,
            key="lang_radio",
        )
        st.session_state.language_label = lang

    with action_col:
        explain = st.button("✨ Explain Concept", type="primary", use_container_width=True, key="btn_explain")
        quiz = st.button("📝 Generate Quiz", use_container_width=True, key="btn_quiz")

    language = LANG_MAP[st.session_state.language_label]
    active_topic = get_active_topic()

    if explain or quiz:
        if not active_topic:
            st.error("Please enter or speak a topic first.")
        elif not engine.is_configured:
            st.error("Gemini API key not configured. Add GEMINI_API_KEY to .env or Streamlit Secrets.")
        else:
            with st.spinner("Generating with Gemini AI..."):
                start = time.time()
                if quiz:
                    _, extracted = speech_engine.detect_intent(active_topic)
                    use_topic = extracted or active_topic
                    output = engine.generate_quiz(use_topic, language)
                    mode = "quiz"
                else:
                    use_topic = active_topic
                    output = engine.explain_concept(use_topic, language)
                    mode = "explain"
                elapsed = time.time() - start

            st.session_state.last_output = output
            st.session_state.last_mode = mode
            st.session_state.last_topic = use_topic
            st.session_state.elapsed = elapsed
            st.session_state.quiz_answers = {}
            st.session_state.quiz_submitted = False
            st.session_state.tts_audio = None
            st.session_state.tts_error = ""
            st.session_state.resource_slide = 0
            st.session_state.parsed_quiz = quiz_parser.parse(output) if mode == "quiz" else None
            st.session_state.history.insert(0, {
                "topic": use_topic, "type": mode, "time": datetime.now().strftime("%H:%M"),
            })
            st.session_state.status_msg = "Done ✓"


def render_response_panel(language: str) -> None:
    """Left panel — AI response with size controls and expand."""
    st.markdown('<div class="panel-title">🤖 AI Teaching Assistant Response</div>', unsafe_allow_html=True)

    ctrl1, ctrl2, ctrl3, ctrl4, ctrl5 = st.columns([0.7, 0.7, 0.8, 1.2, 1.2])
    with ctrl1:
        if st.button("A−", key="size_down", use_container_width=True):
            st.session_state.text_size = max(12, st.session_state.text_size - 2)
            st.rerun()
    with ctrl2:
        if st.button("A+", key="size_up", use_container_width=True):
            st.session_state.text_size = min(34, st.session_state.text_size + 2)
            st.rerun()
    with ctrl3:
        st.markdown(f"**{st.session_state.text_size}**")
    with ctrl4:
        expand_label = "↙ Restore" if st.session_state.response_expanded else "⛶ Expand"
        if st.button(expand_label, key="btn_expand", use_container_width=True):
            st.session_state.response_expanded = not st.session_state.response_expanded
            st.rerun()
    with ctrl5:
        if st.session_state.last_output:
            st.download_button(
                "💾 Save TXT",
                st.session_state.last_output,
                file_name=f"{st.session_state.last_topic.replace(' ', '_')}.txt",
                use_container_width=True,
                key="save_txt_header",
            )

    if st.session_state.last_output:
        if st.session_state.last_mode == "quiz" and st.session_state.parsed_quiz:
            parsed = st.session_state.parsed_quiz
            if parsed.questions:
                render_interactive_quiz(parsed, st.session_state.text_size)
            else:
                render_output(st.session_state.last_output)
        else:
            render_output(st.session_state.last_output)

        words = len(st.session_state.last_output.split())
        st.caption(
            f"Words: {words} | Generated in {st.session_state.elapsed:.1f}s | "
            f"Language: {st.session_state.language_label} | ● Completed"
        )
    else:
        st.info("Waiting for input. Use the microphone or type a topic above to begin your lesson session.")


def render_voice_controls(language: str) -> None:
    """Speak response + voice speed — matches desktop footer."""
    v1, v2, v3, v4 = st.columns([1.4, 1.2, 1, 1])

    with v1:
        if st.button("🔊 Speak Response", type="primary", use_container_width=True, key="speak_btn"):
            if st.session_state.last_output:
                st.session_state.speak_requested = True
                st.rerun()
            else:
                st.session_state.tts_error = "Generate content first."

    with v2:
        st.session_state.voice_slow = st.toggle("Slow speech", value=st.session_state.voice_slow)

    with v3:
        st.markdown(f"**Status:** {st.session_state.status_msg}")

    with v4:
        if st.button("⏹ Stop", use_container_width=True, key="stop_btn"):
            st.session_state.tts_audio = None
            st.session_state.tts_error = ""
            st.session_state.speak_requested = False
            st.session_state.status_msg = "Ready"

    if st.session_state.tts_error:
        st.warning(st.session_state.tts_error)
    if st.session_state.tts_audio:
        st.success("Audio ready — press ▶ Play below")
        st.audio(st.session_state.tts_audio, format="audio/mp3")


def render_quick_actions(language: str) -> None:
    """Quick action buttons grid."""
    st.markdown('<div class="panel-title">Quick Actions</div>', unsafe_allow_html=True)
    qa1, qa2, qa3, qa4 = st.columns(4)

    with qa1:
        if st.button("🔊\nRead Aloud", use_container_width=True, key="qa_speak"):
            if st.session_state.last_output:
                st.session_state.speak_requested = True
                st.rerun()
            else:
                st.session_state.tts_error = "Generate content first."
    with qa2:
        if st.session_state.last_output:
            st.download_button(
                "💾\nSave Output",
                st.session_state.last_output,
                file_name=f"{st.session_state.last_topic.replace(' ', '_')}.txt",
                use_container_width=True,
                key="qa_save",
            )
    with qa3:
        if st.button("📤\nShare", use_container_width=True, key="qa_share"):
            if st.session_state.last_output:
                share = (
                    f"Voice AI Teaching Assistant\n"
                    f"Topic: {st.session_state.last_topic}\n\n"
                    f"{st.session_state.last_output[:2000]}"
                )
                st.code(share, language=None)
                st.caption("Select and copy the text above to share.")
            else:
                st.warning("Generate content first.")
    with qa4:
        if st.button("🔄\nNew Topic", use_container_width=True, key="qa_new"):
            st.session_state.pending_clear = True
            st.rerun()


def main() -> None:
    """Run the Streamlit teaching assistant."""
    st.set_page_config(
        page_title="Voice AI Teaching Assistant",
        page_icon="🎓",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    init_session_state()
    apply_custom_css(st.session_state.text_size, st.session_state.classroom_mode)

    engine = GeminiEngine()
    speech_engine = SpeechEngine()
    quiz_parser = QuizParser()
    language = LANG_MAP[st.session_state.language_label]

    process_pending_speech(language)

    # ── Sidebar ──
    with st.sidebar:
        st.markdown("### 🤖 Voice AI Teaching Assistant")
        st.caption("Connecting Dreams Foundation | Haryana Govt. Schools")
        st.divider()

        st.session_state.classroom_mode = st.toggle(
            "🎓 Classroom Mode", value=st.session_state.classroom_mode
        )
        if st.session_state.classroom_mode:
            st.session_state.text_size = st.slider(
                "Text Size", 14, 34, st.session_state.text_size, 2, key="sidebar_text_size"
            )

        st.divider()
        st.markdown("**Quick Topics**")
        qcols = st.columns(2)
        for i, qt in enumerate(QUICK_TOPICS):
            if qcols[i % 2].button(qt, use_container_width=True, key=f"quick_{qt}"):
                st.session_state.pending_topic = qt
                st.rerun()

        st.divider()
        st.markdown("💡 **Tip for Teachers**")
        st.caption("Use simple, clear questions for better AI responses.")

        if not engine.is_configured:
            st.error("⚠️ GEMINI_API_KEY missing")

    # ── Header ──
    h1, _ = st.columns([4, 1])
    with h1:
        st.markdown('<p class="main-header">👋 Namaste, Teacher!</p>', unsafe_allow_html=True)
        st.markdown(
            '<p class="sub-header">Your AI Co-Pilot for Smarter Teaching and Engaging Classrooms.</p>',
            unsafe_allow_html=True,
        )

    render_stats()

    with st.container(border=True):
        render_input_card(engine, speech_engine, quiz_parser)

    # ── Output: expand hides right panel ──
    if st.session_state.response_expanded:
        with st.container(border=True):
            render_response_panel(language)
            render_voice_controls(language)
    else:
        left, right = st.columns([3, 2])
        with left:
            with st.container(border=True):
                render_response_panel(language)
                render_voice_controls(language)
        with right:
            with st.container(border=True):
                st.markdown('<div class="panel-title">📺 Smart Board Resources</div>', unsafe_allow_html=True)
                render_resource_carousel(st.session_state.last_topic or st.session_state.topic)
                render_quick_actions(language)

    st.divider()
    st.caption(
        "Connecting Dreams Foundation | Haryana Govt. Schools | "
        "Gemini 2.5 Flash | Streamlit + STT/TTS"
    )


if __name__ == "__main__":
    main()
