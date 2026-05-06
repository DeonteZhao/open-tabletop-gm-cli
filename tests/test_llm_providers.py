from __future__ import annotations

import unittest

from config import Config
from llm import (
    build_client_kwargs,
    list_provider_options,
    normalize_provider,
    provider_base_url,
    validate_llm_config,
)


class LlmProviderTests(unittest.TestCase):
    def test_domestic_openai_compatible_providers_are_available(self):
        provider_ids = {option["value"] for option in list_provider_options()}
        expected = {
            "openai",
            "deepseek",
            "openrouter",
            "siliconflow",
            "kimi",
            "qwen",
            "glm",
            "doubao",
            "baichuan",
            "minimax",
            "custom",
        }
        self.assertTrue(expected.issubset(provider_ids))

    def test_known_provider_base_urls(self):
        self.assertEqual(provider_base_url("kimi"), "https://api.moonshot.cn/v1")
        self.assertEqual(provider_base_url("qwen"), "https://dashscope.aliyuncs.com/compatible-mode/v1")
        self.assertEqual(provider_base_url("siliconflow"), "https://api.siliconflow.cn/v1")

    def test_normalize_provider_from_base_url(self):
        self.assertEqual(normalize_provider("", "https://api.moonshot.cn/v1"), "kimi")
        self.assertEqual(normalize_provider("", "https://dashscope.aliyuncs.com/compatible-mode/v1"), "qwen")
        self.assertEqual(normalize_provider("", "http://localhost:1234/v1"), "custom")

    def test_custom_base_url_is_preserved_in_client_kwargs(self):
        config = Config(prefer_env=False)
        config.provider = "custom"
        config.base_url = "http://localhost:1234/v1"
        config.api_key = "local-key"
        config.model = "local-model"
        kwargs = build_client_kwargs(config)
        self.assertEqual(kwargs["base_url"], "http://localhost:1234/v1")
        self.assertEqual(kwargs["api_key"], "local-key")

    def test_custom_provider_requires_base_url(self):
        config = Config(prefer_env=False)
        config.provider = "custom"
        config.base_url = ""
        config.api_key = "key"
        config.model = "model"
        self.assertIn("Base URL", validate_llm_config(config))


if __name__ == "__main__":
    unittest.main()
