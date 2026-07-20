"""
Tokenizer Manager — counts tokens for various model architectures.
Provides accurate context window management (sliding window / truncation).
"""

from loguru import logger
from config.settings import settings


class TokenizerManager:
    """
    Counts and manages context windows for LLMs using tiktoken or transformers tokenizers.
    Falls back gracefully if libraries or models are not pre-downloaded.
    """

    _tokenizers = {}

    @classmethod
    def get_tokenizer(cls, model_name: str):
        """Get or initialize a tokenizer for a specific model."""
        if model_name in cls._tokenizers:
            return cls._tokenizers[model_name]

        # Try tiktoken first (for OpenAI or models sharing the format)
        if "gpt" in model_name.lower():
            try:
                import tiktoken
                enc = tiktoken.encoding_for_model(model_name)
                cls._tokenizers[model_name] = enc
                return enc
            except Exception as e:
                logger.warning(f"Could not load tiktoken for {model_name}: {e}")

        # Try Hugging Face tokenizers (llama, mistral, qwen, etc.)
        try:
            from transformers import AutoTokenizer
            # Fallback mappings for local/Ollama model names to HF equivalents
            hf_mapping = {
                "llama3": "meta-llama/Meta-Llama-3-8B",
                "llama3.1": "meta-llama/Meta-Llama-3.1-8B",
                "qwen2.5": "Qwen/Qwen2.5-7B",
                "mistral": "mistralai/Mistral-7B-v0.1",
            }
            mapped_name = next(
                (v for k, v in hf_mapping.items() if k in model_name.lower()),
                None
            )

            # If no mapping, try using the model name directly
            target = mapped_name or model_name
            # Load local fast tokenizer, if fails it falls back
            enc = AutoTokenizer.from_pretrained(target, use_fast=True)
            cls._tokenizers[model_name] = enc
            logger.info(f"Loaded Hugging Face tokenizer for {model_name}")
            return enc
        except Exception as e:
            logger.warning(f"Could not load HuggingFace tokenizer for {model_name}: {e}")

        # Global fallback (cl100k_base)
        try:
            import tiktoken
            enc = tiktoken.get_encoding("cl100k_base")
            cls._tokenizers[model_name] = enc
            logger.info(f"Loaded fallback tiktoken cl100k_base for {model_name}")
            return enc
        except Exception as e:
            logger.error(f"Fallback tokenizer failed: {e}")
            return None

    @classmethod
    def count_tokens(cls, text: str, model_name: str) -> int:
        """Count tokens in text for a given model."""
        if not text:
            return 0

        enc = cls.get_tokenizer(model_name)
        if enc is None:
            # Absolute fallback: ~4 characters per token
            return len(text) // 4

        try:
            if hasattr(enc, "encode"):
                return len(enc.encode(text))
            elif hasattr(enc, "encode_ordinary"):
                return len(enc.encode_ordinary(text))
        except Exception as e:
            logger.warning(f"Token counting error: {e}")
            return len(text) // 4

    @classmethod
    def trim_history(
        cls,
        messages: list[dict],
        max_tokens: int,
        model_name: str,
        system_prompt: str = "",
    ) -> list[dict]:
        """
        Trims a list of messages (history) to fit within a token limit.
        Guarantees the system prompt is accounted for if provided.
        Keeps newer messages.
        """
        system_tokens = cls.count_tokens(system_prompt, model_name)
        available_tokens = max_tokens - system_tokens

        trimmed = []
        accumulated_tokens = 0

        # Iterate backward (from newest to oldest)
        for msg in reversed(messages):
            msg_tokens = cls.count_tokens(msg.get("content", ""), model_name)
            # Add small overhead per message (e.g. metadata wrapper tokens)
            msg_tokens += 4

            if accumulated_tokens + msg_tokens > available_tokens:
                break
            trimmed.insert(0, msg)
            accumulated_tokens += msg_tokens

        return trimmed
