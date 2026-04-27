# open-tabletop-gm-cli 🤖🎲

<p align="center">
  <strong>AI 跑团主持人 —— 本地运行、全中文、支持 D&D 5E / CoC 7E 双规则</strong>
</p>

<p align="center">
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.8+-blue.svg?logo=python&logoColor=white" alt="Python 3.8+"></a>
  <a href="./LICENSE"><img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License: MIT"></a>
  <a href="https://github.com/DeonteZhao/open-tabletop-gm-cli/stargazers"><img src="https://img.shields.io/github/stars/DeonteZhao/open-tabletop-gm-cli?style=social" alt="GitHub stars"></a>
</p>

<p align="center">
  <a href="#快速开始">快速开始</a> ·
  <a href="#特性">特性</a> ·
  <a href="#支持的模型厂商">模型厂商</a> ·
  <a href="#规则系统">规则系统</a> ·
  <a href="#命令速查">命令速查</a>
</p>

<p align="center">
  <b>中文</b> | <a href="./README_EN.md">English</a>
</p>

---

## 简介

基于 [Bobby-Gray/open-tabletop-gm](https://github.com/Bobby-Gray/open-tabletop-gm) 重构的**独立版 AI 跑团 GM**。无需 IDE、无需 Cursor/OpenCode，本地安装后直接运行。

用自然语言与 AI GM 对话（默认中文输出），骰子、战斗、法术位、SAN 检定、NPC 对话、剧情推进全部自动处理。

**与上游的主要区别：**
- 独立 CLI 应用，零 IDE 依赖
- 内置 Flask Web UI（`localhost:7860`），支持战役管理、聊天、模组导入
- 扩充国内 LLM 厂商支持，OpenAI 兼容接口即插即用
- 新增 CoC 7E（克苏鲁的呼唤）规则模块，与 D&D 5E 双系统可选
- 全中文本地化：界面、叙事、NPC 台词

---

## 特性

| 特性 | 说明 |
|------|------|
| 🖥️ **Web UI** | Flask 网页界面，含战役大厅、聊天、配置面板；D&D 战斗驾驶舱 / CoC 理智保险丝双面板 |
| 🤖 **多模型接入** | 任意 OpenAI 兼容接口。DeepSeek、Kimi、Qwen、GLM、SiliconFlow、豆包、百川、MiniMax、OpenAI、OpenRouter，或本地 LM Studio / Ollama |
| 🇨🇳 **中文优先** | 全部 UI 文本、GM 叙事、NPC 对话均为中文，无需写提示词 |
| 🐉 **双规则系统** | D&D 5E（西幻战斗）+ CoC 7E（克苏鲁调查、SAN 机制） |
| 📚 **模组导入** | 导入 PDF / DOCX / MD / TXT 模组，AI 自动解析地点、NPC、任务 |
| 🎮 **CLI + Web 双模式** | 命令行极简模式；Web 模式支持状态面板 + 局域网投屏 |
| ⚡ **工具调用引擎** | 骰子、战斗、状态追踪、日历/休息、投屏推送通过 OpenAI Function Calling 执行，规则计算零 LLM 参与 |

> 📸 界面截图将在后续版本补充。

---

## 快速开始

```bash
# 1. 克隆仓库
git clone https://github.com/DeonteZhao/open-tabletop-gm-cli.git
cd open-tabletop-gm-cli

# 2. 安装依赖（Python 3.8+）
pip install -r requirements.txt

# 3. 配置 LLM API
python main.py config
#   → 依次输入 API Key、Base URL、模型名称

# 4. 创建战役并开始游戏
python main.py new 我的战役 --system dnd5e
python main.py load 我的战役

# 5. 或启动 Web UI
python webui.py        # http://localhost:7860
```

> 🔴 **GitHub 无法访问？** 三种替代方案：
> - 加速代理：`git clone https://ghproxy.com/https://github.com/DeonteZhao/open-tabletop-gm-cli.git`
> - ZIP 下载：`https://github.com/DeonteZhao/open-tabletop-gm-cli/archive/refs/heads/main.zip`
> - Gitee 导入：仓库地址 `https://github.com/DeonteZhao/open-tabletop-gm-cli`

环境变量（优先级最高）：
```bash
export OPENAI_API_KEY="sk-xxx"
export OPENAI_BASE_URL="https://api.deepseek.com/v1"
export OPENAI_MODEL="deepseek-chat"
```

---

## 支持的模型厂商

任意 OpenAI 兼容接口均可接入。以下为已验证的国内厂商（无需 VPN）：

| 厂商 | Base URL | 推荐模型 |
|------|----------|----------|
| **深度求索 DeepSeek** | `https://api.deepseek.com/v1` | `deepseek-chat`, `deepseek-reasoner` |
| **硅基流动 SiliconFlow** | `https://api.siliconflow.cn/v1` | `Qwen/Qwen2.5-72B-Instruct`, `deepseek-ai/DeepSeek-V3` |
| **月之暗面 Kimi** | `https://api.moonshot.cn/v1` | `moonshot-v1-8k` |
| **阿里云 通义千问** | `https://dashscope.aliyuncs.com/compatible-mode/v1` | `qwen-plus`, `qwen-max` |
| **智谱 AI GLM** | `https://open.bigmodel.cn/api/paas/v4` | `glm-4-flash`, `glm-4-plus` |
| **字节跳动 豆包** | `https://ark.cn-beijing.volces.com/api/v3` | `doubao-pro-32k` |
| **百川智能** | `https://api.baichuan-ai.com/v1` | `Baichuan4` |
| **MiniMax** | `https://api.minimax.chat/v1` | `abab6.5s-chat` |
| **OpenAI** | `https://api.openai.com/v1` | `gpt-4o`, `gpt-4o-mini` |
| **OpenRouter** | `https://openrouter.ai/api/v1` | 聚合多模型统一接入 |
| **本地模型** | `http://localhost:1234/v1` | LM Studio / Ollama |

配置文件：`~/.config/open-tabletop-gm/config.json`（权限 600）。

---

## 命令速查

### CLI 子命令

```bash
python main.py config                    # 交互式配置向导
python main.py new <战役名> --system dnd5e   # 新建 D&D 战役
python main.py new <战役名> --system coc7e   # 新建 CoC 战役
python main.py list                      # 列出所有战役
python main.py load <战役名>             # 加载并开始游戏
python main.py import <战役名> <文件路径>    # 导入模组到战役
```

### 游戏内斜杠命令

| 命令 | 功能 |
|------|------|
| `/save` | 保存进度 |
| `/end` | 保存并退出 |
| `/quit` | 不保存退出 |
| `/recap` | 查看当前状态摘要 |
| `/world` | 查看世界设定 |
| `/npcs` | 查看 NPC 列表 |
| `/import <文件路径>` | 导入模组 |
| `/help` | 显示所有命令 |

### Web UI

```bash
python webui.py                                   # 默认端口 7860
OPEN_TABLETOP_GM_WEBUI_PORT=8080 python webui.py  # 自定义端口
```

浏览器访问 `http://localhost:7860`，功能：
- 战役大厅（创建 / 加载 / 管理）
- 配置面板（随时切换 API 厂商）
- 聊天界面（实时叙事）
- 模组导入（拖拽上传）
- 系统专属面板：D&D 战斗驾驶舱 / CoC 理智保险丝 + 线索板

---

## 规则系统

### D&D 5E（龙与地下城第五版）
经典西幻冒险。回合制战斗，AI 自动处理 d20 检定、HP/AC 追踪、法术位管理、状态效果。

### CoC 7E（克苏鲁的呼唤第七版）
1920 年代调查恐怖。d100 技能检定、**SAN（理智值）机制**——目睹不可名状之物将损失理智，归零则永久疯狂。AI GM 擅长营造悬疑与压迫感。

---

## 模组导入

导入第三方冒险模组，AI GM 依据模组内容主持游戏。

**支持格式：** 文字版 PDF、DOCX、Markdown、TXT（扫描版/纯图片 PDF 需先 OCR）

**CLI 导入：**
```bash
python main.py import 我的战役 /path/to/模组.pdf
```

**Web UI 导入：** 战役页面拖拽上传

**模组来源：** DMsGuild（D&D）、混沌元素官方（CoC）、[魔都 TRPG](https://www.contraband-panda.com/)（中文 CoC）、或社区自制模组

---

## 项目结构

```
open-tabletop-gm-cli/
  main.py              ← CLI 入口
  webui.py             ← Flask Web UI 入口
  engine.py            ← LLM 引擎（OpenAI 兼容 API + 工具调用）
  config.py            ← 配置管理（~/.config/open-tabletop-gm/）
  cli.py               ← CLI 游戏循环
  commands.py          ← 斜杠命令分发
  campaign.py          ← 战役增删改查
  tools.py             ← 工具执行（骰子、战斗、追踪、日历、投屏）
  importer.py          ← PDF/DOCX/MD/TXT 模组导入
  requirements.txt     ← openai, PyMuPDF, Flask, python-docx
  systems/
    dnd5e/             ← D&D 5E 规则模块
    coc7e/             ← CoC 7E 规则模块
  webui_templates/     ← Jinja2 模板
  webui_static/        ← CSS, JS, 图标
  display/             ← 投屏伴侣组件（来自上游）
  scripts/             ← 骰子、战斗、追踪、日历脚本
  templates/           ← 战役文件空白模板
```

战役数据存储在仓库外：`~/.local/share/open-tabletop-gm/campaigns/<战役名>/`
包含：`state.md`、`world.md`、`npcs.md`、`session-log.md`、`character-sheet.md`

---

## 技术说明

- **Engine → LLM**：通过 OpenAI 兼容接口调用，启用 Function Calling。系统 prompt 由 `SKILL.md` + `systems/<系统>/system.md` + 战役状态文件动态组装。
- **Engine → Tools**：本地 Python 脚本通过 subprocess 执行，零外部依赖（纯标准库）。
- **工具调用循环**：LLM 决定何时调用 `dice`、`combat`、`tracker`、`calendar`、`display_send`，工具结果回输给 LLM 继续生成叙事。
- **OpenRouter 兼容**：自动注入 `HTTP-Referer` 和 `X-Title` 请求头。

---

## 致谢

本项目基于 [Bobby-Gray/open-tabletop-gm](https://github.com/Bobby-Gray/open-tabletop-gm) 重构，原项目为 Claude Code Skill 框架。独立 CLI 版去除了 IDE 依赖，新增 Web UI、扩充 LLM 厂商支持、新增 CoC 7E 规则模块，并完成全中文本地化。

---

## License

[MIT License](./LICENSE)
