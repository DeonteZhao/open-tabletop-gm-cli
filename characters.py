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

DND_RACE_OPTIONS = {
    "human": {"label": "人类", "desc": "适应力强，背景灵活，适合几乎所有职业路线。"},
    "elf": {"label": "精灵", "desc": "敏锐、优雅，常见于游侠、游荡者与施法职业。"},
    "dwarf": {"label": "矮人", "desc": "坚韧耐打，适合前线战斗与防守型角色。"},
    "halfling": {"label": "半身人", "desc": "机敏而幸运，常见于潜行与社交型角色。"},
    "dragonborn": {"label": "龙裔", "desc": "带有龙族血统，气势强，适合近战与威慑路线。"},
    "gnome": {"label": "侏儒", "desc": "聪明而好奇，常见于法师、工匠或研究者。"},
    "halfelf": {"label": "半精灵", "desc": "兼具魅力与适应力，擅长社交和多面发展。"},
    "halforc": {"label": "半兽人", "desc": "力量与凶猛兼备，适合野蛮人或战士。"},
    "tiefling": {"label": "提夫林", "desc": "带有异界血统，天生神秘，常见于术士与魅力型角色。"},
}

DND_CLASS_OPTIONS = {
    "barbarian": {"label": "野蛮人", "desc": "怒气驱动的近战猛将，血厚、伤害高。"},
    "bard": {"label": "吟游诗人", "desc": "以表演、知识和法术支援队伍的全能型角色。"},
    "cleric": {"label": "牧师", "desc": "侍奉神祇的施法者，兼具治疗、辅助和神圣打击。"},
    "druid": {"label": "德鲁伊", "desc": "亲近自然，能施法并化身野兽。"},
    "fighter": {"label": "战士", "desc": "武器专精的稳定前线，是最直观的战斗职业。"},
    "monk": {"label": "武僧", "desc": "依靠身法与气运战斗，擅长机动与连击。"},
    "paladin": {"label": "圣武士", "desc": "以誓言和信念作战，兼具防御、治疗与爆发。"},
    "ranger": {"label": "游侠", "desc": "擅长追踪、生存和远近兼修的荒野猎手。"},
    "rogue": {"label": "游荡者", "desc": "擅长潜行、巧技与精准爆发，适合侦查与渗透。"},
    "sorcerer": {"label": "术士", "desc": "天生拥有魔力，法术爆发强，资源管理直接。"},
    "warlock": {"label": "邪术师", "desc": "与超自然存在立约换取力量，风格鲜明。"},
    "wizard": {"label": "法师", "desc": "依赖知识与法术书的经典施法者，法术选择最丰富。"},
}

DND_BACKGROUND_OPTIONS = {
    "acolyte": {"label": "侍僧", "desc": "来自宗教团体，熟悉教会、人脉与仪式。"},
    "charlatan": {"label": "骗子", "desc": "靠话术与伪装生存，擅长欺骗和身份切换。"},
    "criminal": {"label": "罪犯", "desc": "熟悉地下世界、潜行、黑市和见不得光的手段。"},
    "entertainer": {"label": "艺人", "desc": "擅长演出、取悦观众和吸引注意力。"},
    "folkhero": {"label": "民间英雄", "desc": "出身平民却做过壮举，容易赢得普通人的信任。"},
    "guildartisan": {"label": "行会工匠", "desc": "有稳定手艺和行业关系，适合社会化发展。"},
    "hermit": {"label": "隐士", "desc": "独居避世，往往掌握隐秘知识或个人启示。"},
    "noble": {"label": "贵族", "desc": "出身上层社会，拥有礼仪、资源和社会关系。"},
    "outlander": {"label": "荒野流浪者", "desc": "擅长野外求生、追踪和远行。"},
    "sage": {"label": "贤者", "desc": "学识丰富，适合知识调查与奥秘研究。"},
    "sailor": {"label": "水手", "desc": "熟悉航海、港口和粗粝的集体生活。"},
    "soldier": {"label": "士兵", "desc": "接受过军事训练，懂纪律、战术和军旅关系。"},
    "urchin": {"label": "街头孤儿", "desc": "从底层求生，擅长潜行、偷盗和城市穿梭。"},
}

DND_ABILITY_METHOD_OPTIONS = {
    "roll": {"label": "掷骰", "desc": "使用 4d6 去最低，随机性强，更有命运感。"},
    "pointbuy": {"label": "购点", "desc": "27 点购点，平衡稳定，适合精确规划。"},
    "manual": {"label": "手动输入", "desc": "直接给出属性，适合你已经想好具体数值。"},
}

