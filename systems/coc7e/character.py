from __future__ import annotations

import uuid
from datetime import datetime, timezone


COC_STATS = ["STR", "CON", "SIZ", "DEX", "APP", "INT", "POW", "EDU"]


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def half(value: int) -> int:
    return value // 2


def fifth(value: int) -> int:
    return value // 5


def validate_scores(scores: dict[str, int]) -> dict[str, int]:
    normalized = {stat: int(scores[stat]) for stat in COC_STATS}
    for stat, value in normalized.items():
        if value < 15 or value > 99:
            raise ValueError(f"{stat}={value} 超出 CoC 首版建角允许范围 15-99。")
    return normalized


def compute_hit_points(scores: dict[str, int]) -> int:
    return (scores["CON"] + scores["SIZ"]) // 10


def compute_magic_points(scores: dict[str, int]) -> int:
    return scores["POW"] // 5


def compute_sanity(scores: dict[str, int]) -> int:
    return scores["POW"]


def compute_move_rate(scores: dict[str, int], age: int) -> int:
    if scores["STR"] < scores["SIZ"] and scores["DEX"] < scores["SIZ"]:
        base = 7
    elif scores["STR"] > scores["SIZ"] and scores["DEX"] > scores["SIZ"]:
        base = 9
    else:
        base = 8

    if age >= 80:
        return max(1, base - 5)
    if age >= 70:
        return max(1, base - 4)
    if age >= 60:
        return max(1, base - 3)
    if age >= 50:
        return max(1, base - 2)
    if age >= 40:
        return max(1, base - 1)
    return base


def compute_build_and_db(scores: dict[str, int]) -> tuple[int, str]:
    total = scores["STR"] + scores["SIZ"]
    if total <= 64:
        return -2, "-2"
    if total <= 84:
        return -1, "-1"
    if total <= 124:
        return 0, "0"
    if total <= 164:
        return 1, "+1D4"
    if total <= 204:
        return 2, "+1D6"
    if total <= 284:
        return 3, "+2D6"

    extra_steps = 3 + ((total - 205) // 80)
    extra_dice = 2 + ((total - 205) // 80)
    return extra_steps, f"+{extra_dice}D6"


def render_markdown(record: dict, details: dict) -> str:
    scores = details["scores"]
    derived = details["derived"]
    lines = [
        f"# {record['name']}",
        f"**Player:** {record['player_name']}  **Campaign:** {record['campaign']}  **System:** CoC 7e",
        "",
        "## Identity",
        f"- **Era:** {details['era']} | **Occupation:** {details['occupation']} | **Age:** {details['age']}",
        f"- **Summary:** {record['summary']}",
        "",
        "## Core Attributes",
        "| Stat | Score | Half | Fifth |",
        "|------|-------|------|-------|",
    ]
    for stat in COC_STATS:
        lines.append(f"| {stat} | {scores[stat]} | {half(scores[stat])} | {fifth(scores[stat])} |")

    lines.extend(
        [
            "",
            "## Derived Stats",
            f"- **HP:** {derived['hp']} / {derived['hp']}",
            f"- **MP:** {derived['mp']}",
            f"- **SAN:** {derived['san']} / {derived['san']}",
            f"- **Luck:** {derived['luck']}",
            f"- **MOV:** {derived['mov']}",
            f"- **Build:** {derived['build']}",
            f"- **DB:** {derived['damage_bonus']}",
            "",
            "## Skills Summary",
            details["skills_summary"] or "- 待补充",
            "",
            "## Backstory",
            details["backstory"] or "- 待补充",
            "",
        ]
    )
    return "\n".join(lines)


def build_coc_character(
    *,
    campaign_name: str,
    name: str,
    player_name: str,
    era: str,
    occupation: str,
    age: int,
    scores: dict[str, int],
    skills_summary: str,
    backstory: str,
) -> dict:
    normalized_scores = validate_scores(scores)
    build, damage_bonus = compute_build_and_db(normalized_scores)
    derived = {
        "hp": compute_hit_points(normalized_scores),
        "mp": compute_magic_points(normalized_scores),
        "san": compute_sanity(normalized_scores),
        "luck": normalized_scores["POW"],
        "mov": compute_move_rate(normalized_scores, age),
        "build": build,
        "damage_bonus": damage_bonus,
    }
    summary = f"{era} {occupation} | {age}岁"
    details = {
        "era": era,
        "occupation": occupation,
        "age": age,
        "scores": normalized_scores,
        "skills_summary": skills_summary,
        "backstory": backstory,
        "derived": derived,
    }
    record = {
        "id": str(uuid.uuid4()),
        "name": name,
        "system": "coc7e",
        "system_label": "COC",
        "campaign": campaign_name,
        "player_name": player_name,
        "status": "ready",
        "summary": summary,
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
        "details": details,
    }
    record["markdown"] = render_markdown(record, details)
    return record
