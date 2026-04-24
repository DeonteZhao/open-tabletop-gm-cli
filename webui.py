from __future__ import annotations

import json
import os
import secrets
import threading
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from flask import Flask, jsonify, render_template, request, session
from werkzeug.utils import secure_filename

from campaign import CAMPAIGNS_DIR, create_campaign, list_campaigns
from config import CONFIG_FILE, Config, get_config
from engine import Engine
from importer import import_pdf


BASE_DIR = Path(__file__).resolve().parent
WEBUI_TEMPLATES_DIR = BASE_DIR / "webui_templates"
WEBUI_STATIC_DIR = BASE_DIR / "webui_static"
DEFAULT_PORT = 7860
UPLOADS_DIR = Path(tempfile.gettempdir()) / "open-tabletop-gm" / "imports"
ALLOWED_IMPORT_EXTENSIONS = {".pdf", ".docx", ".md", ".txt"}

SYSTEM_META = {
    "dnd5e": {
        "label": "D&D 5E",
        "tagline": "英雄史诗",
        "theme": "dnd5e",
        "module_icon": "shield",
        "resource_label": "HP / AC / 先攻",
        "resource_value": "32 / 16 / +3",
        "resource_ratio": 0.72,
        "resource_meter": "heroic",
        "insight_label": "战斗面板",
        "insight_value": "资源、条件、行动入口",
        "status_tags": [
            {"label": "CONCENTRATION", "icon": "focus", "tone": "warning"},
            {"label": "BLESSED", "icon": "spark", "tone": "success"},
            {"label": "SPELL SLOTS", "icon": "flame", "tone": "neutral"},
        ],
        "quick_actions": [
            {"label": "攻击", "icon": "crosshair", "variant": "primary"},
            {"label": "法术", "icon": "flame", "variant": "secondary"},
            {"label": "治疗", "icon": "heart", "variant": "ghost"},
        ],
        "rule_entries": [
            {"title": "SRD 法术", "detail": "施法时间 / 距离 / 专注", "icon": "book-open"},
            {"title": "战斗流程", "detail": "攻击、豁免、条件", "icon": "swords"},
            {"title": "怪物速览", "detail": "AC / HP / CR", "icon": "dragon"},
        ],
        "feature_modules": [
            {
                "eyebrow": "专属模块",
                "title": "战斗仪表",
                "icon": "swords",
                "description": "聚焦行动经济、护甲等级与行动顺序，维持 D&D 战斗驾驶舱的读数感。",
                "stats": [
                    {"label": "ARMOR CLASS", "value": "16", "icon": "shield", "tone": "neutral"},
                    {"label": "INITIATIVE", "value": "+3", "icon": "zap", "tone": "success"},
                    {"label": "SPEED", "value": "30 FT", "icon": "footprints", "tone": "neutral"},
                ],
            },
            {
                "eyebrow": "专属模块",
                "title": "英雄资源",
                "icon": "spark",
                "description": "以段式资源条和条件芯片呈现法术位、集中与增益，强化高频动作入口。",
                "stats": [
                    {"label": "HIT POINTS", "value": "32 / 38", "icon": "heart", "tone": "neutral"},
                    {"label": "SPELL SLOTS", "value": "3 / 4", "icon": "flame", "tone": "warning"},
                    {"label": "DEATH SAVE", "value": "0 / 3", "icon": "skull", "tone": "danger"},
                ],
            },
        ],
        "specialized_panel": {
            "kind": "dnd5e",
            "title": "战斗驾驶舱",
            "eyebrow": "专属组件",
            "summary": "把护甲、先攻、生命和法术位放进同一块战斗仪表，保留 D&D 资源管理的驾驶舱感。",
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
            "action_steps": [
                {"label": "攻击动作", "detail": "Attack / Damage", "icon": "crosshair"},
                {"label": "奖励动作", "detail": "Class Feature / Off-hand", "icon": "spark"},
                {"label": "反应", "detail": "Opportunity / Shield", "icon": "zap"},
            ],
        },
    },
    "coc7e": {
        "label": "CoC 7E",
        "tagline": "克苏鲁调查",
        "theme": "coc7e",
        "module_icon": "brain",
        "resource_label": "SAN / HP / MP",
        "resource_value": "54 / 11 / 12",
        "resource_ratio": 0.54,
        "resource_meter": "sanity",
        "insight_label": "调查面板",
        "insight_value": "理智保险丝、d100、线索板",
        "status_tags": [
            {"label": "TEMP INSANITY", "icon": "alert-triangle", "tone": "insanity"},
            {"label": "MYTHOS 14%", "icon": "hex", "tone": "eldritch"},
            {"label": "CLUE LINKED", "icon": "fingerprint", "tone": "neutral"},
        ],
        "quick_actions": [
            {"label": "技能检定", "icon": "target", "variant": "primary"},
            {"label": "理智检定", "icon": "brain", "variant": "secondary"},
            {"label": "推动检定", "icon": "arrow-right-circle", "variant": "ghost"},
        ],
        "rule_entries": [
            {"title": "技能阈值", "detail": "常规 / 困难 / 极难", "icon": "percent"},
            {"title": "疯狂规则", "detail": "临时 / 不定性 / 永久", "icon": "alert-triangle"},
            {"title": "线索板", "detail": "线索、证物、关联", "icon": "fingerprint"},
        ],
        "feature_modules": [
            {
                "eyebrow": "专属模块",
                "title": "理智保险丝",
                "icon": "brain",
                "description": "突出当前 SAN、神话侵蚀与疯狂阈值，让 CoC 的精神风险在侧栏持续可见。",
                "stats": [
                    {"label": "CURRENT SAN", "value": "54 / 70", "icon": "brain", "tone": "warning"},
                    {"label": "MYTHOS", "value": "14%", "icon": "hex", "tone": "eldritch"},
                    {"label": "BREAKPOINT", "value": "单次失去 5+", "icon": "alert-triangle", "tone": "insanity"},
                ],
            },
            {
                "eyebrow": "专属模块",
                "title": "调查链路",
                "icon": "fingerprint",
                "description": "将 d100 检定、线索流转和职业调查节奏集中到统一面板，避免被通用聊天区吞没。",
                "stats": [
                    {"label": "SPOT HIDDEN", "value": "55%", "icon": "target", "tone": "neutral"},
                    {"label": "BONUS / PENALTY", "value": "0 / 1", "icon": "percent", "tone": "neutral"},
                    {"label": "OCCUPATION", "value": "INVESTIGATOR", "icon": "briefcase", "tone": "neutral"},
                ],
            },
        ],
        "specialized_panel": {
            "kind": "coc7e",
            "title": "理智与调查仪表",
            "eyebrow": "专属组件",
            "summary": "把 SAN、神话侵蚀、d100 检定和线索状态钉在同一个调查仪表上，突出 CoC 的精神压力。",
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
            "clue_chain": [
                {"label": "地窖泥点", "tone": "neutral", "icon": "fingerprint"},
                {"label": "神话痕迹", "tone": "eldritch", "icon": "hex"},
                {"label": "临时疯狂风险", "tone": "insanity", "icon": "alert-triangle"},
            ],
        },
    },
}


