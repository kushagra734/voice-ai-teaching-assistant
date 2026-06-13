"""Build study links for the Smart Board resources carousel."""

import urllib.parse
from dataclasses import dataclass, field

# Study link templates
LINK_WIKIPEDIA_EN = "https://en.wikipedia.org/wiki/{query}"
LINK_WIKIPEDIA_HI = "https://hi.wikipedia.org/wiki/{query}"
LINK_KHAN_ACADEMY = "https://www.khanacademy.org/search?page_search_query={query}"
LINK_YOUTUBE_EDU = "https://www.youtube.com/results?search_query={query}+class+6+10+explained+hindi"
LINK_NCERT = "https://www.google.com/search?q=NCERT+{query}+class+notes+PDF"


@dataclass
class StudyLink:
    """A labeled external study URL."""

    title: str
    url: str
    icon: str = "🔗"


@dataclass
class StudyResources:
    """Study links for a lesson topic."""

    topic: str
    links: list = field(default_factory=list)


class StudyResourceFetcher:
    """Builds Wikipedia, Khan Academy, YouTube, and NCERT links for topics."""

    def fetch_links(self, topic: str) -> StudyResources:
        """
        Build study links for the given topic (no network calls).

        Args:
            topic: Lesson or quiz topic.

        Returns:
            StudyResources with link list.
        """
        topic = topic.strip()
        search_topic = self._clean_topic_for_search(topic)
        encoded = urllib.parse.quote(search_topic.replace(" ", "_"))
        return StudyResources(
            topic=topic,
            links=self._build_links(topic, encoded),
        )

    def _clean_topic_for_search(self, topic: str) -> str:
        """Remove class numbers and noise from topic for cleaner URLs."""
        cleaned = topic.strip()
        for suffix in (" 101", " 102", " class 6", " class 7", " class 8", " class 9", " class 10"):
            if cleaned.lower().endswith(suffix):
                cleaned = cleaned[: -len(suffix)].strip()
        return cleaned or topic.strip()

    def _build_links(self, topic: str, encoded: str) -> list:
        """Build a list of study links for the topic."""
        query = urllib.parse.quote(topic)
        return [
            StudyLink("Wikipedia (English)", LINK_WIKIPEDIA_EN.format(query=encoded), "🌐"),
            StudyLink("Wikipedia (Hindi)", LINK_WIKIPEDIA_HI.format(query=encoded), "📖"),
            StudyLink("Khan Academy", LINK_KHAN_ACADEMY.format(query=query), "🎓"),
            StudyLink("YouTube Lessons", LINK_YOUTUBE_EDU.format(query=query), "▶️"),
            StudyLink("NCERT Notes", LINK_NCERT.format(query=query), "📚"),
        ]
