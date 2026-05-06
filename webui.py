from __future__ import annotations

import json
import os
import secrets
import threading
import tempfile
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, render_template, request, session
from werkzeug.utils import secure_filename

from campaign import (
    CAMPAIGNS_DIR,
    append_session_log_turn,
    create_campaign,
    delete_campaign,
    list_campaigns,
    save_campaign_state,
)
from characters import (
    COC_STATS,
    DND_ABILITY_METHOD_OPTIONS,
    DND_BACKGROUND_OPTIONS,
    DND_CLASS_OPTIONS,
    DND_CLASS_NAMES,
    DND_RACE_OPTIONS,
    DND_SKILL_DISPLAY,
    DND_STATS,
    build_coc_character_record,
    build_dnd_character_record,
    describe_dnd_options,
    describe_dnd_skills,
    generate_dnd_roll_arrays,
    list_all_characters,
    list_campaign_characters,
    list_system_characters,
    normalize_dnd_ability_method,
    parse_stat_block,
    resolve_character_choice,
    save_character_record,
)
from config import CONFIG_FILE, Config, get_config
from engine import Engine, LLMError
from importer import import_pdf
from llm import get_provider_spec, list_provider_options, normalize_provider, provider_base_url, validate_llm_config


BASE_DIR = Path(__file__).resolve().parent
WEBUI_TEMPLATES_DIR = BASE_DIR / "webui_templates"
WEBUI_STATIC_DIR = BASE_DIR / "webui_static"
DEFAULT_PORT = 7860
UPLOADS_DIR = Path(tempfile.gettempdir()) / "open-tabletop-gm" / "imports"
ALLOWED_IMPORT_EXTENSIONS = {".pdf", ".docx", ".md", ".txt"}

SYSTEM_META = {
    "dnd5e": {
        "label": "DND",
        "tagline": "英雄史诗",
        "theme": "dnd5e",
        "module_icon": "shield",
        "resource_label": "HP / AC / 先攻",
        "resource_value": "32 / 16 / +3",
        "resource_ratio": 0.72,
        "resource_meter": "heroic",
        "insight_label": "会话摘要",
        "insight_value": "集中维持中 / 法术位 3 / 4 / 死亡豁免 0 / 3",
        "specialized_panel": {
            "kind": "dnd5e",
            "title": "战斗摘要",
            "eyebrow": "专属组件",
            "battle_stats": [
                {"label": "Armor Class", "value": "16", "icon": "shield"},
                {"label": "Initiative", "value": "+3", "icon": "zap"},
                {"label": "Speed", "value": "30 FT", "icon": "footprints"},
            ],
            "resource_tracks": [
                {
                    "label": "Hit Points",
                    "value": "32 / 38",
                    "icon": "heart",
                    "segments": 10,
                    "filled": 8,
                    "tone": "heroic",
                },
                {
                    "label": "Spell Slots",
                    "value": "3 / 4",
                    "icon": "flame",
                    "segments": 4,
                    "filled": 3,
                    "tone": "warning",
                },
            ],
        },
    },
    "coc7e": {
        "label": "COC",
        "tagline": "克苏鲁调查",
        "theme": "coc7e",
        "module_icon": "brain",
        "resource_label": "SAN / HP / MP",
        "resource_value": "54 / 11 / 12",
        "resource_ratio": 0.54,
        "resource_meter": "sanity",
        "insight_label": "会话摘要",
        "insight_value": "神话侵蚀 14% / 单次失去 5+ 触发断点 / 当前检定困难成功",
        "specialized_panel": {
            "kind": "coc7e",
            "title": "理智摘要",
            "eyebrow": "专属组件",
            "sanity": {
                "label": "Sanity Fuse",
                "current": 54,
                "max": 70,
                "erosion": 14,
                "breakpoint": "单次失去 5+",
            },
            "d100_check": {
                "skill": "Spot Hidden",
                "target": 55,
                "roll": 24,
                "tens": 2,
                "ones": 4,
                "outcome": "困难成功",
                "hard": 27,
                "extreme": 11,
            },
        },
    },
}

DND_ALIGNMENT_OPTIONS = [
    ("Lawful Good", "守序善良", "讲原则、重承诺，倾向保护弱者。"),
    ("Neutral Good", "中立善良", "优先做正确的事，不被阵营教条束缚。"),
    ("Chaotic Good", "混乱善良", "自由而热心，愿意打破规则帮助别人。"),
    ("Lawful Neutral", "守序中立", "相信制度、契约或个人准则。"),
    ("True Neutral", "绝对中立", "务实、平衡，避免被极端立场裹挟。"),
    ("Chaotic Neutral", "混乱中立", "重视自由和直觉，行动难以预测。"),
    ("Lawful Evil", "守序邪恶", "冷静利用规则、权力和契约。"),
    ("Neutral Evil", "中立邪恶", "目标优先，少受道德和秩序约束。"),
    ("Chaotic Evil", "混乱邪恶", "冲动、破坏性强，适合黑暗角色。"),
    ("未指定", "未指定", "暂不固定阵营，先在游戏中自然塑形。"),
]

DND_SCORE_PRESETS = [
    ("STR=15 DEX=14 CON=13 INT=12 WIS=10 CHA=8", "力量前线", "适合战士、圣武士、野蛮人。"),
    ("STR=8 DEX=14 CON=13 INT=15 WIS=12 CHA=10", "学识施法", "适合法师、调查型角色。"),
    ("STR=8 DEX=15 CON=13 INT=12 WIS=14 CHA=10", "敏捷游侠", "适合游荡者、游侠、潜行路线。"),
    ("STR=10 DEX=12 CON=13 INT=8 WIS=14 CHA=15", "魅力领袖", "适合吟游诗人、术士、邪术师。"),
]

COC_ERA_OPTIONS = [
    ("1920年代", "1920年代", "经典调查年代，适合诡秘庄园与城市阴影。"),
    ("现代", "现代", "手机、网络与现代职业都可直接纳入故事。"),
    ("维多利亚时代", "维多利亚时代", "蒸汽、绅士俱乐部与早期神秘学氛围。"),
]

