"""Small Ollama client using only the Python standard library.

Ollama is optional. Callers should always provide a fallback path because the
local daemon/model may be unavailable during demo.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request


DEFAULT_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
DEFAULT_MODEL = os.environ.get("OLLAMA_MODEL")


class OllamaClient:
    def __init__(self, model_name: str | None = None, base_url: str | None = None):
        self.model_name = model_name or DEFAULT_MODEL
        self.base_url = (base_url or DEFAULT_BASE_URL).rstrip("/")

    def _list_models(self, timeout: int = 3) -> list[str]:
        req = urllib.request.Request(f"{self.base_url}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        return [m.get("name") for m in payload.get("models", []) if m.get("name")]

    def _ensure_model(self, timeout: int = 3) -> tuple[bool, str]:
        models = self._list_models(timeout=timeout)
        if self.model_name:
            if self.model_name not in models:
                return False, f"Ollama is running, but model '{self.model_name}' was not found. Available: {models[:8]}"
            return True, "Ollama model is available."
        if not models:
            return False, "Ollama is running, but no local models were found."
        self.model_name = models[0]
        return True, f"Ollama model is available. Auto-selected '{self.model_name}'."

    def is_available(self, timeout: int = 3) -> tuple[bool, str]:
        try:
            return self._ensure_model(timeout=timeout)
        except Exception as exc:
            return False, str(exc)

    def chat(self, messages: list[dict], timeout: int = 120, temperature: float = 0.2) -> str:
        ok, message = self._ensure_model(timeout=min(timeout, 5))
        if not ok:
            raise RuntimeError(message)
        payload = {
            "model": self.model_name,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": 600,
            },
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}/api/chat",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                result = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Ollama HTTP {exc.code}: {body}") from exc
        return (result.get("message") or {}).get("content", "").strip()


def get_ollama_client() -> OllamaClient:
    return OllamaClient()
