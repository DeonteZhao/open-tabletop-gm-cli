from __future__ import annotations

from copy import deepcopy

from openai import OpenAI


DEFAULT_PROVIDER = "openai"

PROVIDER_SPECS = {
    "openai": {
        "label": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "model_placeholder": "gpt-4o",
    },
    "deepseek": {
        "label": "DeepSeek",
        "base_url": "https://api.deepseek.com/v1",
        "model_placeholder": "deepseek-chat",
    },
    "openrouter": {
        "label": "OpenRouter",
        "base_url": "https://openrouter.ai/api/v1",
        "model_placeholder": "openai/gpt-4o-mini",
    },
}

OPENROUTER_HEADERS = {
    "HTTP-Referer": "https://github.com/open-tabletop-gm",
    "X-Title": "Open Tabletop GM",
}


def normalize_provider(provider: str | None = "", base_url: str | None = "") -> str:
    provider_value = (provider or "").strip().lower()
    if provider_value in PROVIDER_SPECS:
        return provider_value

    base_url_value = (base_url or "").strip().lower()
    if "openrouter.ai" in base_url_value:
        return "openrouter"
    if "deepseek.com" in base_url_value:
        return "deepseek"
    return DEFAULT_PROVIDER


def get_provider_spec(provider: str | None = "", base_url: str | None = "") -> dict[str, str]:
    provider_key = normalize_provider(provider, base_url)
    return deepcopy(PROVIDER_SPECS[provider_key])


def provider_base_url(provider: str | None = "", base_url: str | None = "") -> str:
    return get_provider_spec(provider, base_url)["base_url"]


def list_provider_options() -> list[dict[str, str]]:
    options = []
    for provider_id, spec in PROVIDER_SPECS.items():
        options.append(
            {
                "value": provider_id,
                "label": spec["label"],
                "base_url": spec["base_url"],
                "model_placeholder": spec["model_placeholder"],
            }
        )
    return options


def validate_llm_config(config) -> str | None:
    provider = normalize_provider(getattr(config, "provider", ""), getattr(config, "base_url", ""))
    if provider not in PROVIDER_SPECS:
        return "当前配置的 LLM 提供商不受支持。"
    if not getattr(config, "api_key", "").strip():
        return "尚未配置 API Key，请先在配置区保存。"
    if not getattr(config, "model", "").strip():
        return "尚未配置模型名，请先在配置区填写模型。"
    return None


def build_client_kwargs(config) -> dict[str, object]:
    provider = normalize_provider(getattr(config, "provider", ""), getattr(config, "base_url", ""))
    client_kwargs: dict[str, object] = {
        "api_key": getattr(config, "api_key", "").strip(),
        "base_url": provider_base_url(provider),
    }
    if provider == "openrouter":
        client_kwargs["default_headers"] = dict(OPENROUTER_HEADERS)
    return client_kwargs


def create_llm_client(config) -> OpenAI:
    return OpenAI(**build_client_kwargs(config))