COC_OCCUPATION_OPTIONS = [
    ("私家侦探", "私家侦探", "擅长追踪线索、盘问和危险调查。"),
    ("记者", "记者", "适合采访、资料挖掘和社交突破。"),
    ("医生", "医生", "医学、急救和理性判断更强。"),
    ("教授", "教授", "知识面广，适合图书馆和学术线索。"),
    ("古董商", "古董商", "熟悉旧物、拍卖、人脉与赝品。"),
]

COC_AGE_OPTIONS = [
    ("25", "25 岁", "年轻、行动力强，适合冒进型调查员。"),
    ("35", "35 岁", "经验与体力比较均衡。"),
    ("45", "45 岁", "阅历更深，适合沉稳职业角色。"),
    ("55", "55 岁", "老练但行动力开始下降。"),
]

COC_SCORE_PRESETS = [
    (
        "STR=60 CON=55 SIZ=60 DEX=65 APP=50 INT=75 POW=60 EDU=70",
        "理性调查员",
        "高 INT/EDU，适合推理、资料检索和知识检定。",
    ),
    (
        "STR=50 CON=55 SIZ=55 DEX=60 APP=70 INT=65 POW=65 EDU=60",
        "社交突破者",
        "较高 APP/POW，适合谈判、采访和抗压。",
    ),
    (
        "STR=70 CON=65 SIZ=70 DEX=60 APP=45 INT=60 POW=55 EDU=55",
        "硬派行动派",
        "身体属性更强，适合危险现场和冲突场景。",
    ),
]


def _get_system_meta(system: str) -> dict[str, object]:
    return SYSTEM_META.get(system, SYSTEM_META["dnd5e"])


def _display_campaign_name(name: str, limit: int = 14) -> str:
    value = name.strip()
    if len(value) <= limit:
        return value
    return f"{value[:limit]}..."


@dataclass
class SessionState:
    engine: Engine | None = None
    campaign_name: str = ""
    campaign_system: str = ""
    chat_history: list[dict[str, str]] = field(default_factory=list)
    status_message: str = "等待载入战役。"
    active_character_id: str = ""
    active_character_name: str = ""
    guide_state: str = ""
    guide_context: dict[str, Any] = field(default_factory=dict)


_SESSION_STATES: dict[str, SessionState] = {}
_STATE_LOCK = threading.Lock()


app = Flask(
    __name__,
    template_folder=str(WEBUI_TEMPLATES_DIR),
    static_folder=str(WEBUI_STATIC_DIR),
    static_url_path="/static",
)
app.secret_key = os.environ.get("OPEN_TABLETOP_GM_WEBUI_SECRET", secrets.token_hex(32))


def _get_session_id() -> str:
    session_id = session.get("webui_session_id")
    if not session_id:
        session_id = secrets.token_hex(16)
        session["webui_session_id"] = session_id
    return session_id


def _get_session_state() -> SessionState:
    session_id = _get_session_id()
    with _STATE_LOCK:
        if session_id not in _SESSION_STATES:
            _SESSION_STATES[session_id] = SessionState()
        return _SESSION_STATES[session_id]


def _read_campaign_system(name: str) -> str:
    campaign_config = CAMPAIGNS_DIR / name / "campaign.json"
    if not campaign_config.exists():
        return "dnd5e"
    try:
        data = json.loads(campaign_config.read_text(encoding="utf-8"))
    except Exception:
        return "dnd5e"
    return data.get("system", "dnd5e")


def _reset_session_state(state: SessionState, status_message: str = "等待载入战役。") -> None:
    state.engine = None
    state.campaign_name = ""
    state.campaign_system = ""
    state.chat_history = []
    state.status_message = status_message
    state.active_character_id = ""
    state.active_character_name = ""
    state.guide_state = ""
    state.guide_context = {}


def _serialize_campaign(name: str) -> dict[str, str]:
    system = _read_campaign_system(name)
    system_meta = _get_system_meta(system)
    return {
        "name": name,
        "display_name": _display_campaign_name(name),
        "system": system,
        "system_label": system_meta["label"],
        "tagline": system_meta["tagline"],
    }


def _list_campaign_payload() -> list[dict[str, str]]:
    campaigns = sorted(list_campaigns(print_out=False))
    return [_serialize_campaign(name) for name in campaigns]


def _control_option(value: str, label: str, desc: str = "", eyebrow: str = "") -> dict[str, str]:
    return {
        "value": value,
        "label": label,
        "desc": desc,
        "eyebrow": eyebrow,
    }


def _options_from_meta(options: dict[str, dict[str, str]]) -> list[dict[str, str]]:
    return [
        _control_option(key, meta["label"], meta.get("desc", ""), key.upper())
        for key, meta in options.items()
    ]


def _options_from_pairs(options: list[tuple[str, str, str]]) -> list[dict[str, str]]:
    return [_control_option(value, label, desc) for value, label, desc in options]


def _score_preset_options(presets: list[tuple[str, str, str]]) -> list[dict[str, str]]:
    return [_control_option(value, label, desc, value) for value, label, desc in presets]


