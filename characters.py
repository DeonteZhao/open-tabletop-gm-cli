from __future__ import annotations

import json
import random
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from campaign import CAMPAIGNS_DIR
from systems.coc7e.character import build_coc_character
from systems.dnd5e import character as dnd5e_character


DND_STATS = ["STR", "DEX", "CON", "INT", "WIS", "CHA"]
COC_STATS = ["STR", "CON", "SIZ", "DEX", "APP", "INT", "POW", "EDU"]
DND_POINT_BUY_COST = {8: 0, 9: 1, 10: 2, 11: 3, 12: 4, 13: 5, 14: 7, 15: 9}
DND_SKILL_NAMES = sorted(dnd5e_character.SKILLS)
DND_CLASS_NAMES = sorted(dnd5e_character.HIT_DICE)


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def slugify_character_name(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower())
    slug = slug.strip("-")
    return slug or "character"


def campaign_characters_dir(campaign_name: str) -> Path:
    return CAMPAIGNS_DIR / campaign_name / "characters"


def ensure_campaign_characters_dir(campaign_name: str) -> Path:
    directory = campaign_characters_dir(campaign_name)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _character_paths(campaign_name: str, slug: str) -> tuple[Path, Path]:
    base = ensure_campaign_characters_dir(campaign_name) / slug
    return base.with_suffix(".md"), base.with_suffix(".json")


