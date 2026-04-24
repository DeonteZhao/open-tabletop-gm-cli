import os
import gradio as gr
from config import get_config, Config, CONFIG_FILE
from campaign import create_campaign, list_campaigns
from engine import Engine
import time
import sys

# Global state to keep track of the loaded engine
current_engine = None
campaign_loaded = ""

def save_config(api_key, base_url, model):
    config = Config()
    config.api_key = api_key.strip()
    config.base_url = base_url.strip()
    config.model = model.strip()
    try:
        config.save()
        return f"配置已保存到 {CONFIG_FILE}"
    except Exception as e:
        return f"保存配置失败: {e}"

def load_config_ui():
    config = get_config()
    return config.api_key, config.base_url, config.model

def get_campaigns():
    return list_campaigns(print_out=False)

def create_new_campaign(name, system):
    if not name.strip():
        return "战役名称不能为空！", gr.update(choices=get_campaigns())
    success = create_campaign(name.strip(), system)
    if success:
        return f"战役 '{name}' ({system}) 创建成功！", gr.update(choices=get_campaigns())
    else:
        return f"创建战役 '{name}' 失败，可能已存在或模板缺失。", gr.update(choices=get_campaigns())

def load_selected_campaign(name):
    global current_engine, campaign_loaded
    if not name:
        return "请先选择一个战役！", gr.update(value=None)
    
    config = get_config()
    if not config.api_key:
        return "尚未配置 API Key！请先在【配置管理】中设置。", gr.update(value=None)
    
    try:
        current_engine = Engine(name)
        current_engine.initialize_chat()
        campaign_loaded = name
        
        # 获取开场白
        init_msg = "Please give a short introductory greeting and describe the current scene to start the session. You must reply in Chinese."
        response = current_engine.chat(init_msg)
        
        chat_history = [[None, response]]
        return f"已加载战役：{name}", gr.update(value=chat_history)
    except Exception as e:
        return f"加载战役失败: {e}", gr.update(value=None)

def chat_with_gm(user_message, history):
    global current_engine
    if not current_engine:
        history.append([user_message, "错误：请先在【战役大厅】中加载一个战役！"])
        return "", history
    
    if not user_message.strip():
        return "", history
        
    history.append([user_message, None])
    yield "", history
    
    try:
        response = current_engine.chat(user_message)
        history[-1][1] = response
        yield "", history
    except Exception as e:
        history[-1][1] = f"引擎通信错误: {e}"
        yield "", history


with gr.Blocks(title="Open Tabletop GM Web UI") as app:
    gr.Markdown("# Open Tabletop GM 🎲")
    
    with gr.Tabs():
        # === 标签页 1：战役大厅 ===
        with gr.Tab("战役大厅"):
            gr.Markdown("### 现有战役")
            with gr.Row():
                campaign_dropdown = gr.Dropdown(choices=get_campaigns(), label="选择战役")
                load_btn = gr.Button("加载战役", variant="primary")
            
            load_status = gr.Textbox(label="状态", interactive=False)
            
            gr.Markdown("### 新建战役")
            with gr.Row():
                new_camp_name = gr.Textbox(label="新战役名称", placeholder="例如：迷雾镇冒险")
                new_camp_sys = gr.Dropdown(choices=["dnd5e", "coc7e"], value="dnd5e", label="规则系统")
                create_btn = gr.Button("创建战役")
            
            create_status = gr.Textbox(label="创建结果", interactive=False)
            
            create_btn.click(
                fn=create_new_campaign, 
                inputs=[new_camp_name, new_camp_sys], 
                outputs=[create_status, campaign_dropdown]
            )

        # === 标签页 2：游戏聊天室 ===
        with gr.Tab("游戏室"):
            chatbot = gr.Chatbot(label="AI GM", height=600)
            msg = gr.Textbox(label="你的行动", placeholder="输入你想做的事情，例如：我环顾四周...", lines=2)
            send_btn = gr.Button("发送", variant="primary")
            
            load_btn.click(
                fn=load_selected_campaign,
                inputs=[campaign_dropdown],
                outputs=[load_status, chatbot]
            )
            
            msg.submit(
                fn=chat_with_gm,
                inputs=[msg, chatbot],
                outputs=[msg, chatbot]
            )
            send_btn.click(
                fn=chat_with_gm,
                inputs=[msg, chatbot],
                outputs=[msg, chatbot]
            )

        # === 标签页 3：配置管理 ===
        with gr.Tab("配置管理"):
            gr.Markdown("设置你的 LLM API Key 与模型。如果使用第三方代理（如 OpenRouter 或国内模型），请填写对应的 Base URL。")
            with gr.Column():
                api_key_input = gr.Textbox(label="API Key", type="password")
                base_url_input = gr.Textbox(label="Base URL (可选)", placeholder="https://api.openai.com/v1")
                model_input = gr.Textbox(label="Model", value="gpt-4o", placeholder="gpt-4o, qwen-max, etc.")
                save_config_btn = gr.Button("保存配置", variant="primary")
                config_status = gr.Textbox(label="保存状态", interactive=False)
            
            # Load initial config
            app.load(fn=load_config_ui, inputs=[], outputs=[api_key_input, base_url_input, model_input])
            
            save_config_btn.click(
                fn=save_config,
                inputs=[api_key_input, base_url_input, model_input],
                outputs=[config_status]
            )

if __name__ == "__main__":
    app.launch(server_name="127.0.0.1", server_port=7860, inbrowser=False)