DND_SKILL_DISPLAY = {
    "Acrobatics": {"label": "体操", "desc": "平衡、翻滚、脱困等灵巧动作。"},
    "Animal Handling": {"label": "驯兽", "desc": "安抚、控制或理解动物。"},
    "Arcana": {"label": "奥秘", "desc": "有关法术、魔法与异界知识。"},
    "Athletics": {"label": "运动", "desc": "攀爬、跳跃、游泳和纯体能表现。"},
    "Deception": {"label": "欺瞒", "desc": "撒谎、误导与伪装。"},
    "History": {"label": "历史", "desc": "文明、战争、王国与过去事件知识。"},
    "Insight": {"label": "洞悉", "desc": "判断他人动机和情绪变化。"},
    "Intimidation": {"label": "威吓", "desc": "以气势、威胁或压迫迫使对方退让。"},
    "Investigation": {"label": "调查", "desc": "搜查线索、推理痕迹、分析信息。"},
    "Medicine": {"label": "医药", "desc": "诊断伤病、急救与基础医学判断。"},
    "Nature": {"label": "自然", "desc": "野外、生物、地形与自然现象知识。"},
    "Perception": {"label": "察觉", "desc": "主动发现声音、动静、陷阱与异常。"},
    "Performance": {"label": "表演", "desc": "歌唱、演奏、戏剧和公开表演。"},
    "Persuasion": {"label": "游说", "desc": "以真诚、礼仪或逻辑说服他人。"},
    "Religion": {"label": "宗教", "desc": "神祇、仪式、圣职与神圣传统知识。"},
    "Sleight of Hand": {"label": "巧手", "desc": "扒窃、藏物、手上把戏。"},
    "Stealth": {"label": "隐匿", "desc": "潜行、藏身、无声移动。"},
    "Survival": {"label": "求生", "desc": "追踪、觅食、辨路和野外生存。"},
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _normalize_lookup_key(value: str) -> str:
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", value.strip().casefold())


def slugify_character_name(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower())
    slug = slug.strip("-")
    return slug or "character"


def campaign_characters_dir(campaign_name: str) -> Path:
    return CAMPAIGNS_DIR / campaign_name / "characters"


def shared_characters_root_dir() -> Path:
    return CAMPAIGNS_DIR.parent / "characters"


def system_characters_dir(system_name: str) -> Path:
    return shared_characters_root_dir() / system_name


def ensure_system_characters_dir(system_name: str) -> Path:
    directory = system_characters_dir(system_name)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def ensure_campaign_characters_dir(campaign_name: str) -> Path:
    directory = campaign_characters_dir(campaign_name)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _shared_character_paths(system_name: str, slug: str) -> tuple[Path, Path]:
    base = ensure_system_characters_dir(system_name) / slug
    return base.with_suffix(".md"), base.with_suffix(".json")


def _legacy_character_paths(campaign_name: str, slug: str) -> tuple[Path, Path]:
    base = ensure_campaign_characters_dir(campaign_name) / slug
    return base.with_suffix(".md"), base.with_suffix(".json")


def _read_json_file(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def save_character_record(record: dict[str, Any]) -> dict[str, Any]:
    system_name = str(record["system"])
    slug = str(record["slug"])
    markdown_path, json_path = _shared_character_paths(system_name, slug)
    summary = dict(record)
    markdown = str(summary.pop("markdown"))
    summary.setdefault("origin_campaign", summary.get("campaign", ""))
    summary["sheet_path"] = str(markdown_path)
    summary["json_path"] = str(json_path)

    markdown_path.write_text(markdown, encoding="utf-8")
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def _read_campaign_system(campaign_name: str) -> str | None:
    config_path = CAMPAIGNS_DIR / campaign_name / "campaign.json"
    if not config_path.exists():
        return None
    payload = _read_json_file(config_path)
    if not payload:
        return None
    system_name = str(payload.get("system", "")).strip()
    return system_name or None


def _resolve_current_system(current_campaign_or_system: str | None = None) -> str | None:
    value = (current_campaign_or_system or "").strip()
    if not value:
        return None
    if value in {"dnd5e", "coc7e"}:
        return value
    return _read_campaign_system(value)


def _load_character_summary_by_system(system_name: str, slug: str) -> dict[str, Any] | None:
    _, json_path = _shared_character_paths(system_name, slug)
    payload = _read_json_file(json_path)
    if payload:
        return payload
    for campaign_dir in sorted(CAMPAIGNS_DIR.iterdir()) if CAMPAIGNS_DIR.exists() else []:
        if not campaign_dir.is_dir():
            continue
        _, legacy_json_path = _legacy_character_paths(campaign_dir.name, slug)
        payload = _read_json_file(legacy_json_path)
        if payload and payload.get("system") == system_name:
            return payload
    return None


def load_character_summary(campaign_name: str, slug: str) -> dict[str, Any] | None:
    system_name = _resolve_current_system(campaign_name)
    if not system_name:
        return None
    payload = _load_character_summary_by_system(system_name, slug)
    if not payload:
        return None
    return _with_compatibility(payload, campaign_name)


def load_character_markdown(campaign_name: str, slug: str) -> str:
    summary = load_character_summary(campaign_name, slug)
    if not summary:
        raise FileNotFoundError(f"角色卡不存在：{slug}")
    return load_character_markdown_from_record(summary)


def load_character_markdown_from_record(record: dict[str, Any]) -> str:
    candidates: list[Path] = []
    sheet_path = str(record.get("sheet_path", "")).strip()
    if sheet_path:
        candidates.append(Path(sheet_path))
    system_name = str(record.get("system", "")).strip()
    slug = str(record.get("slug", "")).strip()
    campaign_name = str(record.get("campaign", "")).strip()
    if system_name and slug:
        shared_markdown_path, _ = _shared_character_paths(system_name, slug)
        candidates.append(shared_markdown_path)
    if campaign_name and slug:
        legacy_markdown_path, _ = _legacy_character_paths(campaign_name, slug)
        candidates.append(legacy_markdown_path)

    for path in candidates:
        if path.exists():
            return path.read_text(encoding="utf-8")
    raise FileNotFoundError(f"角色卡不存在：{record.get('name', slug)}")


def _with_compatibility(payload: dict[str, Any], current_campaign: str | None = None) -> dict[str, Any]:
    data = dict(payload)
    current_system = _resolve_current_system(current_campaign)
    data["is_compatible_with_current_campaign"] = bool(current_system and data.get("system") == current_system)
    data.setdefault("origin_campaign", data.get("campaign", ""))
    return data


def _iter_all_character_payloads() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    seen_keys: set[str] = set()

    if shared_characters_root_dir().exists():
        for system_dir in sorted(shared_characters_root_dir().iterdir()):
            if not system_dir.is_dir():
                continue
            for json_path in sorted(system_dir.glob("*.json")):
                payload = _read_json_file(json_path)
                if not payload:
                    continue
                key = str(payload.get("id") or f"{payload.get('system')}:{payload.get('slug')}:{payload.get('campaign')}")
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                records.append(payload)

    if CAMPAIGNS_DIR.exists():
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
                key = str(payload.get("id") or f"{payload.get('system')}:{payload.get('slug')}:{payload.get('campaign')}")
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                records.append(payload)

    return records


def list_system_characters(system_name: str, current_campaign: str | None = None) -> list[dict[str, Any]]:
    if not system_name:
        return []
    records = []
    for payload in _iter_all_character_payloads():
        if payload.get("system") != system_name:
            continue
        records.append(_with_compatibility(payload, current_campaign or system_name))
    return sorted(records, key=lambda item: (item.get("updated_at", ""), item.get("name", "")), reverse=True)


def list_campaign_characters(campaign_name: str) -> list[dict[str, Any]]:
    system_name = _resolve_current_system(campaign_name)
    if not system_name:
        return []
    return list_system_characters(system_name, campaign_name)


def list_all_characters(current_campaign: str | None = None) -> list[dict[str, Any]]:
    records = [_with_compatibility(payload, current_campaign) for payload in _iter_all_character_payloads()]
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


def _build_alias_map(options: dict[str, dict[str, str]], extra_aliases: dict[str, list[str]] | None = None) -> dict[str, str]:
    alias_map: dict[str, str] = {}
    for canonical, meta in options.items():
        keys = {canonical, meta["label"], f"{canonical} {meta['label']}", f"{meta['label']} {canonical}"}
        for key in keys:
            alias_map[_normalize_lookup_key(key)] = canonical
    if extra_aliases:
        for canonical, aliases in extra_aliases.items():
            for alias in aliases:
                alias_map[_normalize_lookup_key(alias)] = canonical
    return alias_map


_DND_RACE_ALIAS_MAP = _build_alias_map(
    DND_RACE_OPTIONS,
    {
        "halfelf": ["half elf", "半精灵"],
        "halforc": ["half orc", "半兽人"],
        "dragonborn": ["dragon born", "龙裔"],
        "tiefling": ["提夫林", "魔裔"],
    },
)
_DND_CLASS_ALIAS_MAP = _build_alias_map(
    DND_CLASS_OPTIONS,
    {
        "fighter": ["warrior", "战士"],
        "rogue": ["thief", "盗贼", "游荡者"],
        "sorcerer": ["sorceror", "术士"],
        "warlock": ["邪术师"],
        "cleric": ["priest", "牧师"],
        "paladin": ["圣骑士", "圣武士"],
        "ranger": ["游侠"],
        "wizard": ["mage", "法师"],
        "barbarian": ["野蛮人"],
        "bard": ["吟游诗人"],
        "druid": ["德鲁伊"],
        "monk": ["武僧"],
    },
)
_DND_BACKGROUND_ALIAS_MAP = _build_alias_map(
    DND_BACKGROUND_OPTIONS,
    {
        "guildartisan": ["guild artisan", "行会工匠"],
        "folkhero": ["folk hero", "民间英雄"],
        "outlander": ["荒野流浪者"],
        "urchin": ["街头孤儿"],
    },
)
_DND_METHOD_ALIAS_MAP = _build_alias_map(
    DND_ABILITY_METHOD_OPTIONS,
    {
        "roll": ["掷骰", "骰点", "随机", "4d6"],
        "pointbuy": ["点购", "购点", "point buy", "27点"],
        "manual": ["手动", "手填", "直接输入", "自定义"],
    },
)
_DND_SKILL_ALIAS_MAP = _build_alias_map(
    DND_SKILL_DISPLAY,
    {
        "Animal Handling": ["驯养动物"],
        "Arcana": ["奥术", "奥秘"],
        "History": ["历史"],
        "Insight": ["洞察", "洞悉"],
        "Investigation": ["侦查", "调查"],
        "Medicine": ["医疗", "医药"],
        "Nature": ["自然"],
        "Perception": ["观察", "察觉"],
        "Persuasion": ["说服", "游说"],
        "Religion": ["宗教"],
        "Sleight of Hand": ["手上把戏", "巧手"],
        "Stealth": ["潜行", "隐匿"],
        "Survival": ["生存", "求生"],
        "Intimidation": ["威胁", "威吓"],
        "Performance": ["表演"],
        "Acrobatics": ["杂技", "体操"],
        "Athletics": ["运动"],
        "Deception": ["欺诈", "欺瞒"],
    },
)


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
    cleaned = _DND_CLASS_ALIAS_MAP.get(_normalize_lookup_key(value), value.strip().lower())
    if cleaned not in dnd5e_character.HIT_DICE:
        raise ValueError(f"暂不支持职业：{value}。可选：{', '.join(DND_CLASS_NAMES)}。")
    return cleaned


def normalize_dnd_race(value: str) -> str:
    cleaned = _DND_RACE_ALIAS_MAP.get(_normalize_lookup_key(value))
    if cleaned:
        return DND_RACE_OPTIONS[cleaned]["label"]
    return value.strip()


def normalize_dnd_background(value: str) -> str:
    cleaned = _DND_BACKGROUND_ALIAS_MAP.get(_normalize_lookup_key(value))
    if cleaned:
        return DND_BACKGROUND_OPTIONS[cleaned]["label"]
    return value.strip()


def normalize_dnd_ability_method(value: str) -> str:
    cleaned = _DND_METHOD_ALIAS_MAP.get(_normalize_lookup_key(value))
    if cleaned:
        return cleaned
    return value.strip().lower()


def _normalize_dnd_proficiencies(raw_value: str) -> list[str]:
    selected = []
    for item in parse_choice_list(raw_value):
        normalized = _DND_SKILL_ALIAS_MAP.get(_normalize_lookup_key(item))
        if normalized and normalized not in selected:
            selected.append(normalized)
    return selected


def describe_dnd_options(options: dict[str, dict[str, str]]) -> str:
    return "\n".join(f"- {key}: {meta['label']}。{meta['desc']}" for key, meta in options.items())


def describe_dnd_skills() -> str:
    return "\n".join(
        f"- {skill}: {meta['label']}。{meta['desc']}" for skill, meta in DND_SKILL_DISPLAY.items()
    )


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
    race = normalize_dnd_race(str(data["race"]).strip())
    char_class = _normalize_dnd_class(str(data["class"]).strip())
    background = normalize_dnd_background(str(data["background"]).strip())
    alignment = str(data.get("alignment", "")).strip() or "未指定"
    ability_method = normalize_dnd_ability_method(str(data["ability_method"]).strip())
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
        "class_display": DND_CLASS_OPTIONS.get(char_class, {}).get("label", char_class.title()),
        "background": background,
        "alignment": alignment,
        "ability_method": ability_method,
        "ability_method_label": DND_ABILITY_METHOD_OPTIONS.get(ability_method, {}).get("label", ability_method),
        "scores": scores,
        "modifiers": modifiers,
        "proficiencies": proficiencies,
        "saving_throws": saving_throws,
        "skills": skill_rows,
        "proficiency_bonus": proficiency_bonus,
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
