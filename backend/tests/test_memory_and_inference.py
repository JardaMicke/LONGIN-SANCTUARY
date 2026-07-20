"""
Test suite for LONGIN SANCTUARY memory, inference, and content safety systems.
"""

import sys
from pathlib import Path
import unittest
from uuid import uuid4

# Setup path to import backend modules
sys.path.append(str(Path(__file__).parent.parent))

from core.context.tokenizer_manager import TokenizerManager
from core.content.content_classifier import ContentClassifier
from core.content.age_check import AgeVerifier


class TestMemoryAndInference(unittest.TestCase):

    def test_token_counting_fallback(self):
        """Verify token counter returns approximate correct sizes."""
        text = "Hello world! This is a test of the token counter."
        # Approximate: ~12 words -> ~12-15 tokens
        tokens = TokenizerManager.count_tokens(text, "llama3.1")
        self.assertGreater(tokens, 0)
        self.assertLess(tokens, len(text))

    def test_history_trimming(self):
        """Verify sliding window trims older messages first."""
        history = [
            {"role": "user", "content": "Message 1 (very old)"},
            {"role": "assistant", "content": "Message 2"},
            {"role": "user", "content": "Message 3 (recent)"},
        ]
        trimmed = TokenizerManager.trim_history(
            messages=history,
            max_tokens=30, # low limit to trigger trimming
            model_name="llama3.1"
        )
        # Should keep recent messages
        self.assertGreater(len(trimmed), 0)
        self.assertEqual(trimmed[-1]["content"], "Message 3 (recent)")

    def test_content_classifier_sfw(self):
        """SFW text should pass the classifier without hits."""
        text = "Dnes je velmi hezký den na procházku v lese."
        classifier = ContentClassifier()
        self.assertFalse(classifier.is_nsfw(text))
        self.assertEqual(classifier.filter_response(text, "strict"), text)

    def test_content_classifier_nsfw(self):
        """NSFW keywords should trigger the classifier and moderate censorship."""
        text = "Tento text obsahuje slovo sex a nahota."
        classifier = ContentClassifier()
        self.assertTrue(classifier.is_nsfw(text))
        
        # Strict mode blocks completely
        strict_filtered = classifier.filter_response(text, "strict")
        self.assertIn("zablokován", strict_filtered)
        
        # Moderate mode censors keywords
        moderate_filtered = classifier.filter_response(text, "moderate")
        self.assertIn("s*x", moderate_filtered.lower())
        self.assertIn("n*hota", moderate_filtered.lower())

    def test_age_verification_token(self):
        """Verify creation and decoding of age gate JWTs."""
        ip = "192.168.1.18"
        token = AgeVerifier.create_verification_token(ip)
        self.assertIsNotNone(token)
        
        # Decode validation
        from jose import jwt
        from config.settings import settings
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        self.assertTrue(payload.get("verified"))
        self.assertEqual(payload.get("ip"), ip)


if __name__ == "__main__":
    unittest.main()
