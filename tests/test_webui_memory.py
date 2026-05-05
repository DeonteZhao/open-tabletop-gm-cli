from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import campaign
import characters
import webui


class FakeEngine:
    def __init__(self, campaign_name: str, prefer_env_config: bool = True):
        self.campaign_name = campaign_name
        self.prefer_env_config = prefer_env_config
        self.active_character_name = ""
        self.messages = []

    def refresh_config(self):
        return None

    def start_session_intro(self, active_character_name: str) -> str:
        self.active_character_name = active_character_name
        self.messages.append({"role": "assistant", "content": f"开场：{active_character_name} 进入冒险。"})
        return f"开场：{active_character_name} 进入冒险。"

    def chat(self, user_input: str) -> str:
        self.messages.append({"role": "user", "content": user_input})
        response = f"GM回应：{user_input}"
        self.messages.append({"role": "assistant", "content": response})
        return response

    def summarize_for_save(self) -> str:
        return "## Save Summary\n- 玩家进入了老宅。\n- 当前线索：门后有脚印。\n"


class WebUiMemoryTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.campaigns_dir = Path(self.temp_dir.name) / "campaigns"
        self.campaigns_dir.mkdir()
        self.patches = [
            patch.object(campaign, "CAMPAIGNS_DIR", self.campaigns_dir),
            patch.object(characters, "CAMPAIGNS_DIR", self.campaigns_dir),
            patch.object(webui, "CAMPAIGNS_DIR", self.campaigns_dir),
            patch.object(webui, "Engine", FakeEngine),
            patch.object(webui, "validate_llm_config", lambda config: None),
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

    def _create_character_and_start(self):
        self.assertTrue(campaign.create_campaign("alpha", "dnd5e"))
        self.client.post("/api/campaigns/load", json={"name": "alpha"})
        for step in [
            "Aldric",
            "人类",
            "战士",
            "士兵",
            "Lawful Good",
            "手动输入",
            "STR=15 DEX=14 CON=13 INT=12 WIS=10 CHA=8",
            "运动, 求生",
            "是",
        ]:
            self.client.post("/api/chat", json={"message": step})

    def test_chat_turn_is_appended_to_session_log(self):
        self._create_character_and_start()
        response = self.client.post("/api/chat", json={"message": "我推开老宅的门"})
        self.assertTrue(response.get_json()["ok"])

        session_log = self.campaigns_dir / "alpha" / "session-log.md"
        content = session_log.read_text(encoding="utf-8")
        self.assertIn("我推开老宅的门", content)
        self.assertIn("GM回应：我推开老宅的门", content)

    def test_save_writes_summary_to_state_file(self):
        self._create_character_and_start()
        self.client.post("/api/chat", json={"message": "我推开老宅的门"})
        response = self.client.post("/api/campaigns/save")
        self.assertTrue(response.get_json()["ok"])

        state_file = self.campaigns_dir / "alpha" / "state.md"
        content = state_file.read_text(encoding="utf-8")
        self.assertIn("## Save Summary", content)
        self.assertIn("玩家进入了老宅", content)
        self.assertNotIn("State saved by user command", content)


if __name__ == "__main__":
    unittest.main()
