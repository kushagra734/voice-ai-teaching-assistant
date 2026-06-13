"""Speech intent detection for the Streamlit voice teaching assistant."""

import re

import speech_recognition as sr

# Error message constants
ERROR_MIC_NOT_FOUND = "Microphone not detected. Please check your audio settings."
ERROR_COULD_NOT_UNDERSTAND = "Could not understand speech. Please try again clearly."
ERROR_TIMEOUT = "No speech detected. Please try speaking again."
ERROR_SERVICE_UNAVAILABLE = "Speech recognition service unavailable. Please try again."
ERROR_UNKNOWN = "Speech recognition failed. Please try again."

# Recognition configuration
LISTEN_TIMEOUT = 5
PHRASE_TIME_LIMIT = 10
AMBIENT_NOISE_DURATION = 0.8

# Quiz detection patterns
QUIZ_PATTERNS = [
    r"^quiz\s+on\s+(.+)$",
    r"^quiz\s+about\s+(.+)$",
    r"^quiz\s+for\s+(.+)$",
    r"^generate\s+quiz\s+on\s+(.+)$",
    r"^generate\s+quiz\s+about\s+(.+)$",
    r"^make\s+a\s+quiz\s+on\s+(.+)$",
    r"^(.+)\s+ka\s+quiz$",
    r"^(.+)\s+par\s+quiz$",
]


class SpeechResult:
    """Container for speech recognition results with intent detection."""

    def __init__(self, text: str, is_quiz: bool = False, topic: str = "", error: str = ""):
        """
        Initialize a speech result.

        Args:
            text: Raw transcribed text or error message.
            is_quiz: True if the user requested a quiz.
            topic: Extracted topic string.
            error: Non-empty if recognition failed.
        """
        self.text = text
        self.is_quiz = is_quiz
        self.topic = topic
        self.error = error

    @property
    def success(self) -> bool:
        """Return True if recognition succeeded without errors."""
        return not self.error


class SpeechEngine:
    """Handles microphone input and speech-to-text conversion."""

    def __init__(self):
        """Initialize the speech recognizer."""
        self._recognizer = sr.Recognizer()
        self._recognizer.energy_threshold = 300
        self._recognizer.dynamic_energy_threshold = True
        self._recognizer.pause_threshold = 0.8

    def listen(self) -> SpeechResult:
        """
        Listen via microphone and return transcribed text with intent.

        Returns:
            SpeechResult with text, quiz intent, and topic or error info.
        """
        try:
            with sr.Microphone() as source:
                self._recognizer.adjust_for_ambient_noise(
                    source, duration=AMBIENT_NOISE_DURATION
                )
                audio = self._recognizer.listen(
                    source,
                    timeout=LISTEN_TIMEOUT,
                    phrase_time_limit=PHRASE_TIME_LIMIT,
                )

        except sr.WaitTimeoutError:
            return SpeechResult(text="", error=ERROR_TIMEOUT)
        except OSError:
            return SpeechResult(text="", error=ERROR_MIC_NOT_FOUND)
        except Exception:
            return SpeechResult(text="", error=ERROR_MIC_NOT_FOUND)

        try:
            text = self._recognizer.recognize_google(audio, language="en-IN")
            text = text.strip()

            if not text:
                return SpeechResult(text="", error=ERROR_COULD_NOT_UNDERSTAND)

            is_quiz, topic = self.detect_intent(text)
            return SpeechResult(text=text, is_quiz=is_quiz, topic=topic)

        except sr.UnknownValueError:
            return SpeechResult(text="", error=ERROR_COULD_NOT_UNDERSTAND)
        except sr.RequestError:
            return SpeechResult(text="", error=ERROR_SERVICE_UNAVAILABLE)
        except Exception:
            return SpeechResult(text="", error=ERROR_UNKNOWN)

    def detect_intent(self, text: str) -> tuple:
        """
        Detect whether the user wants a quiz or a concept explanation.

        Args:
            text: Transcribed speech text.

        Returns:
            Tuple of (is_quiz: bool, topic: str).
        """
        cleaned = text.strip()
        lower = cleaned.lower()

        for pattern in QUIZ_PATTERNS:
            match = re.match(pattern, lower, re.IGNORECASE)
            if match:
                topic = match.group(1).strip()
                topic = self._clean_topic(topic)
                if topic:
                    return True, topic

        topic = self._clean_topic(cleaned)
        return False, topic

    def _clean_topic(self, topic: str) -> str:
        """
        Remove filler words and punctuation from an extracted topic.

        Args:
            topic: Raw topic string.

        Returns:
            Cleaned topic string.
        """
        topic = topic.strip().rstrip(".,!?")
        topic = re.sub(r"^(the|a|an)\s+", "", topic, flags=re.IGNORECASE)
        return topic.strip()
