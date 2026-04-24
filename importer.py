import os
from pathlib import Path
import fitz  # PyMuPDF
from openai import OpenAI
from config import get_config
from campaign import CAMPAIGNS_DIR

def chunk_text(text: str, max_chars: int = 8000) -> list:
    """Split text into chunks of maximum characters."""
    chunks = []
    current_chunk = ""
    
    # Split by paragraphs to avoid breaking sentences
    paragraphs = text.split('\n\n')
    
    for p in paragraphs:
        if len(current_chunk) + len(p) < max_chars:
            current_chunk += p + "\n\n"
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = p + "\n\n"
            
    if current_chunk:
        chunks.append(current_chunk.strip())
        
    return chunks

def extract_information(chunk: str, client: OpenAI, model: str) -> dict:
    """Use LLM to extract world, NPC, and state information from a text chunk."""
    system_prompt = """
    You are an AI assistant helping a Game Master prepare a tabletop RPG campaign.
    Please analyze the following text from a campaign module or rulebook.
    Extract the information into three categories:
    1. World/Lore: Setting details, locations, history, factions.
    2. NPCs: Characters, their motivations, stats, or descriptions.
    3. State/Plot: Current events, quests, plot hooks, or campaign state.
    
    Return the information clearly formatted in Markdown under these three exact headings:
    # World
    # NPCs
    # State
    
    If there is no relevant information for a category, leave it blank under the heading.
    """
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Text to analyze:\n\n{chunk}"}
            ]
        )
        content = response.choices[0].message.content or ""
        
        # Parse the response into the three categories
        result = {"world": "", "npcs": "", "state": ""}
        current_section = None
        
        for line in content.split('\n'):
            line_lower = line.lower()
            if "# world" in line_lower:
                current_section = "world"
            elif "# npcs" in line_lower or "# npc" in line_lower:
                current_section = "npcs"
            elif "# state" in line_lower or "# plot" in line_lower:
                current_section = "state"
            elif current_section:
                result[current_section] += line + "\n"
                
        return result
    except Exception as e:
        print(f"Error extracting information: {e}")
        return {"world": "", "npcs": "", "state": ""}

def import_pdf(campaign_name: str, pdf_path: str):
    campaign_dir = CAMPAIGNS_DIR / campaign_name
    
    if not os.path.exists(pdf_path):
        print(f"File not found: {pdf_path}")
        return

    # Check file extension
    file_ext = Path(pdf_path).suffix.lower()
    
    print(f"Reading file: {pdf_path}...")
    full_text = ""
    
    if file_ext == ".pdf":
        try:
            doc = fitz.open(pdf_path)
            for page in doc:
                full_text += page.get_text()
            doc.close()
        except Exception as e:
            print(f"Failed to read PDF: {e}")
            return
    elif file_ext == ".docx":
        try:
            from docx import Document
            doc = Document(pdf_path)
            for para in doc.paragraphs:
                full_text += para.text + "\n"
        except ImportError:
            print("Error: 'python-docx' library is required to read .docx files.")
            print("Please install it using: pip install python-docx")
            return
        except Exception as e:
            print(f"Failed to read DOCX: {e}")
            return
    elif file_ext in [".md", ".txt"]:
        try:
            with open(pdf_path, 'r', encoding='utf-8') as f:
                full_text = f.read()
        except Exception as e:
            print(f"Failed to read text file: {e}")
            return
    else:
        print(f"Unsupported file type: {file_ext}. Please use PDF, DOCX, MD, or TXT.")
        return

    if not full_text.strip():
        print("No text found in PDF.")
        return

    print(f"Extracted {len(full_text)} characters. Chunking text...")
    chunks = chunk_text(full_text)
    print(f"Created {len(chunks)} chunks. Processing with AI...")

    config = get_config()
    client_kwargs = {"api_key": config.api_key}
    
    # OpenRouter headers logic matching engine.py
    if config.base_url and "openrouter.ai" in config.base_url:
        client_kwargs["default_headers"] = {
            "HTTP-Referer": "https://github.com/open-tabletop-gm",
            "X-Title": "Open Tabletop GM"
        }
    if config.base_url:
        client_kwargs["base_url"] = config.base_url
        
    client = OpenAI(**client_kwargs)

    combined_world = ""
    combined_npcs = ""
    combined_state = ""

    for i, chunk in enumerate(chunks):
        print(f"Processing chunk {i+1}/{len(chunks)}...")
        extracted = extract_information(chunk, client, config.model)
        if extracted["world"].strip():
            combined_world += extracted["world"].strip() + "\n\n"
        if extracted["npcs"].strip():
            combined_npcs += extracted["npcs"].strip() + "\n\n"
        if extracted["state"].strip():
            combined_state += extracted["state"].strip() + "\n\n"

    print("Writing extracted information to campaign files...")
    
    # Ensure campaign directory exists before writing
    if not campaign_dir.exists():
        from campaign import create_campaign
        print(f"Creating new campaign '{campaign_name}'...")
        create_campaign(campaign_name)
    
    def append_to_file(filename: str, content: str):
        if not content.strip():
            return
        filepath = campaign_dir / filename
        existing = ""
        if filepath.exists():
            existing = filepath.read_text(encoding="utf-8")
        
        with open(filepath, "w", encoding="utf-8") as f:
            if existing:
                f.write(existing + "\n\n---\n\n" + content)
            else:
                f.write(content)

    append_to_file("world.md", combined_world)
    append_to_file("npcs.md", combined_npcs)
    append_to_file("state.md", combined_state)

    print(f"Successfully imported data into campaign '{campaign_name}'.")