def _read_json_file(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def save_character_record(record: dict[str, Any]) -> dict[str, Any]:
    campaign_name = str(record["campaign"])
    slug = str(record["slug"])
    markdown_path, json_path = _character_paths(campaign_name, slug)
    summary = dict(record)
    markdown = str(summary.pop("markdown"))
    summary["sheet_path"] = str(markdown_path)
    summary["json_path"] = str(json_path)

    markdown_path.write_text(markdown, encoding="utf-8")
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def load_character_summary(campaign_name: str, slug: str) -> dict[str, Any] | None:
    _, json_path = _character_paths(campaign_name, slug)
    payload = _read_json_file(json_path)
    if not payload:
        return None
    return _with_compatibility(payload, campaign_name)


def load_character_markdown(campaign_name: str, slug: str) -> str:
    markdown_path, _ = _character_paths(campaign_name, slug)
    if not markdown_path.exists():
        raise FileNotFoundError(f"角色卡不存在：{markdown_path}")
    return markdown_path.read_text(encoding="utf-8")


def _with_compatibility(payload: dict[str, Any], current_campaign: str | None = None) -> dict[str, Any]:
    data = dict(payload)
    if current_campaign:
        data["is_compatible_with_current_campaign"] = data.get("campaign") == current_campaign
    else:
        data["is_compatible_with_current_campaign"] = False
    return data


def list_campaign_characters(campaign_name: str) -> list[dict[str, Any]]:
    directory = campaign_characters_dir(campaign_name)
    if not directory.exists():
        return []

    records: list[dict[str, Any]] = []
    for json_path in sorted(directory.glob("*.json")):
        payload = _read_json_file(json_path)
        if not payload:
            continue
        records.append(_with_compatibility(payload, campaign_name))
    return sorted(records, key=lambda item: (item.get("updated_at", ""), item.get("name", "")), reverse=True)


def list_all_characters(current_campaign: str | None = None) -> list[dict[str, Any]]:
    if not CAMPAIGNS_DIR.exists():
        return []

    records: list[dict[str, Any]] = []
    for campaign_dir in sorted(CAMPAIGNS_DIR.iterdir()):
        if not campaign_dir.is_dir():
            continue
        character_dir = campaign_dir / "characters"
        if not character_dir.exists():
            continue
        for json_path in sorted(character_dir.glob("*.json")):
            payload = _read_json_file(json_path)
            if not payload:
                continue
            records.append(_with_compatibility(payload, current_campaign))
    return sorted(records, key=lambda item: (item.get("updated_at", ""), item.get("name", "")), reverse=True)


def resolve_character_choice(campaign_name: str, raw_value: str) -> dict[str, Any] | None:
    value = raw_value.strip()
    if not value:
        return None

    characters = list_campaign_characters(campaign_name)
    if not characters:
        return None

    if value.isdigit():
        index = int(value) - 1
        if 0 <= index < len(characters):
            return characters[index]

    lowered = value.casefold()
    for record in characters:
        if lowered in {
            str(record.get("id", "")).casefold(),
            str(record.get("slug", "")).casefold(),
            str(record.get("name", "")).casefold(),
        }:
            return record
    return None


def generate_dnd_roll_arrays() -> list[list[int]]:
    arrays: list[list[int]] = []
    for _ in range(3):
        scores = []
        for _ in range(6):
            rolls = sorted((random.randint(1, 6) for _ in range(4)), reverse=True)
            scores.append(sum(rolls[:3]))
        arrays.append(sorted(scores, reverse=True))
    return arrays


def parse_stat_block(raw_value: str, stat_names: list[str]) -> dict[str, int]:
    matches = re.findall(r"([A-Za-z]+)\s*=\s*(\d+)", raw_value.upper())
    data = {key: int(value) for key, value in matches if key in stat_names}
    missing = [key for key in stat_names if key not in data]
    if missing:
        raise ValueError(f"缺少属性：{', '.join(missing)}。请使用 `STAT=值` 格式一次性提交。")
    return data


def parse_choice_list(raw_value: str) -> list[str]:
    items = [item.strip() for item in re.split(r"[,，\n]+", raw_value) if item.strip()]
    return items


def validate_dnd_scores(scores: dict[str, int], method: str) -> None:
    for stat, value in scores.items():
        if value < 3 or value > 20:
            raise ValueError(f"{stat}={value} 超出允许范围。")

    if method != "pointbuy":
        return

    total_cost = 0
    for stat in DND_STATS:
        value = scores[stat]
        if value not in DND_POINT_BUY_COST:
            raise ValueError(f"{stat}={value} 不符合 point buy 规则，允许范围为 8-15。")
        total_cost += DND_POINT_BUY_COST[value]
    if total_cost != 27:
        raise ValueError(f"point buy 总成本必须为 27，当前为 {total_cost}。")


def _normalize_dnd_class(value: str) -> str:
    cleaned = value.strip().lower()
    if cleaned not in dnd5e_character.HIT_DICE:
        raise ValueError(f"暂不支持职业：{value}。可选：{', '.join(DND_CLASS_NAMES)}。")
    return cleaned


def _normalize_dnd_proficiencies(raw_value: str) -> list[str]:
    selected = []
    valid_map = {name.casefold(): name for name in DND_SKILL_NAMES}
    for item in parse_choice_list(raw_value):
        normalized = valid_map.get(item.casefold())
        if normalized and normalized not in selected:
            selected.append(normalized)
    return selected


def _format_modifier(value: int) -> str:
    return f"+{value}" if value >= 0 else str(value)


def _build_dnd_markdown(record: dict[str, Any], details: dict[str, Any]) -> str:
    scores = details["scores"]
    mods = details["modifiers"]
    saving_throws = details["saving_throws"]
    skills = details["skills"]
    proficiencies = details["proficiencies"]
    lines = [
        f"# {record['name']}",
        f"**Player:** {record['player_name']}  **Campaign:** {record['campaign']}  **System:** DND 5e",
        "",
        "## Identity",
        f"- **Race:** {details['race']} | **Class:** {details['class_display']} | **Level:** 1 | **Background:** {details['background']}",
        f"- **Alignment:** {details['alignment']} | **XP:** 0 / 300",
        f"- **Creation Method:** {details['ability_method_label']}",
        "",
        "## Ability Scores",
        "| STR | DEX | CON | INT | WIS | CHA |",
        "|-----|-----|-----|-----|-----|-----|",
        f"| {scores['STR']} ({mods['STR']}) | {scores['DEX']} ({mods['DEX']}) | {scores['CON']} ({mods['CON']}) | {scores['INT']} ({mods['INT']}) | {scores['WIS']} ({mods['WIS']}) | {scores['CHA']} ({mods['CHA']}) |",
        "",
        "## Combat Stats",
        f"- **HP:** {details['hp']} / {details['hp']} | **Temp HP:** 0",
        f"- **AC:** {details['armor_class']} | **Initiative:** {mods['DEX']} | **Speed:** 30 FT",
        f"- **Hit Dice:** 1d{details['hit_die']} (remaining: 1)",
        "",
        "## Saving Throws",
        "| Stat | Bonus |",
        "|------|-------|",
    ]
    for stat in DND_STATS:
        lines.append(f"| {stat} | {saving_throws[stat]} |")

    lines.extend(
        [
            "",
            "## Skills",
            "| Skill | Ability | Bonus | Proficient |",
            "|-------|---------|-------|-----------|",
        ]
    )
    for skill_name in DND_SKILL_NAMES:
        skill = skills[skill_name]
        marker = "Yes" if skill_name in proficiencies else "No"
        lines.append(f"| {skill_name} | {skill['ability']} | {skill['bonus']} | {marker} |")

    lines.extend(
        [
            "",
            "## Features & Notes",
            f"- **Summary:** {record['summary']}",
            "- **Equipment:** 待补充",
            "- **Backstory:** 待补充",
            "",
        ]
    )
    return "\n".join(lines)


def build_dnd_character_record(campaign_name: str, data: dict[str, Any]) -> dict[str, Any]:
    name = str(data["name"]).strip()
    player_name = str(data["player_name"]).strip()
    race = str(data["race"]).strip()
    char_class = _normalize_dnd_class(str(data["class"]).strip())
    background = str(data["background"]).strip()
    alignment = str(data.get("alignment", "")).strip() or "未指定"
    ability_method = str(data["ability_method"]).strip().lower()
    scores = {stat: int(value) for stat, value in dict(data["scores"]).items()}
    validate_dnd_scores(scores, ability_method)
    proficiencies = _normalize_dnd_proficiencies(str(data.get("proficiencies", "")))

    hit_die = dnd5e_character.HIT_DICE[char_class]
    proficiency_bonus = dnd5e_character.PROF_BONUS[1]
    modifiers = {stat: _format_modifier(dnd5e_character.mod(scores[stat])) for stat in DND_STATS}
    saving_throws: dict[str, str] = {}
    for stat in DND_STATS:
        base_bonus = dnd5e_character.mod(scores[stat])
        if stat in dnd5e_character.SAVE_PROFS.get(char_class, []):
            base_bonus += proficiency_bonus
        saving_throws[stat] = _format_modifier(base_bonus)

    skill_rows: dict[str, dict[str, str]] = {}
    for skill_name, ability in dnd5e_character.SKILLS.items():
        bonus = dnd5e_character.mod(scores[ability])
        if skill_name in proficiencies:
            bonus += proficiency_bonus
        skill_rows[skill_name] = {"ability": ability, "bonus": _format_modifier(bonus)}

    hp = hit_die + dnd5e_character.mod(scores["CON"])
    details = {
        "race": race,
        "class": char_class,
        "class_display": char_class.title(),
        "background": background,
        "alignment": alignment,
        "ability_method": ability_method,
        "ability_method_label": {
            "roll": "4d6 去最低",
            "pointbuy": "27 点购点",
            "manual": "手动输入",
        }.get(ability_method, ability_method),
        "scores": scores,
        "modifiers": modifiers,
        "proficiencies": proficiencies,
        "saving_throws": saving_throws,
        "skills": skill_rows,
        "hit_die": hit_die,
        "hp": hp,
        "armor_class": 10 + dnd5e_character.mod(scores["DEX"]),
    }
    summary = f"{race} {char_class.title()} 1级 | 背景：{background}"
    record = {
        "id": str(uuid.uuid4()),
        "name": name,
        "slug": slugify_character_name(name),
        "system": "dnd5e",
        "system_label": "DND",
        "campaign": campaign_name,
        "player_name": player_name,
        "status": "ready",
        "summary": summary,
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
        "details": details,
    }
    record["markdown"] = _build_dnd_markdown(record, details)
    return record


def build_coc_character_record(campaign_name: str, data: dict[str, Any]) -> dict[str, Any]:
    payload = build_coc_character(
        campaign_name=campaign_name,
        name=str(data["name"]).strip(),
        player_name=str(data["player_name"]).strip(),
        era=str(data["era"]).strip(),
        occupation=str(data["occupation"]).strip(),
        age=int(data["age"]),
        scores={stat: int(value) for stat, value in dict(data["scores"]).items()},
        skills_summary=str(data.get("skills_summary", "")).strip(),
        backstory=str(data.get("backstory", "")).strip(),
    )
    payload["slug"] = slugify_character_name(payload["name"])
    return payload
