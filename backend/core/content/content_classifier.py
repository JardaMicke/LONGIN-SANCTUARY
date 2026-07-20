"""
Content Classifier — detects NSFW themes in text prompts and model outputs.
Filters content based on server and character safety configuration.
"""

import re
from loguru import logger
from config.settings import settings


class ContentClassifier:
    """Classifies prompts and generated text to prevent leaks of restricted content."""

    # Simple base vocabulary of NSFW indicators (Czech + English)
    NSFW_KEYWORDS = [
        r"\berotika\b", r"\bsexy\b", r"\bnahota\b", r"\bnahý\b", r"\bnahá\b",
        r"\bporn\b", r"\bnude\b", r"\berotic\b", r"\bnaked\b", r"\bsex\b",
        r"\bpornografie\b", r"\bpenis\b", r"\bvagina\b", r"\bprsa\b", r"\bkozy\b",
        r"\bblood\b", r"\bgore\b", r"\bkrveprolití\b", r"\bmurder\b", r"\bvražda\b"
    ]

    def __init__(self):
        self._regex = re.compile(
            "|".join(self.NSFW_KEYWORDS),
            re.IGNORECASE
        )

    def is_nsfw(self, text: str) -> bool:
        """Return True if text contains explicit keywords."""
        if not text:
            return False
        return bool(self._regex.search(text))

    def filter_response(self, text: str, filter_level: str) -> str:
        """
        Filters text according to filter level (strict, moderate, permissive).
        Censors explicit words if filter level is strict/moderate.
        """
        if filter_level == "permissive":
            return text

        if filter_level == "strict" and self.is_nsfw(text):
            return "[Obsah byl zablokován bezpečnostním filtrem]"

        # For moderate, censor matches with asterisks by replacing the second character
        def censor(match):
            word = match.group(0)
            if len(word) > 1:
                return word[0] + "*" + word[2:]
            return "*"

        return self._regex.sub(censor, text)
