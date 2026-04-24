import os
import json
import stat
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "open-tabletop-gm"
CONFIG_FILE = CONFIG_DIR / "config.json"

class Config:
    def __init__(self):
        self.api_key = os.environ.get("OPENAI_API_KEY", "")
        self.base_url = os.environ.get("OPENAI_BASE_URL", "")
        self.model = os.environ.get("OPENAI_MODEL", "gpt-4o")

    def load(self):
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Environment variables take precedence if they are set
                    if not os.environ.get("OPENAI_API_KEY"):
                        self.api_key = data.get("api_key", self.api_key)
                    if not os.environ.get("OPENAI_BASE_URL"):
                        self.base_url = data.get("base_url", self.base_url)
                    if not os.environ.get("OPENAI_MODEL"):
                        self.model = data.get("model", self.model)
            except Exception as e:
                print(f"Failed to load config: {e}")

    def save(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        data = {
            "api_key": self.api_key,
            "base_url": self.base_url,
            "model": self.model
        }
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        
        # Set file permissions to 600 (read/write for owner only)
        # Note: chmod on Windows might not behave exactly like Unix, 
        # but stat.S_IRUSR | stat.S_IWUSR is the equivalent for 600
        CONFIG_FILE.chmod(stat.S_IRUSR | stat.S_IWUSR)

def interactive_config():
    print("=== Open Tabletop GM Configuration ===")
    config = Config()
    config.load()
    
    api_key = input(f"API Key [{config.api_key}]: ").strip()
    if api_key:
        config.api_key = api_key
        
    base_url = input(f"Base URL [{config.base_url}]: ").strip()
    if base_url:
        config.base_url = base_url
        
    model = input(f"Model [{config.model}]: ").strip()
    if model:
        config.model = model
        
    config.save()
    print(f"\nConfiguration saved to {CONFIG_FILE} (permissions: 600).")

def get_config():
    config = Config()
    config.load()
    return config
