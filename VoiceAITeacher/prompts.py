"""Prompt templates for Gemini AI educational content generation."""

# Supported output languages
LANG_ENGLISH = "english"
LANG_HINDI = "hindi"
LANG_HINGLISH = "hinglish"

_CONCEPT_RULES = {
    LANG_ENGLISH: """
Write in clear, simple ENGLISH only for Classes 6-10.
Use relatable Indian examples: dal, roti, cricket, monsoon, Diwali, etc.
Keep vocabulary easy for government school students in Haryana.
""",
    LANG_HINDI: """
Write in simple HINDI using Devanagari script (हिंदी) only for Classes 6-10.
Use relatable Indian examples: दाल, रोटी, क्रिकेट, मानसून, दिवाली, etc.
Keep vocabulary easy for government school students in Haryana.
""",
    LANG_HINGLISH: """
Write in HINGLISH only — Roman/Latin script (English letters).
Mix Hindi words in English letters + English words in every sentence.
Example: "Photosynthesis ka matlab hai ki plants sunlight se khana banate hain."
Use relatable Indian examples: dal, roti, cricket, monsoon, Diwali, etc.
NEVER use Devanagari script. NEVER use pure English only.
""",
}

_QUIZ_RULES = {
    LANG_ENGLISH: "Write all questions and options in simple ENGLISH only.",
    LANG_HINDI: "Write all questions and options in simple HINDI (Devanagari script) only.",
    LANG_HINGLISH: (
        "Write all questions and options in HINGLISH Roman script. "
        "Mix Hindi + English in every sentence. No Devanagari."
    ),
}


def get_concept_prompt(topic: str, language: str = LANG_HINGLISH) -> str:
    """
    Build a concept explanation prompt for the given topic and language.

    Args:
        topic: Lesson topic.
        language: One of english, hindi, hinglish.

    Returns:
        Formatted prompt string.
    """
    lang = language if language in _CONCEPT_RULES else LANG_HINGLISH
    rules = _CONCEPT_RULES[lang]

    return f"""
You are a friendly AI teacher for Indian government school students in Classes 6-10.
Explain the topic "{topic}".

LANGUAGE RULES — FOLLOW STRICTLY:
{rules}

Format your response EXACTLY like this:

📚 EXPLANATION:
[3-4 paragraphs]

🔑 KEY POINTS:
- [point 1]
- [point 2]
- [point 3]
- [point 4]
- [point 5]

📝 SUMMARY:
[2-3 line summary]
"""


def get_quiz_prompt(topic: str, language: str = LANG_HINGLISH) -> str:
    """
    Build a quiz generation prompt for the given topic and language.

    Args:
        topic: Quiz topic.
        language: One of english, hindi, hinglish.

    Returns:
        Formatted prompt string.
    """
    lang = language if language in _QUIZ_RULES else LANG_HINGLISH
    rules = _QUIZ_RULES[lang]

    return f"""
You are a quiz generator for Indian government school students in Classes 6-10.
Generate exactly 5 multiple choice questions on "{topic}".
Each question must have exactly 4 options labeled A), B), C), D).

LANGUAGE: {rules}

Format EXACTLY like this:

QUIZ: {topic}
════════════════════════════════

Q1. [Question text]
A) [Option]
B) [Option]
C) [Option]
D) [Option]

Q2. ...
[continue for all 5 questions]

════════════════════════════════
ANSWER KEY:
Q1 → [Correct Option Letter]
Q2 → [Correct Option Letter]
Q3 → [Correct Option Letter]
Q4 → [Correct Option Letter]
Q5 → [Correct Option Letter]
"""
