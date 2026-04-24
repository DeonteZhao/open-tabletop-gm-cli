import os
import subprocess
import json
from typing import Dict, Any

def get_project_root() -> str:
    return os.path.dirname(os.path.abspath(__file__))

def execute_tool(tool_name: str, arguments: Dict[str, Any]) -> str:
    """
    Translates OpenAI tool calls to the original command-line scripts.
    """
    root = get_project_root()
    
    cmd = []
    
    if tool_name == "dice":
        script_path = os.path.join(root, 'scripts', 'dice.py')
        cmd = ["python", script_path, arguments.get("notation", "")]
        if arguments.get("silent"):
            cmd.append("--silent")
            
    elif tool_name == "combat":
        script_path = os.path.join(root, 'scripts', 'combat.py')
        cmd = ["python", script_path, arguments.get("action", "")]
        for key, value in arguments.items():
            if key != "action" and value is not None:
                if key == "json_data":
                    cmd.append(str(value))
                else:
                    cmd.append(f"--{key}")
                    cmd.append(str(value))
                    
    elif tool_name == "tracker":
        script_path = os.path.join(root, 'scripts', 'tracker.py')
        cmd = ["python", script_path, "-c", arguments.get("campaign", "default")]
        action = arguments.get("action", "")
        cmd.append(action)
        for key, value in arguments.items():
            if key not in ["action", "campaign"] and value is not None:
                cmd.append(str(value))
                
    elif tool_name == "calendar":
        script_path = os.path.join(root, 'scripts', 'calendar.py')
        cmd = ["python", script_path, "-c", arguments.get("campaign", "default")]
        action = arguments.get("action", "")
        cmd.append(action)
        for key, value in arguments.items():
            if key not in ["action", "campaign"] and value is not None:
                cmd.append(f"--{key}")
                cmd.append(str(value))
                
    elif tool_name == "lookup":
        script_path = os.path.join(root, 'systems', 'dnd5e', 'lookup.py')
        cmd = ["python", script_path, arguments.get("category", ""), arguments.get("query", "")]
        
    elif tool_name == "display_send":
        # Send narration or stats to display/send.py
        script_path = os.path.join(root, 'display', 'send.py')
        cmd = ["python", script_path]
        
        # Add flags
        if arguments.get("player"):
            cmd.extend(["--player", arguments["player"]])
        if arguments.get("npc"):
            cmd.extend(["--npc", arguments["npc"]])
        if arguments.get("dice"):
            cmd.append("--dice")
        if arguments.get("tutor"):
            cmd.append("--tutor")
        if arguments.get("stat_hp"):
            cmd.extend(["--stat-hp", arguments["stat_hp"]])
        if arguments.get("stat_condition_add"):
            cmd.extend(["--stat-condition-add", arguments["stat_condition_add"]])
            
        # We need to pass the text via stdin
        text = arguments.get("text", "")
        try:
            result = subprocess.run(
                cmd,
                input=text,
                capture_output=True,
                text=True,
                check=False
            )
            return json.dumps({"status": "success", "output": "Sent to display."})
        except Exception as e:
            return json.dumps({"status": "error", "error_message": str(e)})

    if not cmd:
        return json.dumps({"status": "error", "error_message": f"Unknown tool: {tool_name}"})
        
    if not os.path.exists(cmd[1]):
        return json.dumps({"status": "error", "error_message": f"Script not found: {cmd[1]}"})

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False
        )
        if result.returncode != 0:
            return json.dumps({
                "status": "error",
                "return_code": result.returncode,
                "error_message": result.stderr.strip(),
                "partial_output": result.stdout.strip()
            }, ensure_ascii=False)
            
        return json.dumps({
            "status": "success",
            "output": result.stdout.strip()
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({"status": "error", "error_message": str(e)}, ensure_ascii=False)
