# Copyright (C) 2026 Byers Brands, LLC
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

"""
LLM client implementations for Python.
These clients can be called from Rust via FFI or used directly in Python.
"""

import requests
import json
from typing import Optional


class BaseLLMClient:
    """Base class for LLM clients."""

    def generate(self, prompt: str) -> str:
        raise NotImplementedError


class MockLLMClient(BaseLLMClient):
    """Mock LLM client for testing."""

    def __init__(self, response: str = None):
        if response is None:
            # Default to valid JSON response for testing
            self.response = json.dumps([
                {
                    "text": "The contract was signed on 2023-10-15.",
                    "category": "Stipulated/Verified",
                    "source_party": "CLIENT",
                    "date": "2023-10-15",
                    "citation": "Layer1/PDFs/contract_123.pdf"
                }
            ])
        else:
            self.response = response

    def generate(self, prompt: str) -> str:
        return self.response


class OllamaClient(BaseLLMClient):
    """Ollama LLM client."""

    def __init__(self, endpoint: str = "http://localhost:11434", model: str = "llama2"):
        self.endpoint = endpoint
        self.model = model

    def generate(self, prompt: str) -> str:
        """
        Generate response using Ollama API.
        API docs: https://github.com/jmorganca/ollama/blob/main/docs/api.md
        """
        url = f"{self.endpoint}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False
        }

        try:
            response = requests.post(url, json=payload, timeout=60)
            response.raise_for_status()
            return response.json().get('response', '')
        except requests.exceptions.RequestException as e:
            raise Exception(f"Ollama API error: {e}")


class GeminiClient(BaseLLMClient):
    """Google Gemini LLM client."""

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash"):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://generativelanguage.googleapis.com/v1"

    def generate(self, prompt: str) -> str:
        """
        Generate response using Google Gemini API.
        API docs: https://ai.google.dev/docs
        """
        url = f"{self.base_url}/models/{self.model}:generateContent?key={self.api_key}"
        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }]
        }

        try:
            response = requests.post(url, json=payload, timeout=60)
            response.raise_for_status()
            result = response.json()
            return result['candidates'][0]['content']['parts'][0]['text']
        except requests.exceptions.RequestException as e:
            raise Exception(f"Gemini API error: {e}")
        except (KeyError, IndexError) as e:
            raise Exception(f"Gemini API response parsing error: {e}")


class HiverLLMClient(BaseLLMClient):
    """Client for Hiver's existing Mistral AI integration."""

    def __init__(self, api_key: Optional[str] = None):
        # Reuse existing Mistral integration from ai_assistant app
        from apps.ai_assistant.mistral_client import MistralClient
        self.client = MistralClient(api_key=api_key)

    def generate(self, prompt: str) -> str:
        """Generate response using Hiver's Mistral client."""
        return self.client.generate(prompt)


# Example usage
if __name__ == "__main__":
    # Test Ollama client
    client = OllamaClient()
    response = client.generate("What is 2+2?")
    print(f"Ollama response: {response}")

    # Test Gemini client
    # client = GeminiClient(api_key="your-api-key")
    # response = client.generate("What is 2+2?")
    # print(f"Gemini response: {response}")
