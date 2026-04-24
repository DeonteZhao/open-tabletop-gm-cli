# Tasks

- [x] Task 1: 项目基础结构与依赖配置
  - [x] SubTask 1.1: 创建 `requirements.txt` 并添加 `openai>=1.0.0` 及 PDF 解析相关基础库（如 `PyMuPDF` 或 `pdfplumber`，视需）。
  - [x] SubTask 1.2: 建立项目基础目录结构，准备好 `templates/` 模板文件和空白的 `SKILL.md`。

- [x] Task 2: 配置管理模块 (`config.py`)
  - [x] SubTask 2.1: 实现从环境变量读取配置的功能。
  - [x] SubTask 2.2: 实现从 `~/.config/open-tabletop-gm/config.json` 读取和保存配置的功能（处理文件权限为 600）。
  - [x] SubTask 2.3: 实现 `python main.py config` 交互式向导。

- [x] Task 3: 战役管理模块 (`campaign.py`)
  - [x] SubTask 3.1: 实现 `python main.py new <name>`，复制 `templates/` 下的模板文件到 `~/.local/share/open-tabletop-gm/campaigns/<name>/`。
  - [x] SubTask 3.2: 实现 `python main.py list`，列出所有现有存档。

- [x] Task 4: 核心引擎与 LLM 交互 (`engine.py`)
  - [x] SubTask 4.1: 构建 System Prompt 组装逻辑（拼接 `SKILL.md`、`systems/dnd5e/system.md` 和战役状态文件摘要）。
  - [x] SubTask 4.2: 实现基于 OpenAI Python SDK 的 API 调用封装，支持多种兼容 API 的 LLM。
  - [x] SubTask 4.3: 实现 Tool Call Loop，解析 LLM 调用的工具。

- [x] Task 5: 本地脚本工具调用机制 (`tools.py`)
  - [x] SubTask 5.1: 使用 `subprocess.run()` 封装调用 `scripts/*.py`（如 `dice.py`, `combat.py`）的逻辑。
  - [x] SubTask 5.2: 将脚本调用结果捕获并格式化返回给 LLM。

- [x] Task 6: 终端交互与斜杠命令 (`cli.py` & `commands.py`)
  - [x] SubTask 6.1: 实现 `python main.py load <name>` 进入游戏的主循环（接收自然语言输入）。
  - [x] SubTask 6.2: 实现 `/save`, `/end`, `/quit`, `/recap`, `/world`, `/npcs`, `/help` 等基础斜杠命令。

- [x] Task 7: 外部模组导入机制 (`importer.py`)
  - [x] SubTask 7.1: 实现 `python main.py import` 和 `/import` 命令，支持 PDF 文本解析。
  - [x] SubTask 7.2: 实现长文本分块处理，并调用 AI GM 提取关键内容追加写入到战役设定文件（`world.md`, `npcs.md`, `state.md`）。

- [x] Task 8: CLI 主入口集成 (`main.py`)
  - [x] SubTask 8.1: 整合配置、战役、引擎、导入等模块，使用 `argparse` 或类似库解析命令行参数。
  - [x] SubTask 8.2: 处理异常与错误提示（API 调用失败、无配置等）。

# Task Dependencies
- Task 2 独立进行。
- Task 3 依赖 Task 1。
- Task 4 依赖 Task 2, Task 3。
- Task 5 独立进行，为 Task 4 提供支持。
- Task 6 依赖 Task 4, Task 5。
- Task 7 依赖 Task 4, Task 3。
- Task 8 依赖所有上述任务。
