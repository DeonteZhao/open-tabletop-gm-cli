# 增加 Web UI 与 CoC 7E 规则系统 Spec

## Why
目前项目主要通过 CLI 与用户交互，对非技术用户门槛较高。为了提供更直观、易用的体验，需要增加一个 Web UI，允许用户在浏览器中配置 API Key、管理战役存档，并进行聊天式的文字游戏。
另外，作为通用的 TTRPG 引擎，目前仅支持了 D&D 5E 规则。为了验证系统的通用性并满足玩家需求，需要新增克苏鲁的呼唤第 7 版（CoC 7E）规则系统支持。

## What Changes
- 新增 `webui.py`（推荐使用轻量级框架，如 Gradio 或 Flask+HTML），作为 Web UI 的启动入口。
- Web UI 包含三个主要模块：
  1. **配置页**：提供图形化表单，配置和保存 API Key、模型、基础 URL 等。
  2. **战役大厅**：展示现有战役存档列表，提供创建新战役（可选规则系统）和加载战役的入口。
  3. **游戏室**：类似聊天软件的交互界面，展示 AI GM 的叙事输出，并允许玩家输入文字指令（自然语言及斜杠命令）。
- 在 `systems/` 目录下新建 `coc7e/` 目录，并编写 `system.md` 以定义 CoC 7E 的 D100 百分骰机制、理智值（Sanity）、属性等核心规则。
- 重构部分创建战役（`main.py new` 或 `campaign.py`）的代码，使其支持在新建时记录或选择规则系统（dnd5e 或 coc7e）。

## Impact
- Affected specs: 扩展了原有的 CLI 交互模式，增加 Web 访问能力。
- Affected code: 
  - 新增 `webui.py`。
  - 新增 `systems/coc7e/system.md` 及相关支撑脚本（若需）。
  - 修改 `campaign.py` 或 `engine.py` 暴露接口供 Web 调用，确保核心逻辑不依赖于终端 `print` 和 `input`。

## ADDED Requirements
### Requirement: Web UI 交互界面
系统 SHALL 提供一个基于浏览器的操作界面，涵盖初始配置、战役管理与游戏交互功能。

#### Scenario: 玩家在 Web 上开始一场游戏
- **WHEN** 用户在终端运行 `python webui.py` 并打开本地浏览器地址
- **THEN** 用户可以在界面上填写 API Key，点击保存；随后点击“新建战役”并选择 CoC 7E 规则，进入聊天界面与 AI GM 开始文字交互。

### Requirement: CoC 7E 规则支持
系统 SHALL 内置 CoC 7E（Call of Cthulhu 7th Edition）的规则设定。

#### Scenario: 游戏内进行 CoC 7E 判定
- **WHEN** 玩家在 CoC 7E 规则战役中描述“我要侦查房间里的线索”
- **THEN** AI GM 根据 `systems/coc7e/system.md` 的规则，调用 D100 掷骰判定，并以 CoC 7E 的成功等级（大成功/极难/困难/常规/失败/大失败）叙述结果。
