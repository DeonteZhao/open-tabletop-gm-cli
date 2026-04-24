# Open-Tabletop-GM CLI App Spec

## Why
当前开源项目 Open-Tabletop-GM 依赖 IDE 环境（如 OpenCode、Cursor）才能运行。我们需要将其改造为一个独立的 CLI 应用程序，使用户能够在终端中直接使用自然语言和 AI Game Master 游玩 D&D 5e 等 TTRPG 游戏，降低使用门槛。

## What Changes
- 创建入口文件 `main.py` 以支持 CLI 命令行交互。
- 实现配置管理（向导式配置、配置文件存取、环境变量解析）。
- 实现战役管理功能（创建战役 `new`、加载战役 `load`、列出战役 `list`）。
- 构建 Engine 核心逻辑：系统提示词组装、与 LLM 的 API 交互（基于 OpenAI 兼容 API）、Tool Call 循环处理。
- 集成外部脚本调用机制：通过 `subprocess.run()` 零修改调用现有工具脚本（如 `dice.py` 等）。
- 实现终端内的自然语言交互与斜杠命令解析（`/save`, `/end`, `/recap`, `/import` 等）。
- 实现 PDF 模组导入与分块处理机制。

## Impact
- Affected specs: 增加了独立运行的 CLI 能力，新增本地配置管理和多 LLM 平台支持。
- Affected code: 新增 `main.py`、`config.py`、`engine.py`、`campaign.py`、`commands.py` 等核心引擎文件，保持原有 `scripts/` 和 `systems/` 下的文件不被修改。

## ADDED Requirements
### Requirement: 独立 CLI 启动与配置
The system SHALL 提供 `config` 子命令引导用户配置 LLM API，支持通过环境变量、配置文件优先级读取。

#### Scenario: 首次运行配置
- **WHEN** 用户执行 `python main.py config`
- **THEN** 终端提示选择 LLM 提供商、输入 API Key 和选择语言，并保存至 `~/.config/open-tabletop-gm/config.json`（权限 600）。

### Requirement: 战役生命周期管理
The system SHALL 支持 `new`, `list`, `load` 等战役管理命令，自动从模板复制初始状态文件。

### Requirement: 核心游戏循环 (Tool Call Loop)
The system SHALL 在 `load` 后进入游戏循环，读取玩家输入，组装上下文发送给 LLM，解析 Function Calling 并调用本地 Python 脚本，将结果回传给 LLM 进行叙事。

### Requirement: PDF 模组导入
The system SHALL 支持解析外部 PDF 模组（长文档分块），由 AI GM 提取信息并写入战役世界设定。