def _build_character_guide_controls(state: SessionState) -> dict[str, object]:
    context = state.guide_context
    step = context.get("step", "")
    form = context.get("form") if isinstance(context.get("form"), dict) else {}

    if state.guide_state == "choose_existing":
        return {
            "title": "选择角色入口",
            "subtitle": "检测到已有可用角色，可以直接启用，也可以创建新角色。",
            "mode": "cards",
            "options": [
                _control_option("是", "使用已有角色", "直接进入当前战役。"),
                _control_option("否", "创建新角色", "打开角色创建流程。"),
            ],
            "input_label": "也可以输入“是”或“否”",
        }

    if state.guide_state == "select_existing":
        characters = list_campaign_characters(state.campaign_name)
        return {
            "title": "选择已有角色",
            "subtitle": "点击角色卡即可启用，也可以继续输入编号或角色名。",
            "mode": "cards",
            "options": [
                _control_option(str(index), character["name"], character.get("summary", ""), character.get("origin_campaign", ""))
                for index, character in enumerate(characters, start=1)
            ],
            "input_label": "输入编号或角色名",
        }

    if state.guide_state == "confirm_character":
        return {
            "title": "确认角色卡",
            "subtitle": "保存后会进入战役开场。",
            "mode": "confirm",
            "options": [
                _control_option("是", "确认并开始", "保存角色，进入冒险。"),
                _control_option("否", "重新创建", "放弃当前草稿。"),
            ],
            "input_label": "也可以输入“是”或“否”",
        }

    if state.guide_state != "create_character":
        return {}

    if state.campaign_system == "coc7e":
        if step == "name":
            return {
                "title": "调查员姓名",
                "subtitle": "输入姓名，或者从范例名开始再自行调整。",
                "mode": "chips",
                "options": _options_from_pairs([
                    ("Harvey Walters", "Harvey Walters", "经典调查员名。"),
                    ("林秋石", "林秋石", "现代中文调查员名。"),
                    ("Eleanor Price", "Eleanor Price", "适合维多利亚或学术背景。"),
                ]),
                "input_label": "调查员姓名",
            }
        if step == "era":
            return {
                "title": "选择时代",
                "subtitle": "时代会影响职业、线索形式和叙事质感。",
                "mode": "cards",
                "options": _options_from_pairs(COC_ERA_OPTIONS),
                "input_label": "自定义时代",
            }
        if step == "occupation":
            return {
                "title": "选择职业",
                "subtitle": "职业决定调查路径和角色在队伍中的功能。",
                "mode": "cards",
                "options": _options_from_pairs(COC_OCCUPATION_OPTIONS),
                "input_label": "自定义职业",
            }
        if step == "age":
            return {
                "title": "选择年龄",
                "subtitle": "年龄会影响移动力，也会改变角色阅历感。",
                "mode": "chips",
                "options": _options_from_pairs(COC_AGE_OPTIONS),
                "input_label": "自定义年龄",
            }
        if step == "scores":
            return {
                "title": "选择属性模板",
                "subtitle": "先选一个调查员原型，之后仍可用输入框提交自定义八项属性。",
                "mode": "cards",
                "options": _score_preset_options(COC_SCORE_PRESETS),
                "input_label": "自定义属性",
            }
        if step == "skills_summary":
            return {
                "title": "关键技能摘要",
                "subtitle": "选择一个技能组合，或直接输入你想强调的技能。",
                "mode": "chips",
                "options": _options_from_pairs([
                    ("图书馆使用 70，侦查 60，聆听 55", "资料调查", "适合线索和档案检索。"),
                    ("心理学 65，话术 60，信誉 50", "社交突破", "适合访谈与人际推进。"),
                    ("急救 60，医学 50，自然学 55", "现场支援", "适合危险现场和伤情处理。"),
                ]),
                "input_label": "自定义关键技能",
            }
        if step == "backstory":
            return {
                "title": "背景钩子",
                "subtitle": "选择一个动机作为开局抓手，后续可继续细化。",
                "mode": "cards",
                "options": _options_from_pairs([
                    ("正在追查一宗多年未破的失踪案。", "未破旧案", "适合调查与个人执念。"),
                    ("收到旧友求助信后赶来此地。", "旧友求助", "适合快速卷入事件。"),
                    ("为一件来历不明的古物寻找真相。", "神秘古物", "适合克苏鲁式物件线索。"),
                ]),
                "input_label": "自定义背景",
            }
        return {}

    if step == "name":
        return {
            "title": "角色姓名",
            "subtitle": "输入姓名，或者先选一个范例名快速开始。",
            "mode": "chips",
            "options": _options_from_pairs([
                ("Aldric", "Aldric", "适合骑士、战士。"),
                ("Vesper", "Vesper", "适合游荡者、法师。"),
                ("Mira", "Mira", "适合游侠、牧师。"),
            ]),
            "input_label": "角色姓名",
        }
    if step == "race":
        return {
            "title": "选择种族",
            "subtitle": "点击卡片即可选择，输入框仍支持中文名或英文键名。",
            "mode": "cards",
            "options": _options_from_meta(DND_RACE_OPTIONS),
            "input_label": "自定义种族",
        }
    if step == "class":
        return {
            "title": "选择职业",
            "subtitle": "职业决定生命骰、豁免熟练和玩法定位。",
            "mode": "cards",
            "options": _options_from_meta(DND_CLASS_OPTIONS),
            "input_label": "职业名",
        }
    if step == "background":
        return {
            "title": "选择背景",
            "subtitle": "背景决定角色进入故事的社会身份。",
            "mode": "cards",
            "options": _options_from_meta(DND_BACKGROUND_OPTIONS),
            "input_label": "背景名",
        }
    if step == "alignment":
        return {
            "title": "选择阵营",
            "subtitle": "阵营不是束缚，只是开局时的行为倾向。",
            "mode": "chips",
            "options": _options_from_pairs(DND_ALIGNMENT_OPTIONS),
            "input_label": "自定义阵营",
        }
    if step == "ability_method":
        return {
            "title": "选择属性生成方式",
            "subtitle": "想要随机命运、平衡规划或直接自定义都可以。",
            "mode": "cards",
            "options": _options_from_meta(DND_ABILITY_METHOD_OPTIONS),
            "input_label": "属性生成方式",
        }
    if step == "scores":
        method = form.get("ability_method", "manual")
        roll_arrays = context.get("roll_arrays") or []
        roll_options = [
            _control_option(
                f"STR={array[0]} DEX={array[1]} CON={array[2]} INT={array[3]} WIS={array[4]} CHA={array[5]}",
                f"掷骰数组 {index}",
                "点击后按 STR/DEX/CON/INT/WIS/CHA 顺序分配。",
                ", ".join(str(score) for score in array),
            )
            for index, array in enumerate(roll_arrays, start=1)
        ]
        return {
            "title": "选择属性模板",
            "subtitle": "先用一个模板开局；想精调时仍可直接输入六维。",
            "mode": "cards",
            "options": roll_options or _score_preset_options(DND_SCORE_PRESETS),
            "input_label": "自定义六维",
            "meta": {"method": method},
        }
    if step == "proficiencies":
        return {
            "title": "选择熟练技能",
            "subtitle": "可多选，点“提交选择”后继续确认角色卡。",
            "mode": "multi_select",
            "submit_label": "提交技能",
            "options": [
                _control_option(skill, meta["label"], meta.get("desc", ""), skill)
                for skill, meta in DND_SKILL_DISPLAY.items()
            ],
            "input_label": "也可以输入逗号分隔的技能",
        }
    return {}