def _get_system_meta(system: str) -> dict[str, object]:
    return SYSTEM_META.get(system, SYSTEM_META["dnd5e"])


@dataclass
class SessionState:
    engine: Engine | None = None
    campaign_name: str = ""
    campaign_system: str = ""
    chat_history: list[dict[str, str]] = field(default_factory=list)
    status_message: str = "等待载入战役。"


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


def _serialize_campaign(name: str) -> dict[str, str]:
    system = _read_campaign_system(name)
    system_meta = _get_system_meta(system)
    return {
        "name": name,
        "system": system,
        "system_label": system_meta["label"],
        "tagline": system_meta["tagline"],
    }


def _list_campaign_payload() -> list[dict[str, str]]:
    campaigns = sorted(list_campaigns(print_out=False))
    return [_serialize_campaign(name) for name in campaigns]


def _serialize_state() -> dict[str, object]:
    state = _get_session_state()
    config = get_config()
    current_campaign = None
    system_meta = _get_system_meta("dnd5e")

    if state.campaign_name:
        current_campaign = {
            "name": state.campaign_name,
            "system": state.campaign_system,
            "system_label": _get_system_meta(state.campaign_system)["label"],
        }
        system_meta = _get_system_meta(state.campaign_system)

    return {
        "config": {
            "api_key": config.api_key,
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


def save_config(api_key: str, base_url: str, model: str) -> str:
    config = Config()
    config.api_key = api_key.strip()
    config.base_url = base_url.strip()
    config.model = model.strip()
    config.save()
    return f"配置已保存到 {CONFIG_FILE}"


def create_new_campaign(name: str, system: str) -> tuple[bool, str]:
    if not name.strip():
        return False, "战役名称不能为空。"

    if create_campaign(name.strip(), system):
        return True, f"战役 '{name.strip()}' 已创建，规则系统为 {_get_system_meta(system)['label']}。"
    return False, f"创建战役 '{name.strip()}' 失败，可能已存在或模板缺失。"


def load_selected_campaign(name: str) -> str:
    if not name:
        raise ValueError("请先选择一个战役。")

    config = get_config()
    if not config.api_key:
        raise ValueError("尚未配置 API Key，请先在配置区保存。")

    state = _get_session_state()
    engine = Engine(name)
    engine.initialize_chat()

    intro_prompt = (
        "Please give a short introductory greeting and describe the current scene "
        "to start the session. You must reply in Chinese."
    )
    response = engine.chat(intro_prompt)

    state.engine = engine
    state.campaign_name = name
    state.campaign_system = _read_campaign_system(name)
    state.chat_history = [{"role": "assistant", "content": response}]
    state.status_message = f"已加载战役：{name}"
    return state.status_message


def chat_with_gm(user_message: str) -> str:
    state = _get_session_state()
    if not state.engine:
        raise ValueError("请先在战役大厅加载一个战役。")

    if not user_message.strip():
        raise ValueError("输入不能为空。")

    response = state.engine.chat(user_message.strip())
    state.chat_history.append({"role": "user", "content": user_message.strip()})
    state.chat_history.append({"role": "assistant", "content": response})
    state.status_message = f"正在进行：{state.campaign_name}"
    return response


@app.get("/")
def index():
    snapshot = _serialize_state()
    return render_template(
        "index.html",
        snapshot=snapshot,
        systems=SYSTEM_META,
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
            payload.get("api_key", ""),
            payload.get("base_url", ""),
            payload.get("model", ""),
        )
    except Exception as exc:
        return _json_error(f"保存配置失败: {exc}", 500)

    state = _get_session_state()
    state.status_message = "配置已更新。"
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

    config = get_config()
    if not config.api_key:
        return _json_error("导入模组前请先在配置区保存 API Key。", 400)

    if not _campaign_exists(campaign_name):
        created = create_campaign(campaign_name, system)
        if not created:
            return _json_error("创建导入目标战役失败，请检查名称是否重复。", 400)

    safe_name = secure_filename(Path(source.filename).name) or f"module{suffix}"
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    upload_path = UPLOADS_DIR / f"{secrets.token_hex(8)}-{safe_name}"
    source.save(upload_path)

    try:
        ok, message = import_pdf(campaign_name, str(upload_path))
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
