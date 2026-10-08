"""Unit tests for Ollama Client"""

import unittest
from tools.ollama_client import OllamaClient


class TestOllamaClient(unittest.TestCase):
    def test_ollama_client_fallback_handling(self):
        client = OllamaClient(base_url="http://localhost:999999")  # Invalid port
        self.assertFalse(client.is_available())
        self.assertEqual(client.list_models(), [])

        res = client.generate("Hello world")
        self.assertFalse(res["success"])
        self.assertTrue("not running" in res["error"] or "Error" in res["error"])


if __name__ == "__main__":
    unittest.main()
