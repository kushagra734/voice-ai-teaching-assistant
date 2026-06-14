# Voice AI Teaching Assistant

Voice-enabled AI co-pilot for Haryana government school teachers — **Connecting Dreams Foundation Round 2, Option A**.

**Live app:** Deploy `app.py` on [Streamlit Cloud](https://share.streamlit.io) for your submission URL.

## Features

| Feature | Description |
|---------|-------------|
| Concept explanation | Gemini AI explains topics in English, Hindi, or Hinglish |
| Voice input | Browser microphone → speech-to-text topic |
| Quiz generation | 5 MCQ interactive quiz with scoring |
| Read aloud | gTTS audio for AI responses |
| Smart board links | Wikipedia, Khan Academy, YouTube, NCERT resources |
| Classroom mode | Larger text for projector / smart board |

## Tech Stack

| Component | Technology |
|-----------|------------|
| Web UI | Streamlit |
| AI | Google Gemini 2.5 Flash |
| Prompts | `prompts.py` (language guardrails) |
| STT | SpeechRecognition + Google Web Speech API |
| TTS | gTTS |

## Run Locally

```bash
cd VoiceAITeacher
pip install -r requirements.txt
cp .env.example .env
# Add GEMINI_API_KEY=your_key to .env
python -m streamlit run app.py
```

Windows shortcut: double-click `run_web.bat`

Open **http://localhost:8501**

## Deploy to Streamlit Cloud (Live URL)

1. Push this folder to a **public GitHub** repository
2. Go to [share.streamlit.io](https://share.streamlit.io) → **New app**
3. Main file path: **`app.py`**
4. Advanced settings → Secrets:

```toml
GEMINI_API_KEY = "your_actual_gemini_api_key"
```

5. Deploy — you get a URL like `https://your-app-name.streamlit.app`

## Getting Gemini API Key

1. Visit [Google AI Studio](https://aistudio.google.com/apikey)
2. Create an API key
3. Add to `.env` (local) or Streamlit Secrets (cloud)

## Project Structure

```
VoiceAITeacher/
├── app.py                 # Streamlit web app (main entry)
├── ai_engine.py           # Gemini API integration
├── prompts.py             # AI prompt templates (EN / HI / Hinglish)
├── quiz_parser.py         # Interactive quiz parsing
├── speech_to_text.py      # Voice intent detection
├── study_resources.py     # Study resource links
├── requirements.txt       # Python dependencies
├── run_web.bat            # Windows launcher
├── .env.example           # Local API key template
└── .streamlit/
    ├── config.toml        # Streamlit theme
    └── secrets.toml.example
```



## License

Built for Connecting Dreams Foundation technical assignment.
