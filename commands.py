import sys
from campaign import CAMPAIGNS_DIR

def handle_help():
    print("\n=== Available Commands ===")
    print("/help   - Show this help message")
    print("/save   - Save the current game state")
    print("/world  - Show the world information")
    print("/npcs   - Show the NPCs information")
    print("/recap  - Generate a recap of the session")
    print("/import - Import a PDF file (/import <pdf_path>)")
    print("/end    - End the session and save")
    print("/quit   - Quit without saving")
    print("==========================\n")

def handle_save(engine):
    print("Saving game state...")
    # In a real implementation, we would summarize the chat history
    # and update the state.md file. For now, we'll just write a basic message.
    state_file = engine.campaign_path / "state.md"
    if state_file.exists():
        content = state_file.read_text(encoding="utf-8")
        # Append a simple save note
        state_file.write_text(content + "\n- State saved by user command.\n", encoding="utf-8")
    print("Game state saved.")

def handle_world(engine):
    world_file = engine.campaign_path / "world.md"
    if world_file.exists():
        print("\n=== World Information ===")
        print(world_file.read_text(encoding="utf-8"))
        print("=========================\n")
    else:
        print("No world information found.")

def handle_npcs(engine):
    npcs_file = engine.campaign_path / "npcs.md"
    if npcs_file.exists():
        print("\n=== NPCs Information ===")
        print(npcs_file.read_text(encoding="utf-8"))
        print("========================\n")
    else:
        print("No NPCs information found.")

def handle_recap(engine):
    print("Generating recap...")
    # Request a recap from the engine
    recap_prompt = "System Command: Please provide a brief recap of our session so far based on our chat history."
    response = engine.chat(recap_prompt)
    print("\n=== Session Recap ===")
    print(response)
    print("=====================\n")

def handle_end(engine):
    handle_save(engine)
    print("Ending session. Goodbye!")
    sys.exit(0)

def handle_quit():
    print("Quitting without saving. Goodbye!")
    sys.exit(0)

def handle_import(engine, args_str: str):
    if not args_str:
        print("Usage: /import <pdf_path>")
        return
    pdf_path = args_str.strip()
    from importer import import_pdf
    print(f"Importing {pdf_path} into campaign '{engine.campaign_name}'...")
    import_pdf(engine.campaign_name, pdf_path)

def process_command(cmd: str, engine) -> bool:
    """
    Process a slash command. 
    Returns True if it was a command, False if it was regular chat.
    """
    if not cmd.startswith("/"):
        return False
        
    cmd_lower = cmd.strip().lower()
    
    if cmd_lower.startswith("/help"):
        handle_help()
    elif cmd_lower.startswith("/save"):
        handle_save(engine)
    elif cmd_lower.startswith("/world"):
        handle_world(engine)
    elif cmd_lower.startswith("/npcs"):
        handle_npcs(engine)
    elif cmd_lower.startswith("/recap"):
        handle_recap(engine)
    elif cmd_lower.startswith("/import"):
        args = cmd.strip()[len("/import"):].strip()
        handle_import(engine, args)
    elif cmd_lower.startswith("/end"):
        handle_end(engine)
    elif cmd_lower.startswith("/quit"):
        handle_quit()
    else:
        print(f"Unknown command: {cmd.strip()}. Type /help for available commands.")
        
    return True