def _serialize_character_guide(state: SessionState) -> dict[str, object]:
    return {
        "active": bool(state.guide_state),
        "state": state.guide_state,
        "step": state.guide_context.get("step", ""),
        "system": state.campaign_system,
        "controls": _build_character_guide_controls(state),
    }


def _find_preview_character(state: SessionState, campaign_characters: list[dict[str, Any]]) -> dict[str, Any] | None:
    if state.active_character_id:
        for character in campaign_characters:
            if character.get("id") == state.active_character_id:
                return character
    pending_record = state.guide_context.get("pending_record")
    if isinstance(pending_record, dict):
        return pending_record
    return None


def _build_dnd_system_meta(base_meta: dict[str, Any], character: dict[str, Any]) -> dict[str, Any]:
    details = character.get("details") or {}
    scores = details.get("scores") or {}
    modifiers = details.get("modifiers") or {}
    proficiencies = details.get("proficiencies") or []
    hp = int(details.get("hp") or 0)
    ac = int(details.get("armor_class") or 10)
    proficiency_bonus = int(details.get("proficiency_bonus") or 2)
    hit_die = int(details.get("hit_die") or 8)
    class_display = str(details.get("class_display") or "冒险者")
    race = str(details.get("race") or "未知种族")
    background = str(details.get("background") or "未知背景")
    system_meta = deepcopy(base_meta)
    system_meta["resource_value"] = f"{hp} / {ac} / {modifiers.get('DEX', '+0')}"
    system_meta["resource_ratio"] = 1
    system_meta["insight_value"] = f"{race} / {class_display} / 背景：{background}"
    system_meta["specialized_panel"] = {
        "kind": "dnd5e",
        "title": f"{character.get('name', '角色')} 作战面板",
        "eyebrow": "当前角色",
        "battle_stats": [
            {"label": "Armor Class", "value": str(ac), "icon": "shield"},
            {"label": "Initiative", "value": str(modifiers.get("DEX", "+0")), "icon": "zap"},
            {"label": "Proficiency", "value": f"+{proficiency_bonus}", "icon": "star"},
        ],
        "resource_tracks": [
            {
                "label": "Hit Points",
                "value": f"{hp} / {hp}",
                "icon": "heart",
                "segments": max(1, hp),
                "filled": max(1, hp),
                "tone": "heroic",
            },
            {
                "label": "Skill Proficiencies",
                "value": str(len(proficiencies)),
                "icon": "scroll",
                "segments": max(4, len(proficiencies) or 1),
                "filled": max(0, len(proficiencies)),
                "tone": "warning",
            },
        ],
    }
    if scores:
        system_meta["insight_value"] = (
            f"{race} / {class_display} / STR {scores.get('STR', '-')}"
            f" DEX {scores.get('DEX', '-')} CON {scores.get('CON', '-')}"
        )
    return system_meta


