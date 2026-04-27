from __future__ import annotations

import json
import os
import secrets
import threading
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, render_template, request, session
from werkzeug.utils import secure_filename

from campaign import (
    CAMPAIGNS_DIR,
    create_campaign,
    delete_campaign,
    list_campaigns,
    save_campaign_state,
)
from characters import (
    COC_STATS,
    DND_CLASS_NAMES,
    DND_SKILL_NAMES,
    DND_STATS,
    build_coc_character_record,
    build_dnd_character_record,
    generate_dnd_roll_arrays,
    list_all_characters,
    list_campaign_characters,
    parse_stat_block,
    resolve_character_choice,
    save_character_record,
)
from config import CONFIG_FILE, Config, get_config
from engine import Engine
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


def _serialize_character_guide(state: SessionState) -> dict[str, object]:
    return {
        "active": bool(state.guide_state),
        "state": state.guide_state,
        "step": state.guide_context.get("step", ""),
        "system": state.campaign_system,
    }


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
        system_meta = _get_system_meta(state.campaign_system)
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


def save_config(provider: str, api_key: str, model: str, api_key_modified: bool = False) -> str:
    config = Config()
    config.provider = normalize_provider(provider)
    config.base_url = provider_base_url(config.provider)
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

    save_campaign_state(state.campaign_name)
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
    state.guide_context = {"system": state.campaign_system, "step": "name", "form": {}}
    if state.campaign_system == "coc7e":
        return (
            "当前战役还没有可用角色，我们现在开始创建调查员。\n\n"
            "第 1 步：请先输入角色姓名。"
        )
    return (
        "当前战役还没有可用角色，我们现在开始创建角色。\n\n"
        "第 1 步：请先输入角色姓名。"
    )


def _start_existing_character_choice(state: SessionState) -> str:
    state.guide_state = "choose_existing"
    state.guide_context = {}
    return (
        "检测到这个战役已经有已创建角色。\n\n"
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
    if step == "player_name":
        return "第 2 步：请输入玩家名。"
    if step == "race":
        return "第 3 步：请输入种族，例如 Human、Elf、Dwarf。"
    if step == "class":
        return f"第 4 步：请输入职业。可选：{', '.join(DND_CLASS_NAMES)}。"
    if step == "background":
        return "第 5 步：请输入背景，例如 Soldier、Acolyte、Criminal。"
    if step == "alignment":
        return "第 6 步：请输入阵营；若不关心可输入“未指定”。"
    if step == "ability_method":
        return "第 7 步：请选择属性生成方式，输入 `roll`、`pointbuy` 或 `manual`。"
    if step == "scores":
        method = context["form"].get("ability_method", "manual")
        if method == "roll":
            arrays = context.get("roll_arrays") or generate_dnd_roll_arrays()
            context["roll_arrays"] = arrays
            lines = [f"数组 {index}: {array}" for index, array in enumerate(arrays, start=1)]
            return (
                "第 8 步：请选择一个数组并分配六维。请直接回复一行属性，例如：\n"
                "`STR=15 DEX=14 CON=13 INT=12 WIS=10 CHA=8`\n\n"
                + "\n".join(lines)
            )
        if method == "pointbuy":
            return (
                "第 8 步：请按 27 点购点输入六维，范围 8-15，例如：\n"
                "`STR=15 DEX=14 CON=13 INT=10 WIS=12 CHA=8`"
            )
        return (
            "第 8 步：请直接输入六维，格式例如：\n"
            "`STR=15 DEX=14 CON=13 INT=12 WIS=10 CHA=8`"
        )
    if step == "proficiencies":
        return (
            "第 9 步：请输入熟练技能，使用逗号分隔，可留空。\n"
            f"可选技能：{', '.join(DND_SKILL_NAMES)}"
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
    if step == "player_name":
        return "第 2 步：请输入玩家名。"
    if step == "era":
        return "第 3 步：请输入时代或背景，例如 1920s、现代、维多利亚时代。"
    if step == "occupation":
        return "第 4 步：请输入职业，例如 私家侦探、记者、医生。"
    if step == "age":
        return "第 5 步：请输入年龄。"
    if step == "scores":
        return (
            "第 6 步：请一次性输入八项属性，格式例如：\n"
            "`STR=60 CON=55 SIZ=65 DEX=70 APP=50 INT=75 POW=60 EDU=70`"
        )
    if step == "skills_summary":
        return "第 7 步：请输入关键技能或专长摘要，使用逗号分隔，例如“图书馆使用 70，侦查 60，聆听 55”。"
    if step == "backstory":
        return "第 8 步：请输入一段简短背景。"
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
        context["step"] = "player_name"
        return _prompt_for_dnd_step("player_name", context)
    if step == "player_name":
        form["player_name"] = value
        context["step"] = "race"
        return _prompt_for_dnd_step("race", context)
    if step == "race":
        form["race"] = value
        context["step"] = "class"
        return _prompt_for_dnd_step("class", context)
    if step == "class":
        if value.lower() not in DND_CLASS_NAMES:
            return _prompt_for_dnd_step("class", context)
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
        method = value.lower()
        if method not in {"roll", "pointbuy", "manual"}:
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
        context["step"] = "player_name"
        return _prompt_for_coc_step("player_name", context)
    if step == "player_name":
        form["player_name"] = value
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
    campaign_characters = list_campaign_characters(name)
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

    if not user_message.strip():
        raise ValueError("输入不能为空。")

    state.chat_history.append({"role": "user", "content": user_message.strip()})
    if state.guide_state:
        response = _handle_character_guide(state, user_message.strip())
    else:
        if not state.active_character_name:
            raise ValueError("请先完成角色选择或创建。")
        response = state.engine.chat(user_message.strip())
        state.status_message = f"正在进行：{state.campaign_name} / {state.active_character_name}"
    state.chat_history.append({"role": "assistant", "content": response})
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
    except Exception as exc:
        return _json_error(f"引擎通信错误: {exc}", 500)

    return jsonify({"ok": True, "message": response, "state": _serialize_state()})


if __name__ == "__main__":
    port = int(os.environ.get("OPEN_TABLETOP_GM_WEBUI_PORT", str(DEFAULT_PORT)))
    app.run(host="127.0.0.1", port=port, debug=False)
