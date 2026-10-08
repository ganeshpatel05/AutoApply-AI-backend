"""AutoApply AI — Ollama Local LLM Client
Direct HTTP client for local Ollama API (http://localhost:11434).
Performance-optimized: session reuse, model caching, redundant call elimination.
"""

import os
import requests
from config.settings import OLLAMA_MODEL, OLLAMA_BASE_URL


class OllamaClient:
    """Communicates directly with local Ollama HTTP API."""
    _avail_cache = None
    _avail_time = 0

    def __init__(self, base_url: str = None, model: str = None):
        self.base_url = (base_url or os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")).rstrip("/")
        self.configured_model = model or os.getenv("OLLAMA_MODEL", "")
        self.session = requests.Session()
        self._cached_model = None  # Cache resolved model name

    def is_available(self, force: bool = False) -> bool:
        """Check if Ollama server is running and reachable."""
        import time
        now = time.time()
        if not force and OllamaClient._avail_cache is not None and (now - OllamaClient._avail_time) < 10:
            return OllamaClient._avail_cache
        try:
            resp = self.session.get(f"{self.base_url}/api/tags", timeout=0.8)
            is_ok = resp.status_code == 200
        except Exception:
            is_ok = False
        OllamaClient._avail_cache = is_ok
        OllamaClient._avail_time = now
        return is_ok

    def list_models(self) -> list[str]:
        """List all model names installed in Ollama."""
        try:
            resp = self.session.get(f"{self.base_url}/api/tags", timeout=3)
            if resp.status_code == 200:
                data = resp.json()
                models = [m.get("name") for m in data.get("models", []) if m.get("name")]
                return models
        except Exception:
            pass
        return []

    def get_active_model(self) -> str:
        """
        Get configured model or auto-detect an available model.
        Returns empty string if no models exist.
        """
        if self.configured_model:
            return self.configured_model

        models = self.list_models()
        if models:
            # Strip tags for comparison or return first
            return models[0].split(":")[0] if ":" in models[0] else models[0]
        return ""

    def _get_cached_model(self) -> str:
        """Get model name with caching to avoid repeated API calls."""
        if self._cached_model:
            return self._cached_model
        model = self.get_active_model()
        if model:
            self._cached_model = model
        return model

    def generate(self, prompt: str, system_prompt: str = "", model: str = None) -> dict:
        """
        Generate text using Ollama chat endpoint.
        Returns {"success": bool, "text": str, "model": str, "error": str}
        Fast failure: checks availability first to prevent hanging when Ollama is offline.
        """
        if not self.is_available():
            return {
                "success": False,
                "text": "",
                "model": model or self.configured_model or "",
                "error": "Ollama server is not running at " + self.base_url
            }

        target_model = model or self._get_cached_model()
        if not target_model:
            return {
                "success": False,
                "text": "",
                "model": "",
                "error": "No Ollama model configured or installed."
            }

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            payload = {
                "model": target_model,
                "messages": messages,
                "stream": False
            }
            resp = self.session.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=(5, 60)  # 5s connect, 60s read
            )
            if resp.status_code == 200:
                data = resp.json()
                content = data.get("message", {}).get("content", "").strip()
                return {
                    "success": True,
                    "text": content,
                    "model": target_model,
                    "error": ""
                }
            else:
                return {
                    "success": False,
                    "text": "",
                    "model": target_model,
                    "error": f"Ollama API returned HTTP status {resp.status_code}: {resp.text}"
                }
        except requests.exceptions.ConnectionError:
            self._cached_model = None  # Reset cache on connection failure
            return {
                "success": False,
                "text": "",
                "model": target_model,
                "error": "Ollama server is not running at " + self.base_url
            }
        except requests.exceptions.Timeout:
            return {
                "success": False,
                "text": "",
                "model": target_model,
                "error": "Request to Ollama timed out (60s)."
            }
        except Exception as e:
            return {
                "success": False,
                "text": "",
                "model": target_model,
                "error": f"Error communicating with Ollama: {str(e)}"
            }