def _build_coc_system_meta(base_meta: dict[str, Any], character: dict[str, Any]) -> dict[str, Any]:
    details = character.get("details") or {}
    scores = details.get("scores") or {}
    derived = details.get("derived") or {}
    san = int(derived.get("san") or 0)
    hp = int(derived.get("hp") or 0)
    mp = int(derived.get("mp") or 0)
    mov = int(derived.get("mov") or 0)
    build = derived.get("build", 0)
    damage_bonus = derived.get("damage_bonus", "0")
    era = str(details.get("era") or "未知时代")
    occupation = str(details.get("occupation") or "未知职业")
    target = int(scores.get("INT") or scores.get("POW") or san or 50)
    roll = min(99, max(1, target // 2 if target else 50))
    system_meta = deepcopy(base_meta)
    system_meta["resource_value"] = f"{san} / {hp} / {mp}"
    system_meta["resource_ratio"] = 1 if san else 0
    system_meta["insight_value"] = f"{era} / {occupation} / MOV {mov} / Build {build} / DB {damage_bonus}"
    system_meta["specialized_panel"] = {
        "kind": "coc7e",
        "title": f"{character.get('name', '调查员')} 状态摘要",
        "eyebrow": "当前角色",
        "sanity": {
            "label": "Sanity Fuse",
            "current": san,
            "max": san,
            "erosion": 0,
            "breakpoint": f"单次失去 5+ / 当日累计 {max(1, san // 5)}+",
        },
        "d100_check": {
            "skill": "INT 灵感",
            "target": target,
            "roll": roll,
            "tens": roll // 10,
            "ones": roll % 10,
            "outcome": "可用于常规成功阈值参考",
            "hard": target // 2,
            "extreme": target // 5,
        },
    }
    return system_meta


def _build_system_meta_for_state(
    state: SessionState,
    current_campaign: dict[str, Any] | None,
    campaign_characters: list[dict[str, Any]],
) -> dict[str, Any]:
    system = state.campaign_system if current_campaign else "dnd5e"
    base_meta = _get_system_meta(system)
    preview_character = _find_preview_character(state, campaign_characters)
    if not preview_character:
        return base_meta
    if system == "coc7e":
        return _build_coc_system_meta(base_meta, preview_character)
    return _build_dnd_system_meta(base_meta, preview_character)


def _serialize_state() -> dict[str, object]:
    state = _get_session_state()
    config = get_config(prefer_env=False)
    provider_spec = get_provider_spec(config.provider, config.base_url)
    current_campaign = None
    system_meta = _get_system_meta("dnd5e")
    campaign_characters: list[dict[str, Any]] = []
    active_character = None

    if state.campaign_name:
        campaign_characters = list_campaign_characters(state.campaign_name)
        current_campaign = {
            "name": state.campaign_name,
            "system": state.campaign_system,
            "system_label": _get_system_meta(state.campaign_system)["label"],
        }
        system_meta = _build_system_meta_for_state(state, current_campaign, campaign_characters)
    if state.active_character_name:
        active_character = {
            "id": state.active_character_id,
            "name": state.active_character_name,
        }

    return {
        "config": {
            "api_key_configured": bool(config.api_key.strip()),
            "provider": config.provider,
            "provider_label": provider_spec["label"],
            "base_url": config.base_url,
            "model": config.model,
            "config_path": str(CONFIG_FILE),
        },
        "campaigns": _list_campaign_payload(),
        "current_campaign": current_campaign,
        "chat_history": state.chat_history,
        "status_message": state.status_message,
        "chat_ready": state.engine is not None,
        "system_meta": system_meta,
        "campaign_characters": campaign_characters,
        "my_characters": list_all_characters(state.campaign_name or None),
        "character_guide": _serialize_character_guide(state),
        "active_character": active_character,
    }


def _asset_version() -> int:
    asset_paths = [
        WEBUI_STATIC_DIR / "css" / "webui.css",
        WEBUI_STATIC_DIR / "js" / "app.js",
        WEBUI_TEMPLATES_DIR / "index.html",
    ]
    return max(int(path.stat().st_mtime) for path in asset_paths if path.exists())


def _json_error(message: str, status_code: int = 400):
    response = jsonify({"ok": False, "message": message, "state": _serialize_state()})
    response.status_code = status_code
    return response


def _campaign_exists(name: str) -> bool:
    return (CAMPAIGNS_DIR / name).exists()


def _load_stored_api_key() -> str:
    if not CONFIG_FILE.exists():
        return ""
    try:
        data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except Exception:
        return ""
    return str(data.get("api_key", "")).strip()


def save_config(provider: str, api_key: str, model: str, api_key_modified: bool = False, base_url: str = "") -> str:
    config = Config()
    config.provider = normalize_provider(provider, base_url)
    config.base_url = provider_base_url(config.provider, base_url)
    if api_key_modified:
        config.api_key = api_key.strip()
    else:
        config.api_key = _load_stored_api_key()
    config.model = model.strip()
    config.save()
    key_message = "API Key 已更新。" if api_key_modified else "已保留现有 API Key。"
    return f"配置已保存到 {CONFIG_FILE}。{key_message}"


def create_new_campaign(name: str, system: str) -> tuple[bool, str]:
    if not name.strip():
        return False, "战役名称不能为空。"

    if create_campaign(name.strip(), system):
        return True, f"战役 '{name.strip()}' 已创建，规则系统为 {_get_system_meta(system)['label']}。"
    return False, f"创建战役 '{name.strip()}' 失败，可能已存在或模板缺失。"


def save_current_campaign() -> str:
    state = _get_session_state()
    if not state.campaign_name:
        raise ValueError("当前没有已加载的战役可保存。")

    summary = None
    if state.engine and hasattr(state.engine, "summarize_for_save"):
        summary = state.engine.summarize_for_save()
    save_campaign_state(state.campaign_name, summary)
    state.status_message = f"已保存战役：{state.campaign_name}"
    return state.status_message


def delete_selected_campaign(name: str) -> str:
    campaign_name = (name or "").strip()
    if not campaign_name:
        raise ValueError("请先选择一个战役。")

    deleted = delete_campaign(campaign_name)
    if not deleted:
        raise ValueError(f"战役 '{campaign_name}' 不存在或已被删除。")

    state = _get_session_state()
    if state.campaign_name == campaign_name:
        _reset_session_state(state, f"战役 '{campaign_name}' 已删除，当前会话已重置。")
    else:
        state.status_message = f"战役 '{campaign_name}' 已删除。"
    return state.status_message


def _is_yes(value: str) -> bool:
    return value.strip().lower() in {"y", "yes", "是", "好", "好的", "确认", "使用", "继续"}


def _is_no(value: str) -> bool:
    return value.strip().lower() in {"n", "no", "否", "不要", "不用", "新建", "创建"}


def _character_list_text(campaign_name: str) -> str:
    characters = list_campaign_characters(campaign_name)
    lines = []
    for index, character in enumerate(characters, start=1):
        lines.append(f"{index}. {character['name']} | {character['summary']}")
    return "\n".join(lines)


def _start_character_creation(state: SessionState) -> str:
    state.guide_state = "create_character"
    state.guide_context = {"system": state.campaign_system, "step": "name", "form": {"player_name": "玩家"}}
    if state.campaign_system == "coc7e":
        return (
            "当前还没有可用于这个 CoC 规则战役的调查员，我们现在开始创建调查员。\n\n"
            "第 1 步：请先输入角色姓名。"
        )
    return (
        "当前还没有可用于这个 DND 规则战役的角色，我们现在开始创建角色。\n\n"
        "第 1 步：请先输入角色姓名。"
    )


def _start_existing_character_choice(state: SessionState) -> str:
    state.guide_state = "choose_existing"
    state.guide_context = {}
    system_label = _get_system_meta(state.campaign_system)["label"]
    return (
        f"检测到你已经创建过可用于这个 {system_label} 战役的角色。\n\n"
        f"{_character_list_text(state.campaign_name)}\n\n"
        "是否使用已有角色？请输入“是”或“否”。"
    )


def _format_score_block(scores: dict[str, Any]) -> str:
    return ", ".join(f"{key}={value}" for key, value in scores.items())


def _finalize_character_selection(state: SessionState, character_summary: dict[str, Any], newly_created: bool) -> str:
    state.active_character_id = str(character_summary.get("id", ""))
    state.active_character_name = str(character_summary.get("name", ""))
    state.guide_state = ""
    state.guide_context = {}
    if not state.engine:
        raise ValueError("引擎未初始化。")
    intro = state.engine.start_session_intro(state.active_character_name)
    state.status_message = f"正在进行：{state.campaign_name} / {state.active_character_name}"
    prefix = "已创建并启用角色" if newly_created else "已启用角色"
    return f"{prefix} **{state.active_character_name}**。\n\n{intro}"


def _prompt_for_dnd_step(step: str, context: dict[str, Any]) -> str:
    if step == "name":
        return "第 1 步：请输入角色姓名。"
    if step == "race":
        return (
            "第 2 步：请选择种族。你可以直接输入英文键名，也可以输入中文名。\n\n"
            f"{describe_dnd_options(DND_RACE_OPTIONS)}"
        )
    if step == "class":
        return (
            "第 3 步：请选择职业。你可以直接输入英文键名，也可以输入中文名。\n\n"
            f"{describe_dnd_options(DND_CLASS_OPTIONS)}"
        )
    if step == "background":
        return (
            "第 4 步：请选择背景。你可以直接输入英文键名，也可以输入中文名。\n\n"
            f"{describe_dnd_options(DND_BACKGROUND_OPTIONS)}"
        )
    if step == "alignment":
        return "第 5 步：请输入阵营；若不关心可输入“未指定”。"
    if step == "ability_method":
        return (
            "第 6 步：请选择属性生成方式。你可以输入英文键名，也可以直接输入中文。\n\n"
            f"{describe_dnd_options(DND_ABILITY_METHOD_OPTIONS)}"
        )
    if step == "scores":
        method = context["form"].get("ability_method", "manual")
        if method == "roll":
            arrays = context.get("roll_arrays") or generate_dnd_roll_arrays()
            context["roll_arrays"] = arrays
            lines = [f"数组 {index}: {array}" for index, array in enumerate(arrays, start=1)]
            return (
                "第 7 步：请选择一个数组并分配六维。请直接回复一行属性，例如：\n"
                "`STR=15 DEX=14 CON=13 INT=12 WIS=10 CHA=8`\n\n"
                + "\n".join(lines)
            )
        if method == "pointbuy":
            return (
                "第 7 步：请按 27 点购点输入六维，范围 8-15，例如：\n"
                "`STR=15 DEX=14 CON=13 INT=10 WIS=12 CHA=8`"
            )
        return (
            "第 7 步：请直接输入六维，格式例如：\n"
            "`STR=15 DEX=14 CON=13 INT=12 WIS=10 CHA=8`"
        )
    if step == "proficiencies":
        return (
            "第 8 步：请输入熟练技能，使用逗号分隔，可输入英文或中文，也可以留空。\n\n"
            f"{describe_dnd_skills()}"
        )
    if step == "confirm":
        record = context["pending_record"]
        details = record["details"]
        return (
            "请确认以下角色信息，输入“是”保存并开始冒险，输入“否”则重新建角。\n\n"
            f"- 姓名：{record['name']}\n"
            f"- 玩家：{record['player_name']}\n"
            f"- 种族/职业：{details['race']} / {details['class_display']}\n"
            f"- 背景：{details['background']}\n"
            f"- 阵营：{details['alignment']}\n"
            f"- 属性：{_format_score_block(details['scores'])}\n"
            f"- 熟练技能：{', '.join(details['proficiencies']) or '无'}"
        )
    return "请继续输入。"


def _prompt_for_coc_step(step: str, context: dict[str, Any]) -> str:
    if step == "name":
        return "第 1 步：请输入调查员姓名。"
    if step == "era":
        return "第 2 步：请输入时代或背景，例如 1920年代、现代、维多利亚时代。"
    if step == "occupation":
        return "第 3 步：请输入职业，例如 私家侦探、记者、医生、教授。"
    if step == "age":
        return "第 4 步：请输入年龄。"
    if step == "scores":
        return (
            "第 5 步：请一次性输入八项属性，格式例如：\n"
            "`STR=60 CON=55 SIZ=65 DEX=70 APP=50 INT=75 POW=60 EDU=70`"
        )
    if step == "skills_summary":
        return "第 6 步：请输入关键技能或专长摘要，使用逗号分隔，例如“图书馆使用 70，侦查 60，聆听 55”。"
    if step == "backstory":
        return "第 7 步：请输入一段简短背景。"
    if step == "confirm":
        record = context["pending_record"]
        details = record["details"]
        derived = details["derived"]
        return (
            "请确认以下调查员信息，输入“是”保存并开始冒险，输入“否”则重新建角。\n\n"
            f"- 姓名：{record['name']}\n"
            f"- 玩家：{record['player_name']}\n"
            f"- 时代/职业：{details['era']} / {details['occupation']}\n"
            f"- 年龄：{details['age']}\n"
            f"- 属性：{_format_score_block(details['scores'])}\n"
            f"- HP/MP/SAN：{derived['hp']} / {derived['mp']} / {derived['san']}\n"
            f"- MOV/Build/DB：{derived['mov']} / {derived['build']} / {derived['damage_bonus']}"
        )
    return "请继续输入。"


def _handle_choose_existing(state: SessionState, user_message: str) -> str:
    if _is_yes(user_message):
        characters = list_campaign_characters(state.campaign_name)
        if len(characters) == 1:
            return _finalize_character_selection(state, characters[0], newly_created=False)
        state.guide_state = "select_existing"
        return (
            "请选择要使用的角色，输入编号或角色名。\n\n"
            f"{_character_list_text(state.campaign_name)}"
        )
    if _is_no(user_message):
        return _start_character_creation(state)
    return "请回复“是”或“否”。如果要使用已有角色请输入“是”，否则请输入“否”。"


def _handle_select_existing(state: SessionState, user_message: str) -> str:
    selected = resolve_character_choice(state.campaign_name, user_message)
    if not selected:
        return (
            "没有找到对应角色，请输入编号或角色名。\n\n"
            f"{_character_list_text(state.campaign_name)}"
        )
    return _finalize_character_selection(state, selected, newly_created=False)


def _handle_dnd_creation(state: SessionState, user_message: str) -> str:
    context = state.guide_context
    form = context.setdefault("form", {})
    step = context.get("step", "name")
    value = user_message.strip()

    if step == "name":
        form["name"] = value
        context["step"] = "race"
        return _prompt_for_dnd_step("race", context)
    if step == "race":
        form["race"] = value
        context["step"] = "class"
        return _prompt_for_dnd_step("class", context)
    if step == "class":
        form["class"] = value
        context["step"] = "background"
        return _prompt_for_dnd_step("background", context)
    if step == "background":
        form["background"] = value
        context["step"] = "alignment"
        return _prompt_for_dnd_step("alignment", context)
    if step == "alignment":
        form["alignment"] = value or "未指定"
        context["step"] = "ability_method"
        return _prompt_for_dnd_step("ability_method", context)
    if step == "ability_method":
        method = normalize_dnd_ability_method(value)
        if method not in DND_ABILITY_METHOD_OPTIONS:
            return _prompt_for_dnd_step("ability_method", context)
        form["ability_method"] = method
        context["step"] = "scores"
        return _prompt_for_dnd_step("scores", context)
    if step == "scores":
        try:
            form["scores"] = {stat: int(score) for stat, score in parse_stat_block(value, DND_STATS).items()}
            pending = build_dnd_character_record(state.campaign_name, form)
        except Exception as exc:
            return f"属性输入有误：{exc}\n\n{_prompt_for_dnd_step('scores', context)}"
        context["pending_record"] = pending
        context["step"] = "proficiencies"
        return _prompt_for_dnd_step("proficiencies", context)
    if step == "proficiencies":
        form["proficiencies"] = value
        try:
            pending = build_dnd_character_record(state.campaign_name, form)
        except Exception as exc:
            return f"建角失败：{exc}\n\n{_prompt_for_dnd_step('proficiencies', context)}"
        state.guide_state = "confirm_character"
        state.guide_context = {"system": state.campaign_system, "pending_record": pending}
        return _prompt_for_dnd_step("confirm", state.guide_context)
    return "建角流程出现未知状态，请重新加载战役。"


def _handle_coc_creation(state: SessionState, user_message: str) -> str:
    context = state.guide_context
    form = context.setdefault("form", {})
    step = context.get("step", "name")
    value = user_message.strip()

    if step == "name":
        form["name"] = value
        context["step"] = "era"
        return _prompt_for_coc_step("era", context)
    if step == "era":
        form["era"] = value
        context["step"] = "occupation"
        return _prompt_for_coc_step("occupation", context)
    if step == "occupation":
        form["occupation"] = value
        context["step"] = "age"
        return _prompt_for_coc_step("age", context)
    if step == "age":
        try:
            form["age"] = int(value)
        except ValueError:
            return "年龄必须是整数。"
        context["step"] = "scores"
        return _prompt_for_coc_step("scores", context)
    if step == "scores":
        try:
            form["scores"] = {stat: int(score) for stat, score in parse_stat_block(value, COC_STATS).items()}
        except Exception as exc:
            return f"属性输入有误：{exc}\n\n{_prompt_for_coc_step('scores', context)}"
        context["step"] = "skills_summary"
        return _prompt_for_coc_step("skills_summary", context)
    if step == "skills_summary":
        form["skills_summary"] = value
        context["step"] = "backstory"
        return _prompt_for_coc_step("backstory", context)
    if step == "backstory":
        form["backstory"] = value
        try:
            pending = build_coc_character_record(state.campaign_name, form)
        except Exception as exc:
            return f"建角失败：{exc}\n\n{_prompt_for_coc_step('backstory', context)}"
        state.guide_state = "confirm_character"
        state.guide_context = {"system": state.campaign_system, "pending_record": pending}
        return _prompt_for_coc_step("confirm", state.guide_context)
    return "建角流程出现未知状态，请重新加载战役。"


def _handle_confirm_character(state: SessionState, user_message: str) -> str:
    if _is_yes(user_message):
        pending = state.guide_context["pending_record"]
        summary = save_character_record(pending)
        return _finalize_character_selection(state, summary, newly_created=True)
    if _is_no(user_message):
        return _start_character_creation(state)
    return "请回复“是”保存角色并开始冒险，或回复“否”重新创建。"


def _handle_character_guide(state: SessionState, user_message: str) -> str:
    if state.guide_state == "choose_existing":
        return _handle_choose_existing(state, user_message)
    if state.guide_state == "select_existing":
        return _handle_select_existing(state, user_message)
    if state.guide_state == "create_character":
        if state.campaign_system == "coc7e":
            return _handle_coc_creation(state, user_message)
        return _handle_dnd_creation(state, user_message)
    if state.guide_state == "confirm_character":
        return _handle_confirm_character(state, user_message)
    raise ValueError("当前没有进行中的角色引导。")


def load_selected_campaign(name: str) -> str:
    if not name:
        raise ValueError("请先选择一个战役。")

    config = get_config(prefer_env=False)
    config_error = validate_llm_config(config)
    if config_error:
        raise ValueError(config_error)

    state = _get_session_state()
    engine = Engine(name, prefer_env_config=False)
    state.engine = engine
    state.campaign_name = name
    state.campaign_system = _read_campaign_system(name)
    state.chat_history = []
    state.active_character_id = ""
    state.active_character_name = ""
    state.guide_context = {}
    campaign_characters = list_system_characters(state.campaign_system, name)
    if campaign_characters:
        guide_message = _start_existing_character_choice(state)
    else:
        guide_message = _start_character_creation(state)
    state.chat_history.append({"role": "assistant", "content": guide_message})
    state.status_message = f"已加载战役：{name}"
    return state.status_message


def chat_with_gm(user_message: str) -> str:
    state = _get_session_state()
    if not state.engine:
        raise ValueError("请先在战役大厅加载一个战役。")

    clean_message = user_message.strip()
    if not clean_message:
        raise ValueError("输入不能为空。")

    if state.guide_state:
        state.chat_history.append({"role": "user", "content": clean_message})
        response = _handle_character_guide(state, clean_message)
        state.chat_history.append({"role": "assistant", "content": response})
        return response

    if not state.active_character_name:
        raise ValueError("请先完成角色选择或创建。")

    response = state.engine.chat(clean_message)
    state.chat_history.append({"role": "user", "content": clean_message})
    state.chat_history.append({"role": "assistant", "content": response})
    append_session_log_turn(state.campaign_name, clean_message, response)
    state.status_message = f"正在进行：{state.campaign_name} / {state.active_character_name}"
    return response


@app.get("/")
def index():
    snapshot = _serialize_state()
    return render_template(
        "index.html",
        snapshot=snapshot,
        systems=SYSTEM_META,
        provider_options=list_provider_options(),
        asset_version=_asset_version(),
    )


@app.get("/api/state")
def get_state():
    return jsonify({"ok": True, "state": _serialize_state()})


@app.post("/api/config")
def save_config_route():
    payload = request.get_json(silent=True) or {}
    try:
        message = save_config(
            payload.get("provider", ""),
            payload.get("api_key", ""),
            payload.get("model", ""),
            bool(payload.get("api_key_modified", False)),
            payload.get("base_url", ""),
        )
    except Exception as exc:
        return _json_error(f"保存配置失败: {exc}", 500)

    state = _get_session_state()
    if state.engine is not None:
        state.engine.refresh_config()
    state.status_message = message
    return jsonify({"ok": True, "message": message, "state": _serialize_state()})


@app.post("/api/campaigns")
def create_campaign_route():
    payload = request.get_json(silent=True) or {}
    try:
        ok, message = create_new_campaign(
            payload.get("name", ""),
            payload.get("system", "dnd5e"),
        )
    except Exception as exc:
        return _json_error(f"创建战役失败: {exc}", 500)

    if not ok:
        return _json_error(message, 400)

    state = _get_session_state()
    state.status_message = message
    return jsonify({"ok": True, "message": message, "state": _serialize_state()})


@app.post("/api/campaigns/save")
def save_campaign_route():
    try:
        message = save_current_campaign()
    except ValueError as exc:
        return _json_error(str(exc), 400)
    except LLMError as exc:
        return _json_error(f"生成保存摘要失败: {exc}", 502)
    except Exception as exc:
        return _json_error(f"保存战役失败: {exc}", 500)

    return jsonify({"ok": True, "message": message, "state": _serialize_state()})


@app.post("/api/import-module")
def import_module_route():
    campaign_name = (request.form.get("name") or "").strip()
    system = (request.form.get("system") or "dnd5e").strip()
    source = request.files.get("source")

    if not campaign_name:
        return _json_error("请先填写导入目标战役名称。", 400)
    if source is None or not source.filename:
        return _json_error("请先选择一个 PDF、DOCX、MD 或 TXT 文件。", 400)

    suffix = Path(source.filename).suffix.lower()
    if suffix not in ALLOWED_IMPORT_EXTENSIONS:
        return _json_error("仅支持 PDF、DOCX、MD 和 TXT 文件。", 400)

    config = get_config(prefer_env=False)
    config_error = validate_llm_config(config)
    if config_error:
        return _json_error(config_error, 400)

    if not _campaign_exists(campaign_name):
        created = create_campaign(campaign_name, system)
        if not created:
            return _json_error("创建导入目标战役失败，请检查名称是否重复。", 400)

    original_name = Path(source.filename).name
    safe_stem = secure_filename(Path(original_name).stem) or "module"
    safe_name = f"{safe_stem}{suffix}"
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    upload_path = UPLOADS_DIR / f"{secrets.token_hex(8)}-{safe_name}"
    source.save(upload_path)

    try:
        ok, message = import_pdf(campaign_name, str(upload_path), prefer_env_config=False)
    finally:
        if upload_path.exists():
            upload_path.unlink()

    if not ok:
        return _json_error(f"导入模组失败：{message}", 500)

    state = _get_session_state()
    state.status_message = f"模组已导入到战役：{campaign_name}"
    return jsonify({"ok": True, "message": message, "state": _serialize_state()})


@app.post("/api/campaigns/load")
def load_campaign_route():
    payload = request.get_json(silent=True) or {}
    try:
        message = load_selected_campaign(payload.get("name", ""))
    except ValueError as exc:
        return _json_error(str(exc), 400)
    except Exception as exc:
        return _json_error(f"加载战役失败: {exc}", 500)

    return jsonify({"ok": True, "message": message, "state": _serialize_state()})


@app.delete("/api/campaigns/<path:name>")
def delete_campaign_route(name: str):
    try:
        message = delete_selected_campaign(name)
    except ValueError as exc:
        return _json_error(str(exc), 400)
    except Exception as exc:
        return _json_error(f"删除战役失败: {exc}", 500)

    return jsonify({"ok": True, "message": message, "state": _serialize_state()})


@app.post("/api/chat")
def chat_route():
    payload = request.get_json(silent=True) or {}
    try:
        response = chat_with_gm(payload.get("message", ""))
    except ValueError as exc:
        return _json_error(str(exc), 400)
    except LLMError as exc:
        return _json_error(f"引擎通信错误: {exc}", 502)
    except Exception as exc:
        return _json_error(f"引擎通信错误: {exc}", 500)

    return jsonify({"ok": True, "message": response, "state": _serialize_state()})


if __name__ == "__main__":
    port = int(os.environ.get("OPEN_TABLETOP_GM_WEBUI_PORT", str(DEFAULT_PORT)))
    app.run(host="127.0.0.1", port=port, debug=False)
