# backend/gemini/client.py
from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple, Union

from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables from .env (if present)
load_dotenv()


class GeminiClientError(Exception):
    """Raised when Gemini client fails in a controlled way."""


def _extract_json(text: str) -> Dict[str, Any]:
    """
    Extract JSON object from model output.
    Handles cases where the model wraps output with ```json ... ``` or has extra text.

    Returns:
        dict parsed JSON

    Raises:
        GeminiClientError if JSON cannot be parsed.
    """
    if not text or not text.strip():
        raise GeminiClientError("Empty response from Gemini.")

    cleaned = text.strip()

    # Remove markdown code fences if present
    cleaned = cleaned.replace("```json", "").replace("```", "").strip()

    # Try direct JSON parse first
    try:
        return json.loads(cleaned)
    except Exception:
        pass

    # Fallback: find first {...} JSON block
    match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    if match:
        candidate = match.group(0)
        try:
            return json.loads(candidate)
        except Exception as e:
            raise GeminiClientError(f"Failed to parse JSON block: {e}")

    raise GeminiClientError("Gemini output was not valid JSON. Ask model to return JSON only.")


@dataclass
class GeminiConfig:
    model_name: str = os.getenv("GEMINI_MODEL", "models/gemini-3-flash-preview")
    temperature: float = 0.2
    top_p: float = 0.95
    top_k: int = 40
    max_output_tokens: int = 2048
    timeout_retries: int = 2
    retry_sleep_seconds: float = 0.8



class GeminiClient:
    """
    A small wrapper around google-generativeai that:
    - configures API key
    - calls Gemini model
    - optionally forces JSON output parsing
    """

    def __init__(self, config: Optional[GeminiConfig] = None) -> None:
        self.config = config or GeminiConfig()
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise GeminiClientError(
                "GEMINI_API_KEY not found. Set it in backend/.env or system environment."
            )

        genai.configure(api_key=api_key)

        self.model = genai.GenerativeModel(
            model_name=self.config.model_name,
            generation_config={
                "temperature": self.config.temperature,
                "top_p": self.config.top_p,
                "top_k": self.config.top_k,
                "max_output_tokens": self.config.max_output_tokens,
            },
        )

    def generate_text(
        self,
        prompt: str,
        *,
        system_instruction: Optional[str] = None,
    ) -> str:
        """
        Returns raw text from Gemini.
        """
        if not prompt or not prompt.strip():
            raise GeminiClientError("Prompt cannot be empty.")

        # google-generativeai can accept "contents" as a string
        # system_instruction is supported via model initialization in some SDK versions,
        # but to keep this stable, we prepend it when provided.
        final_prompt = prompt
        if system_instruction:
            final_prompt = f"{system_instruction.strip()}\n\n{prompt}"

        last_err: Optional[Exception] = None

        for attempt in range(self.config.timeout_retries + 1):
            try:
                resp = self.model.generate_content(final_prompt)
                text = getattr(resp, "text", None)
                if text is None:
                    # Some responses provide candidates; keep it simple and safe
                    raise GeminiClientError("Gemini returned no text.")
                return text
            except Exception as e:
                last_err = e
                if attempt < self.config.timeout_retries:
                    time.sleep(self.config.retry_sleep_seconds)
                    continue
                raise GeminiClientError(f"Gemini generate_text failed: {e}") from e

        # Should never reach
        raise GeminiClientError(f"Gemini generate_text failed: {last_err}")

    def generate_json(
        self,
        prompt: str,
        *,
        system_instruction: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Returns parsed JSON dict from Gemini response.
        Your prompts should explicitly say: "Return JSON only".
        """
        text = self.generate_text(prompt, system_instruction=system_instruction)
        return _extract_json(text)


# Convenience singleton (optional)
_default_client: Optional[GeminiClient] = None


def get_client() -> GeminiClient:
    global _default_client
    if _default_client is None:
        _default_client = GeminiClient()
    return _default_client
