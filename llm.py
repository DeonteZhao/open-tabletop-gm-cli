from __future__ import annotations

from copy import deepcopy

from openai import OpenAI


DEFAULT_PROVIDER = "openai"
CUSTOM_PROVIDER = "custom"

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
    "siliconflow": {
        "label": "硅基流动 SiliconFlow",
        "base_url": "https://api.siliconflow.cn/v1",
        "model_placeholder": "Qwen/Qwen2.5-72B-Instruct",
    },
    "kimi": {
        "label": "月之暗面 Kimi",
        "base_url": "https://api.moonshot.cn/v1",
        "model_placeholder": "moonshot-v1-8k",
    },
    "qwen": {
        "label": "阿里云通义千问",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model_placeholder": "qwen-plus",
    },
    "glm": {
        "label": "智谱 GLM",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "model_placeholder": "glm-4-flash",
    },
    "doubao": {
        "label": "字节豆包",
        "base_url": "https://ark.cn-beijing.volces.com/api/v3",
        "model_placeholder": "doubao-pro-32k",
    },
    "baichuan": {
        "label": "百川智能",
        "base_url": "https://api.baichuan-ai.com/v1",
        "model_placeholder": "Baichuan4",
    },
    "minimax": {
        "label": "MiniMax",
        "base_url": "https://api.minimax.chat/v1",
        "model_placeholder": "abab6.5s-chat",
    },
    "custom": {
        "label": "自定义 OpenAI 兼容接口",
        "base_url": "",
        "model_placeholder": "model-name",
    },
}

BASE_URL_PROVIDER_HINTS = {
    "openrouter.ai": "openrouter",
    "deepseek.com": "deepseek",
    "siliconflow.cn": "siliconflow",
    "moonshot.cn": "kimi",
    "dashscope.aliyuncs.com": "qwen",
    "bigmodel.cn": "glm",
    "volces.com": "doubao",
    "baichuan-ai.com": "baichuan",
    "minimax.chat": "minimax",
    "api.openai.com": "openai",
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
    for hint, provider_id in BASE_URL_PROVIDER_HINTS.items():
        if hint in base_url_value:
            return provider_id
    if base_url_value:
        return CUSTOM_PROVIDER
    return DEFAULT_PROVIDER


def get_provider_spec(provider: str | None = "", base_url: str | None = "") -> dict[str, str]:
    provider_key = normalize_provider(provider, base_url)
    return deepcopy(PROVIDER_SPECS[provider_key])


def provider_base_url(provider: str | None = "", base_url: str | None = "") -> str:
    provider_key = normalize_provider(provider, base_url)
    if provider_key == CUSTOM_PROVIDER:
        return (base_url or "").strip()
    return PROVIDER_SPECS[provider_key]["base_url"]


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
    if provider == CUSTOM_PROVIDER and not getattr(config, "base_url", "").strip():
        return "自定义 LLM 提供商需要填写 Base URL。"
    if not getattr(config, "api_key", "").strip():
        return "尚未配置 API Key，请先在配置区保存。"
    if not getattr(config, "model", "").strip():
        return "尚未配置模型名，请先在配置区填写模型。"
    return None


def build_client_kwargs(config) -> dict[str, object]:
    provider = normalize_provider(getattr(config, "provider", ""), getattr(config, "base_url", ""))
    client_kwargs: dict[str, object] = {
        "api_key": getattr(config, "api_key", "").strip(),
        "base_url": provider_base_url(provider, getattr(config, "base_url", "")),
    }
    if provider == "openrouter":
        client_kwargs["default_headers"] = dict(OPENROUTER_HEADERS)
    return client_kwargs


def create_llm_client(config) -> OpenAI:
    return OpenAI(**build_client_kwargs(config))
