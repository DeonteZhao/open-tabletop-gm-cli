import shutil
from pathlib import Path

CAMPAIGNS_DIR = Path.home() / ".local" / "share" / "open-tabletop-gm" / "campaigns"
TEMPLATES_DIR = Path(__file__).parent / "templates"

def create_campaign(name: str):
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
                
        print(f"Campaign '{name}' created successfully at {campaign_path}.")
        return True
    except Exception as e:
        print(f"Failed to create campaign '{name}': {e}")
        return False

def list_campaigns():
    if not CAMPAIGNS_DIR.exists():
        print("No campaigns found.")
        return
        
    campaigns = [d for d in CAMPAIGNS_DIR.iterdir() if d.is_dir()]
    if not campaigns:
        print("No campaigns found.")
        return
        
    print("=== Campaigns ===")
    for campaign in campaigns:
        print(f"- {campaign.name}")
