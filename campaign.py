import shutil
from pathlib import Path

CAMPAIGNS_DIR = Path.home() / ".local" / "share" / "open-tabletop-gm" / "campaigns"
TEMPLATES_DIR = Path(__file__).parent / "templates"

import json

def create_campaign(name: str, system: str = "dnd5e"):
    campaign_path = CAMPAIGNS_DIR / name
    if campaign_path.exists():
        print(f"Campaign '{name}' already exists at {campaign_path}.")
        return False
        
    if not TEMPLATES_DIR.exists():
        print(f"Templates directory not found at {TEMPLATES_DIR}.")
        return False

    try:
        # Create campaign directory
        campaign_path.mkdir(parents=True, exist_ok=True)
        
        # Copy template files
        for item in TEMPLATES_DIR.iterdir():
            if item.is_file():
                shutil.copy2(item, campaign_path / item.name)
                
        # Save campaign config
        config_path = campaign_path / "campaign.json"
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump({"system": system}, f, indent=4)
                
        print(f"Campaign '{name}' created successfully at {campaign_path} using {system} system.")
        return True
    except Exception as e:
        print(f"Failed to create campaign '{name}': {e}")
        return False

def list_campaigns(print_out: bool = True):
    if not CAMPAIGNS_DIR.exists():
        if print_out:
            print("No campaigns found.")
        return []
        
    campaigns = [d for d in CAMPAIGNS_DIR.iterdir() if d.is_dir()]
    if not campaigns:
        if print_out:
            print("No campaigns found.")
        return []
        
    if print_out:
        print("=== Campaigns ===")
        for campaign in campaigns:
            print(f"- {campaign.name}")
    return [c.name for c in campaigns]
