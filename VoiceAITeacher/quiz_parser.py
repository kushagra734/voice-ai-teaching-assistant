"""Parser for AI-generated quiz text into structured question data."""

import re
from dataclasses import dataclass, field


@dataclass
class QuizQuestion:
    """Single multiple-choice question with options and correct answer."""

    number: int
    text: str
    options: dict = field(default_factory=dict)
    correct: str = ""


@dataclass
class ParsedQuiz:
    """Complete parsed quiz with topic, questions, and answer key."""

    topic: str
    questions: list = field(default_factory=list)
    raw_text: str = ""


class QuizParser:
    """Parses formatted quiz text from Gemini into structured data."""

    QUESTION_BLOCK_PATTERN = re.compile(
        r"Q(\d+)\.\s*(.+?)(?=\nQ\d+\.|\n═|={3,}|ANSWER KEY|$)",
        re.DOTALL | re.IGNORECASE,
    )
    OPTION_PATTERNS = [
        re.compile(r"^([A-D])\)\s*(.+)$", re.MULTILINE),
        re.compile(r"^([A-D])\.\s*(.+)$", re.MULTILINE),
        re.compile(r"^([A-D])\s*[-:]\s*(.+)$", re.MULTILINE),
    ]
    ANSWER_PATTERNS = [
        re.compile(r"Q(\d+)\s*[→\->:]+\s*([A-D])", re.IGNORECASE),
        re.compile(r"Q(\d+)\s*=\s*([A-D])", re.IGNORECASE),
        re.compile(r"Q(\d+)\s+answer[:\s]+([A-D])", re.IGNORECASE),
    ]
    TOPIC_PATTERN = re.compile(r"QUIZ:\s*(.+)", re.IGNORECASE)

    def parse(self, quiz_text: str) -> ParsedQuiz:
        """
        Parse raw quiz text into a ParsedQuiz object.

        Args:
            quiz_text: Raw AI-generated quiz string.

        Returns:
            ParsedQuiz with topic, questions, and correct answers.
        """
        topic_match = self.TOPIC_PATTERN.search(quiz_text)
        topic = topic_match.group(1).strip() if topic_match else "Quiz"
        topic = topic.split("\n")[0].strip()

        if "ANSWER KEY" in quiz_text.upper():
            parts = re.split(r"ANSWER KEY:?", quiz_text, flags=re.IGNORECASE)
            quiz_body = parts[0]
            answer_section = parts[1] if len(parts) > 1 else ""
        else:
            quiz_body = quiz_text
            answer_section = ""

        answer_map = self._parse_answers(answer_section)

        questions = []
        for match in self.QUESTION_BLOCK_PATTERN.finditer(quiz_body):
            q_num = int(match.group(1))
            block = match.group(2).strip()
            question = self._parse_question_block(q_num, block, answer_map)
            if question.text:
                questions.append(question)

        if not questions:
            questions = self._fallback_parse(quiz_body, answer_map)

        questions.sort(key=lambda q: q.number)
        return ParsedQuiz(topic=topic, questions=questions, raw_text=quiz_text)

    def _parse_answers(self, answer_section: str) -> dict:
        """Extract answer key mapping from text."""
        answer_map = {}
        for pattern in self.ANSWER_PATTERNS:
            for match in pattern.finditer(answer_section):
                answer_map[int(match.group(1))] = match.group(2).upper()
        return answer_map

    def _parse_options(self, block: str) -> dict:
        """Extract A-D options from a question block."""
        options = {}
        for pattern in self.OPTION_PATTERNS:
            for match in pattern.finditer(block):
                letter = match.group(1).upper()
                if letter not in options:
                    options[letter] = match.group(2).strip()
        return options

    def _parse_question_block(self, q_num: int, block: str, answer_map: dict) -> QuizQuestion:
        """Parse a single question block into a QuizQuestion."""
        options = self._parse_options(block)
        lines = [line.strip() for line in block.split("\n") if line.strip()]

        q_text_parts = []
        for line in lines:
            if re.match(r"^[A-D][\)\.\:\-]", line, re.IGNORECASE):
                break
            q_text_parts.append(line)

        q_text = " ".join(q_text_parts).strip()
        if not q_text and lines:
            q_text = lines[0]

        return QuizQuestion(
            number=q_num,
            text=q_text,
            options=options,
            correct=answer_map.get(q_num, ""),
        )

    def _fallback_parse(self, quiz_body: str, answer_map: dict) -> list:
        """Fallback line-by-line parser when regex blocks fail."""
        questions = []
        current_num = 0
        current_lines = []

        for line in quiz_body.split("\n"):
            stripped = line.strip()
            q_match = re.match(r"Q(\d+)\.\s*(.*)", stripped, re.IGNORECASE)
            if q_match:
                if current_num and current_lines:
                    block = "\n".join(current_lines)
                    questions.append(self._parse_question_block(current_num, block, answer_map))
                current_num = int(q_match.group(1))
                rest = q_match.group(2).strip()
                current_lines = [rest] if rest else []
            elif current_num and stripped:
                current_lines.append(stripped)

        if current_num and current_lines:
            block = "\n".join(current_lines)
            questions.append(self._parse_question_block(current_num, block, answer_map))

        return questions

    def to_display_text(self, parsed: ParsedQuiz, include_answers: bool = False) -> str:
        """
        Convert parsed quiz back to readable text for copy/save.

        Args:
            parsed: Parsed quiz object.
            include_answers: Whether to append the answer key.

        Returns:
            Formatted text string.
        """
        if parsed.raw_text and not parsed.questions:
            return parsed.raw_text

        lines = [f"QUIZ: {parsed.topic}", "=" * 40, ""]

        for question in parsed.questions:
            lines.append(f"Q{question.number}. {question.text}")
            for letter in ("A", "B", "C", "D"):
                if letter in question.options:
                    lines.append(f"{letter}) {question.options[letter]}")
            lines.append("")

        if include_answers:
            lines.extend(["=" * 40, "ANSWER KEY:"])
            for question in parsed.questions:
                lines.append(f"Q{question.number} -> {question.correct}")

        return "\n".join(lines)
