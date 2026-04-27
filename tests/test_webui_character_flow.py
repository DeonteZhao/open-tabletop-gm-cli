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

    def refresh_config(self):
        return None

    def set_active_character(self, character_name: str):
        self.active_character_name = character_name

    def start_session_intro(self, active_character_name: str) -> str:
        self.active_character_name = active_character_name
        return f"开场：{active_character_name} 进入冒险。"

    def chat(self, user_input: str) -> str:
        return f"GM回应：{user_input}"


class WebUiCharacterFlowTests(unittest.TestCase):
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

    def test_load_campaign_without_character_enters_creation_guide(self):
        self.assertTrue(campaign.create_campaign("alpha", "dnd5e"))

        response = self.client.post("/api/campaigns/load", json={"name": "alpha"})
        payload = response.get_json()

        self.assertTrue(payload["ok"])
        self.assertTrue(payload["state"]["character_guide"]["active"])
        self.assertEqual(payload["state"]["character_guide"]["state"], "create_character")
        self.assertIn("开始创建角色", payload["state"]["chat_history"][0]["content"])

    def test_character_creation_flow_persists_character_and_starts_session(self):
        self.assertTrue(campaign.create_campaign("alpha", "dnd5e"))
        self.client.post("/api/campaigns/load", json={"name": "alpha"})
        steps = [
            "Aldric",
            "人类",
            "战士",
            "士兵",
            "Lawful Good",
            "手动输入",
            "STR=15 DEX=14 CON=13 INT=12 WIS=10 CHA=8",
            "运动, 求生",
            "是",
        ]

        payload = None
        for step in steps:
            payload = self.client.post("/api/chat", json={"message": step}).get_json()

        self.assertIsNotNone(payload)
        self.assertFalse(payload["state"]["character_guide"]["active"])
        self.assertEqual(payload["state"]["active_character"]["name"], "Aldric")
        self.assertEqual(payload["state"]["my_characters"][0]["name"], "Aldric")
        self.assertIn("开场：Aldric 进入冒险。", payload["message"])

    def test_load_campaign_with_existing_character_prompts_reuse(self):
        self.assertTrue(campaign.create_campaign("alpha", "dnd5e"))
        summary = characters.save_character_record(
            characters.build_dnd_character_record(
                "alpha",
                {
                    "name": "Vesper",
                    "player_name": "Tester",
                    "race": "Elf",
                    "class": "wizard",
                    "background": "Sage",
                    "alignment": "Neutral",
                    "ability_method": "manual",
                    "scores": {"STR": 8, "DEX": 14, "CON": 13, "INT": 15, "WIS": 12, "CHA": 10},
                    "proficiencies": "Arcana, History",
                },
            )
        )
        self.assertEqual(summary["name"], "Vesper")

        payload = self.client.post("/api/campaigns/load", json={"name": "alpha"}).get_json()
        self.assertEqual(payload["state"]["character_guide"]["state"], "choose_existing")
        self.assertIn("是否使用已有角色", payload["state"]["chat_history"][0]["content"])

        reply = self.client.post("/api/chat", json={"message": "是"}).get_json()
        self.assertFalse(reply["state"]["character_guide"]["active"])
        self.assertEqual(reply["state"]["active_character"]["name"], "Vesper")


if __name__ == "__main__":
    unittest.main()
