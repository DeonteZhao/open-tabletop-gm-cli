# Tasks

- [x] Task 1: 核心引擎逻辑适配 Web 调用
  - [x] SubTask 1.1: 梳理 `engine.py` 和 `campaign.py`，确保游戏循环、API调用、工具执行能够通过函数返回结果，而非仅依赖 CLI 的 `print`。
  - [x] SubTask 1.2: 支持在新建战役时指定游戏规则系统（默认为 `dnd5e`，支持 `coc7e`），并在加载战役时正确读取对应的 `system.md`。

- [x] Task 2: 构建 Web UI 基础服务与配置页
  - [x] SubTask 2.1: 引入轻量级 Web 框架（如 Gradio、Streamlit 或 Flask），创建 `webui.py`。
  - [x] SubTask 2.2: 实现配置页面，支持读取 `~/.config/open-tabletop-gm/config.json` 并通过 Web 表单保存配置。

- [x] Task 3: 构建 Web UI 战役大厅
  - [x] SubTask 3.1: 在 Web 界面展示所有已有战役存档的列表。
  - [x] SubTask 3.2: 在 Web 界面提供创建新战役的功能，允许输入战役名称并选择规则系统（D&D 5E 或 CoC 7E）。

- [x] Task 4: 构建 Web UI 游戏聊天界面
  - [x] SubTask 4.1: 实现聊天交互界面，加载战役后能够展示 `session-log.md` 中的历史记录（可选）或展示 AI GM 的欢迎语。
  - [x] SubTask 4.2: 实现玩家输入框，发送文本后调用 Engine 与 LLM 交互，将生成的叙事结果及脚本掷骰结果返回并渲染在界面上。

- [x] Task 5: 添加 CoC 7E 规则系统
  - [x] SubTask 5.1: 在 `systems/` 目录下创建 `coc7e` 文件夹。
  - [x] SubTask 5.2: 编写 `systems/coc7e/system.md`，定义 D100 检定机制、属性值、理智值（Sanity）、幸运、伤害与战斗等核心规则，供 AI GM 参考。
  - [x] SubTask 5.3: （可选）如果需要，在 `systems/coc7e/` 下添加针对性的辅助脚本（如创建人物卡的简单脚本），或复用全局 `scripts/dice.py`。

# Task Dependencies
- Task 1 是 Task 2, 3, 4 的基础（解耦核心逻辑）。
- Task 4 依赖 Task 3 的战役加载。
- Task 5 独立，可与 Web UI 并行开发，但需在 Task 3.2 之前提供系统的名称以供界面选择。
