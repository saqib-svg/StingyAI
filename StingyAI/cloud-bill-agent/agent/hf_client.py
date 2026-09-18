"""
Hugging Face Hosted Inference API Client.

Communicates with the Hugging Face hosted chat-completions endpoint using httpx.
No local model downloading or transformers dependencies required.
"""

import os
from typing import Dict, List, Any, Optional
import httpx
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()


class HFInferenceClient:
    """
    Lightweight HTTP Client for Hugging Face hosted Inference API (chat-completions format).
    """

    def __init__(
        self,
        token: Optional[str] = None,
        model_id: Optional[str] = None,
        api_url: Optional[str] = None,
    ):
        self.token = token or os.getenv("HF_API_TOKEN", "").strip()
        self.model_id = model_id or os.getenv("HF_MODEL_ID", "Qwen/Qwen2.5-Coder-32B-Instruct").strip()
        self.api_url = api_url or os.getenv("HF_API_URL", "https://router.huggingface.co/v1/chat/completions").strip()

    def is_configured(self) -> bool:
        """Checks if the HF_API_TOKEN is present."""
        return bool(self.token)

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.1,
        max_tokens: int = 1024,
    ) -> str:
        """
        Sends a chat completions POST request to the Hugging Face hosted router endpoint.
        
        :param messages: List of chat messages (e.g. [{"role": "user", "content": "..."}])
        :param temperature: Sampling temperature
        :param max_tokens: Max output tokens
        :return: Generated text content from assistant response
        """
        if not self.token:
            raise ValueError(
                "Hugging Face API token (HF_API_TOKEN) is not configured. "
                "Please set HF_API_TOKEN in your .env file or environment variables."
            )

        if not self.model_id:
            raise ValueError("Hugging Face model ID (HF_MODEL_ID) is not set.")

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model_id,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        try:
            with httpx.Client(timeout=30.0) as client:
                res = client.post(self.api_url, headers=headers, json=payload)

            if res.status_code == 401 or res.status_code == 403:
                raise RuntimeError(
                    f"Hugging Face API Authentication failed ({res.status_code}). "
                    "Please verify your HF_API_TOKEN in .env."
                )
            elif res.status_code == 429:
                raise RuntimeError("Hugging Face API Rate Limit exceeded (429). Please try again shortly.")
            elif res.status_code != 200:
                raise RuntimeError(
                    f"Hugging Face API Error ({res.status_code}): {res.text}"
                )

            data = res.json()
            choices = data.get("choices", [])
            if not choices:
                raise RuntimeError("Malformed response from Hugging Face API: 'choices' field is empty.")

            assistant_msg = choices[0].get("message", {}).get("content", "")
            return assistant_msg

        except httpx.TimeoutException:
            raise RuntimeError("Hugging Face API request timed out (30s limit exceeded).")
        except httpx.RequestError as e:
            raise RuntimeError(f"Hugging Face API connection failure: {str(e)}")
