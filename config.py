import os
import json
import stat
from pathlib import Path

from llm import list_provider_options, normalize_provider, provider_base_url

CONFIG_DIR = Path.home() / ".config" / "open-tabletop-gm"
CONFIG_FILE = CONFIG_DIR / "config.json"

class Config:
    def __init__(self, prefer_env: bool = True):
        self.prefer_env = prefer_env
        self.api_key = os.environ.get("OPENAI_API_KEY", "")
        env_base_url = os.environ.get("OPENAI_BASE_URL", "")
        env_provider = os.environ.get("OPENAI_PROVIDER", "")
        self.provider = normalize_provider(env_provider, env_base_url)
        self.base_url = env_base_url or provider_base_url(self.provider)
        self.model = os.environ.get("OPENAI_MODEL", "gpt-4o")

    def normalize(self):
        self.provider = normalize_provider(self.provider, self.base_url)
        self.base_url = provider_base_url(self.provider, self.base_url)
        self.model = self.model.strip()
        self.api_key = self.api_key.strip()

    def load(self):
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if self.prefer_env:
                        # Environment variables take precedence if they are set.
                        if not os.environ.get("OPENAI_API_KEY"):
                            self.api_key = data.get("api_key", self.api_key)
                        if not os.environ.get("OPENAI_PROVIDER"):
                            self.provider = data.get("provider", self.provider)
                        if not os.environ.get("OPENAI_BASE_URL"):
                            self.base_url = data.get("base_url", self.base_url)
                        if not os.environ.get("OPENAI_MODEL"):
                            self.model = data.get("model", self.model)
                    else:
                        self.api_key = data.get("api_key", self.api_key)
                        self.provider = data.get("provider", self.provider)
                        self.base_url = data.get("base_url", self.base_url)
                        self.model = data.get("model", self.model)
            except Exception as e:
                print(f"Failed to load config: {e}")
        self.normalize()

    def save(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        self.normalize()
        data = {
            "api_key": self.api_key,
            "provider": self.provider,
            "base_url": self.base_url,
            "model": self.model
        }
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        
        # Set file permissions to 600 (read/write for owner only)
        # Note: chmod on Windows might not behave exactly like Unix, 
        # but stat.S_IRUSR | stat.S_IWUSR is the equivalent for 600
        try:
            CONFIG_FILE.chmod(stat.S_IRUSR | stat.S_IWUSR)
        except OSError:
            # Windows or sandboxed environments may reject chmod even though the file was saved.
            pass

def interactive_config():
    print("=== Open Tabletop GM Configuration ===")
    config = Config(prefer_env=False)
    config.load()

    provider_options = list_provider_options()
    print("Providers:")
    for index, option in enumerate(provider_options, start=1):
        current_marker = " (current)" if option["value"] == config.provider else ""
        print(f"  {index}. {option['label']} - {option['base_url']}{current_marker}")

    provider_input = input(f"Provider [{config.provider}]: ").strip()
    if provider_input:
        if provider_input.isdigit():
            selected_index = int(provider_input) - 1
            if 0 <= selected_index < len(provider_options):
                config.provider = provider_options[selected_index]["value"]
        else:
            config.provider = normalize_provider(provider_input)

    api_key = input(f"API Key [{config.api_key}]: ").strip()
    if api_key:
        config.api_key = api_key

    model = input(f"Model [{config.model}]: ").strip()
    if model:
        config.model = model

    config.save()
    print(f"\nConfiguration saved to {CONFIG_FILE} (permissions: 600).")

def get_config(prefer_env: bool = True):
    config = Config(prefer_env=prefer_env)
    config.load()
    return config
