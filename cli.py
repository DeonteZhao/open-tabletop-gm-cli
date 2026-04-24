import os
import subprocess
from engine import Engine
from commands import process_command
from campaign import CAMPAIGNS_DIR
from config import get_config

def push_to_display(text: str, is_player: bool = False, campaign_name: str = None):
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'display', 'send.py')
    if not os.path.exists(script_path):
        return
        
    cmd = ["python", script_path]
    if is_player:
        cmd.extend(["--player", "Party"])
    if campaign_name:
        cmd.extend(["--set-campaign", campaign_name])
        
    try:
        subprocess.run(cmd, input=text, text=True, capture_output=True, check=False)
    except Exception:
        pass

def load_campaign(campaign_name: str):
    config = get_config()
    if not config.api_key:
        print("Configuration not found or API key is empty. Please run 'python main.py config' first.")
        return

    campaign_path = CAMPAIGNS_DIR / campaign_name
    if not campaign_path.exists():
        print(f"Campaign '{campaign_name}' not found. Please create it first.")
        return
        
    # Register the campaign with the display server
    push_to_display("", campaign_name=campaign_name)
    
    print(f"Loading campaign: {campaign_name}...")
    engine = Engine(campaign_name)
    
    print("\nInitializing AI Game Master...")
    # Initialize system prompt and initial state
    engine.initialize_chat()
    
    print("Welcome to Open Tabletop GM!")
    print("Type your actions naturally, or use /help for commands.")
    print("-" * 50)
    
    print("GM is preparing the opening...")
    response = engine.chat("Please give a short introductory greeting and describe the current scene to start the session. You must reply in Chinese.")
    print(f"\nGM: {response}\n")
    
    # Push the opening narration to the display
    push_to_display(response)
    
    # Game Loop
    while True:
        try:
            user_input = input("\nYou: ").strip()
            if not user_input:
                continue
                
            # Check if it's a command
            if process_command(user_input, engine):
                continue
                
            # Push the player's action to the display
            push_to_display(user_input, is_player=True)
                
            # Otherwise, send to Engine
            print("GM is thinking...")
            response = engine.chat(user_input)
            print(f"\nGM: {response}")
            
            # Push the GM's response to the display
            push_to_display(response)
            
        except KeyboardInterrupt:
            print("\nType /quit to exit without saving, or /end to save and exit.")
        except EOFError:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"\nAn error occurred: {e}")
