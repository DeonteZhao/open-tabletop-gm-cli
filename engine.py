import os
import json
from pathlib import Path
from config import get_config
from llm import create_llm_client
from tools import execute_tool, get_project_root
from campaign import CAMPAIGNS_DIR

class Engine:
    def __init__(self, campaign_name: str, prefer_env_config: bool = True):
        self.campaign_name = campaign_name
        self.campaign_path = CAMPAIGNS_DIR / campaign_name
        self.prefer_env_config = prefer_env_config
        self.refresh_config()
        
        self.messages = []
        self.system_prompt_initialized = False

    def refresh_config(self):
        self.config = get_config(prefer_env=self.prefer_env_config)
        self.client = create_llm_client(self.config)
        self.model = self.config.model

    def build_system_prompt(self) -> str:
        prompt_parts = []
        
        # 1. SKILL.md
        skill_path = Path(get_project_root()) / "SKILL.md"
        if skill_path.exists():
            prompt_parts.append(skill_path.read_text(encoding="utf-8"))
            
        # 2. System rules (e.g. dnd5e or coc7e)
        system_name = "dnd5e"
        campaign_config_path = self.campaign_path / "campaign.json"
        if campaign_config_path.exists():
            try:
                with open(campaign_config_path, "r", encoding="utf-8") as f:
                    camp_config = json.load(f)
                    system_name = camp_config.get("system", "dnd5e")
            except Exception:
                pass
                
        system_path = Path(get_project_root()) / "systems" / system_name / "system.md"
        if system_path.exists():
            prompt_parts.append(system_path.read_text(encoding="utf-8"))
            
        # 3. Campaign specific files
        campaign_files = ["world.md", "npcs.md", "state.md", "character-sheet.md"]
        for filename in campaign_files:
            filepath = self.campaign_path / filename
            if filepath.exists():
                content = filepath.read_text(encoding="utf-8")
                prompt_parts.append(f"--- {filename} ---\n{content}\n")
                
        # 4. Global instructions
        prompt_parts.append(
            "You must always communicate with the user in Chinese. "
            "When you use tools (like dice), explain the result in Chinese.\n\n"
            "IMPORTANT ARCHITECTURE CHANGE:\n"
            "Even though SKILL.md mentions using `bash` blocks to run scripts (like dice.py, combat.py, or send.py), "
            "this environment uses OpenAI Function Calling (tools) instead. "
            "You MUST use the provided tools (e.g., `dice`, `combat`, `tracker`, `calendar`, `display_send`) "
            "to execute scripts and update the display. Do NOT write ```bash code blocks. "
            "Use `display_send` to push your narration and stat updates to the screen companion."
        )
                
        return "\n\n".join(prompt_parts)

    def initialize_chat(self):
        system_prompt = self.build_system_prompt()
        self.messages = [{"role": "system", "content": system_prompt}]
        self.system_prompt_initialized = True

    def get_tools_definition(self):
        return [
            {
                "type": "function",
                "function": {
                    "name": "dice",
                    "description": "Roll dice for checks, attacks, or damage (e.g., 1d20+5, 2d6). Supports CoC 7E bonus/penalty dice (e.g., d100 b1, d100 p2). Set silent=True for secret rolls.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "notation": { "type": "string", "description": "Dice expression (e.g., '1d20+3', '4d6kh3', 'd100 b1', 'd100 p2')" },
                            "silent": { "type": "boolean", "description": "If true, roll secretly" }
                        },
                        "required": ["notation"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "combat",
                    "description": "Handle combat mechanics (init, tracker, attack).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "action": { "type": "string", "enum": ["init", "tracker", "attack"] },
                            "json_data": { "type": "string", "description": "JSON payload for init or tracker" },
                            "atk": { "type": "integer", "description": "Attack bonus (for attack action)" },
                            "ac": { "type": "integer", "description": "Target AC (for attack action)" },
                            "dmg": { "type": "string", "description": "Damage dice (for attack action)" }
                        },
                        "required": ["action"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "tracker",
                    "description": "Track conditions, effects, concentration, death saves.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "campaign": { "type": "string", "description": "Campaign name" },
                            "action": { "type": "string", "enum": ["effect", "condition", "concentrate", "saves", "status", "clear"] },
                            "sub_action": { "type": "string", "description": "e.g., 'start', 'end', 'tick', 'add', 'remove'" },
                            "actor": { "type": "string", "description": "Character name" },
                            "effect_name": { "type": "string", "description": "Name of the effect/condition" },
                            "duration": { "type": "string", "description": "e.g., '10r', '60m', 'indef'" },
                            "is_conc": { "type": "string", "description": "Pass 'conc' if it's concentration" }
                        },
                        "required": ["campaign", "action"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "calendar",
                    "description": "Manage game time and rests.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "campaign": { "type": "string", "description": "Campaign name" },
                            "action": { "type": "string", "enum": ["init", "advance", "rest", "now", "set", "time", "events"] },
                            "amount": { "type": "integer", "description": "Amount to advance (e.g. 8)" },
                            "unit": { "type": "string", "description": "Unit (e.g. 'hours', 'days', 'short', 'long')" }
                        },
                        "required": ["campaign", "action"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "display_send",
                    "description": "Push narration, dice context, NPC dialogue, or stats to the display companion.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "text": { "type": "string", "description": "The narration or dialogue text" },
                            "player": { "type": "string", "description": "Player name if this is a player action" },
                            "npc": { "type": "string", "description": "NPC name if this is dialogue" },
                            "dice": { "type": "boolean", "description": "True if this is a dice result" },
                            "tutor": { "type": "boolean", "description": "True if this is a tutor hint" },
                            "stat_hp": { "type": "string", "description": "Format: NAME:CURRENT:MAX" },
                            "stat_condition_add": { "type": "string", "description": "Format: NAME:CONDITION" }
                        },
                        "required": ["text"]
                    }
                }
            }
        ]

    def chat(self, user_input: str) -> str:
        if not self.system_prompt_initialized:
            self.initialize_chat()
            
        self.messages.append({"role": "user", "content": user_input})
        
        while True:
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=self.messages,
                    tools=self.get_tools_definition(),
                    tool_choice="auto"
                )
                
                response_message = response.choices[0].message
                self.messages.append(response_message)
                
                if response_message.tool_calls:
                    for tool_call in response_message.tool_calls:
                        function_name = tool_call.function.name
                        function_args = json.loads(tool_call.function.arguments)
                        
                        # Call local tool
                        tool_result = execute_tool(function_name, function_args)
                        
                        self.messages.append({
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "name": function_name,
                            "content": tool_result
                        })
                    # Loop back to let the model respond to tool results
                    continue
                else:
                    return response_message.content or ""
                    
            except Exception as e:
                return f"Error communicating with LLM: {str(e)}"
