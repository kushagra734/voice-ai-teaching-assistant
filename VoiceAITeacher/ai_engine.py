"""Gemini AI engine for concept explanations and quiz generation."""

import os

import google.generativeai as genai
from dotenv import load_dotenv

from prompts import LANG_HINGLISH, get_concept_prompt, get_quiz_prompt

# Error message constants
ERROR_NO_API_KEY = (
    "Gemini API key not configured. Please add GEMINI_API_KEY to your .env file."
)
ERROR_NO_INTERNET = "Internet connection required. Please check your network."
ERROR_EMPTY_RESPONSE = "AI returned an empty response. Please try again."
ERROR_RATE_LIMIT = (
    "AI service rate limit reached. Please wait a minute and try again, "
    "or check your Gemini API quota at https://aistudio.google.com/"
)
ERROR_SERVICE_UNAVAILABLE = "AI service temporarily unavailable. Please try again."
ERROR_INVALID_TOPIC = "Please provide a valid topic for generation."
ERROR_MODEL_UNAVAILABLE = "AI model unavailable. Please try again in a moment."

# Model configuration — primary + fallbacks for free-tier quota limits
DEFAULT_MODEL = "gemini-2.5-flash"
FALLBACK_MODELS = (
    "gemini-2.5-flash-lite",
    "gemini-flash-latest",
    "gemini-3-flash-preview",
    "gemini-3.5-flash",
    "gemini-3.1-flash-lite",
)
GENERATION_CONFIG = {
    "temperature": 0.7,
    "top_p": 0.9,
    "max_output_tokens": 4096,
}


class GeminiEngine:
    """Handles all interactions with the Google Gemini API."""

    def __init__(self):
        """Initialize the Gemini engine and configure the API client."""
        load_dotenv()
        self._api_key = os.getenv("GEMINI_API_KEY", "").strip()
        self._model = None
        self._configure()

    def _configure(self) -> None:
        """Configure the Gemini API client if a valid API key is present."""
        if self._api_key:
            genai.configure(api_key=self._api_key)
            self._model = self._create_model(DEFAULT_MODEL)

    def _create_model(self, model_name: str):
        """
        Create a GenerativeModel instance for the given model name.

        Args:
            model_name: Gemini model identifier.

        Returns:
            Configured GenerativeModel instance.
        """
        return genai.GenerativeModel(
            model_name,
            generation_config=GENERATION_CONFIG,
        )

    @property
    def is_configured(self) -> bool:
        """Return True if the API key is set and the model is ready."""
        return bool(self._api_key and self._model)

    def generate_response(self, prompt: str) -> str:
        """
        Send a prompt to Gemini and return the generated text.

        Args:
            prompt: The full prompt string to send to the model.

        Returns:
            Generated text or a user-friendly error message string.
        """
        if not self.is_configured:
            return ERROR_NO_API_KEY

        if not prompt or not prompt.strip():
            return ERROR_INVALID_TOPIC

        models_to_try = (DEFAULT_MODEL,) + FALLBACK_MODELS
        last_error = ERROR_SERVICE_UNAVAILABLE

        for model_name in models_to_try:
            try:
                model = self._create_model(model_name)
                response = model.generate_content(prompt)

                if response is None:
                    last_error = ERROR_EMPTY_RESPONSE
                    continue

                text = self._extract_text(response)
                if not text:
                    last_error = ERROR_EMPTY_RESPONSE
                    continue

                self._model = model
                return text.strip()

            except Exception as exc:
                last_error = self._handle_exception(exc)
                if self._should_try_fallback(exc):
                    continue
                return last_error

        return last_error

    def explain_concept(self, topic: str, language: str = LANG_HINGLISH) -> str:
        """
        Generate a concept explanation for the given topic and language.

        Args:
            topic: The subject or concept to explain.
            language: Output language — english, hindi, or hinglish.

        Returns:
            Formatted explanation string or error message.
        """
        topic = topic.strip()
        if not topic:
            return ERROR_INVALID_TOPIC

        prompt = get_concept_prompt(topic, language)
        return self.generate_response(prompt)

    def generate_quiz(self, topic: str, language: str = LANG_HINGLISH) -> str:
        """
        Generate a 5-question MCQ quiz for the given topic and language.

        Args:
            topic: The subject for the quiz.
            language: Output language — english, hindi, or hinglish.

        Returns:
            Formatted quiz string or error message.
        """
        topic = topic.strip()
        if not topic:
            return ERROR_INVALID_TOPIC

        prompt = get_quiz_prompt(topic, language)
        return self.generate_response(prompt)

    def _extract_text(self, response) -> str:
        """
        Safely extract text content from a Gemini response object.

        Args:
            response: The Gemini API response object.

        Returns:
            Extracted text or empty string.
        """
        try:
            if hasattr(response, "text") and response.text:
                return response.text

            if hasattr(response, "candidates") and response.candidates:
                parts = response.candidates[0].content.parts
                return "".join(part.text for part in parts if hasattr(part, "text"))

        except (AttributeError, IndexError, ValueError):
            pass

        return ""

    def _should_try_fallback(self, exc: Exception) -> bool:
        """
        Determine whether to retry with the next fallback model.

        Args:
            exc: The caught exception.

        Returns:
            True if another model should be attempted.
        """
        error_str = str(exc).lower()
        fallback_keywords = (
            "404",
            "not found",
            "429",
            "quota",
            "resource_exhausted",
            "rate limit",
            "exceeded your current quota",
        )
        return any(keyword in error_str for keyword in fallback_keywords)

    def _handle_exception(self, exc: Exception) -> str:
        """
        Map exceptions to user-friendly error messages.

        Args:
            exc: The caught exception.

        Returns:
            A readable error message string.
        """
        error_str = str(exc).lower()
        error_type = type(exc).__name__.lower()

        network_keywords = (
            "connection",
            "network",
            "timeout",
            "unreachable",
            "dns",
            "socket",
            "ssl",
            "connect",
        )
        if any(keyword in error_str for keyword in network_keywords):
            return ERROR_NO_INTERNET

        if "404" in error_str or "not found" in error_str:
            return ERROR_MODEL_UNAVAILABLE

        rate_limit_keywords = (
            "429",
            "quota",
            "resource_exhausted",
            "rate limit",
            "exceeded your current quota",
        )
        if any(keyword in error_str for keyword in rate_limit_keywords) or "resourceexhausted" in error_type:
            return ERROR_RATE_LIMIT

        api_key_keywords = ("api key", "api_key", "invalid key", "permission", "401", "403")
        if any(keyword in error_str for keyword in api_key_keywords):
            return ERROR_NO_API_KEY

        return ERROR_SERVICE_UNAVAILABLE
