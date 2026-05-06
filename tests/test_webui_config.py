from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import config
import webui


class WebUiConfigTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_file = Path(self.temp_dir.name) / "config.json"
        self.patches = [
            patch.object(config, "CONFIG_FILE", self.config_file),
            patch.object(config, "CONFIG_DIR", self.config_file.parent),
            patch.object(webui, "CONFIG_FILE", self.config_file),
        ]
        for patcher in self.patches:
            patcher.start()
        webui.app.config["TESTING"] = True
        webui._SESSION_STATES.clear()
        self.client = webui.app.test_client()

    def tearDown(self):
        webui._SESSION_STATES.clear()
        for patcher in reversed(self.patches):
            patcher.stop()
        self.temp_dir.cleanup()

    def test_custom_provider_base_url_is_saved_from_api(self):
        response = self.client.post(
            "/api/config",
            json={
                "provider": "custom",
                "base_url": "http://localhost:1234/v1",
                "model": "local-model",
                "api_key": "local-key",
                "api_key_modified": True,
            },
        )
        payload = response.get_json()

        self.assertTrue(payload["ok"])
        saved = config.get_config(prefer_env=False)
        self.assertEqual(saved.provider, "custom")
        self.assertEqual(saved.base_url, "http://localhost:1234/v1")
        self.assertEqual(saved.model, "local-model")
        self.assertEqual(saved.api_key, "local-key")


if __name__ == "__main__":
    unittest.main()
