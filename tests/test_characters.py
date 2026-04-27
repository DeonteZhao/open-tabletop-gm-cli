from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import campaign
import characters
from systems.coc7e import character as coc_character


class CharacterStorageTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.campaigns_dir = Path(self.temp_dir.name) / "campaigns"
        self.campaigns_dir.mkdir()
        self.patches = [
            patch.object(campaign, "CAMPAIGNS_DIR", self.campaigns_dir),
            patch.object(characters, "CAMPAIGNS_DIR", self.campaigns_dir),
        ]
        for patcher in self.patches:
            patcher.start()

    def tearDown(self):
        for patcher in reversed(self.patches):
            patcher.stop()
        self.temp_dir.cleanup()

    def test_slugify_character_name(self):
        self.assertEqual(characters.slugify_character_name("Harvey Walters"), "harvey-walters")
        self.assertEqual(characters.slugify_character_name("  "), "character")

    def test_save_and_list_character_records(self):
        record = characters.build_dnd_character_record(
            "alpha",
            {
                "name": "Aldric",
                "player_name": "Tester",
                "race": "人类",
                "class": "战士",
                "background": "士兵",
                "alignment": "Lawful Good",
                "ability_method": "手动输入",
                "scores": {"STR": 15, "DEX": 14, "CON": 13, "INT": 12, "WIS": 10, "CHA": 8},
                "proficiencies": "运动, 求生",
            },
        )
        saved = characters.save_character_record(record)
        campaign_records = characters.list_campaign_characters("alpha")
        all_records = characters.list_all_characters("alpha")

        self.assertEqual(saved["name"], "Aldric")
        self.assertEqual(len(campaign_records), 1)
        self.assertEqual(campaign_records[0]["slug"], "aldric")
        self.assertTrue(campaign_records[0]["is_compatible_with_current_campaign"])
        self.assertEqual(len(all_records), 1)
        self.assertEqual(all_records[0]["campaign"], "alpha")
        self.assertEqual(all_records[0]["details"]["class_display"], "战士")

    def test_coc_character_helper_derives_stats(self):
        payload = coc_character.build_coc_character(
            campaign_name="haunted-house",
            name="Harvey Walters",
            player_name="Tester",
            era="1920s",
            occupation="Private Investigator",
            age=35,
            scores={"STR": 60, "CON": 50, "SIZ": 60, "DEX": 55, "APP": 60, "INT": 75, "POW": 70, "EDU": 70},
            skills_summary="图书馆使用 70，侦查 60",
            backstory="一名总是追查怪事的私家侦探。",
        )
        derived = payload["details"]["derived"]

        self.assertEqual(derived["hp"], 11)
        self.assertEqual(derived["mp"], 14)
        self.assertEqual(derived["san"], 70)
        self.assertEqual(derived["mov"], 8)


if __name__ == "__main__":
    unittest.main()
