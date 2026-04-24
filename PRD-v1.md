# Open-Tabletop-GM Engine — PRD v1

## 背景

开源项目 https://github.com/Bobby-Gray/open-tabletop-gm 是一个以 Python 脚本驱动游戏机制、LLM 驱动叙事与裁判的桌面 RPG 框架。目前它需要配合 OpenCode、Cursor 等具备 skill 能力的 IDE 使用，无法独立运行。

## 产品目标

做一个独立的 CLI 应用。用户 `git clone` + `pip install` + 配置 LLM API Key 后，在终端里直接用自然语言和 AI Game Master 玩 D&D 5e（可扩展到其他 TTRPG 系统）。不需要任何 IDE、不需要编程知识。

## 目标用户

- 会打开终端、会输入命令行的人
- 有 LLM API Key（或愿意注册一个）
- 不需要懂 D&D 规则、不需要会编程
- 中国大陆用户必须能用（支持国内主流 LLM + 全中文交互）

---

## 1. 用户使用流程

### 1.1 首次使用

```
git clone https://github.com/xxx/open-tabletop-gm.git
cd open-tabletop-gm
pip install -r requirements.txt
python main.py config
  → 选择 LLM 提供商（OpenRouter / OpenAI / DeepSeek / 阿里通义千问 / 月之暗面 Kimi 等）
  → 粘贴 API Key
  → 选择模型
  → 选择语言（中文 / English，默认中文）

python main.py new 迷雾镇冒险
python main.py load 迷雾镇冒险
  → AI GM 用中文开始讲述故事
```

### 1.2 导入 PDF 模组游玩

除了从零开始，玩家也可以下载第三方 D&D 冒险模组（PDF/DOCX/Markdown 格式），由 AI GM 自动解析并整合到战役中：

```python main.py import /path/to/龙枪模组.pdf --campaign 龙枪传说```

AI GM 读取 PDF 文本，将模组中的地点、NPC、任务提取并写入对应战役文件，然后基于模组内容开始主持游戏。

### 1.3 日常游玩

```python main.py list          # 查看所有存档
python main.py load 迷雾镇冒险  # 继续上次冒险
```

### 1.3 配置方式优先级

从最高到最低：环境变量 > 配置文件 > 交互式向导。

环境变量支持：`OPENTTG_API_KEY`、`OPENTTG_BASE_URL`、`OPENTTG_MODEL`、`OPENTTG_LANGUAGE`。

配置文件位置：`~/.config/open-tabletop-gm/config.json`。

---

## 2. 核心交互模式

游戏是纯文字、回合制的对话：

```
> 我推门走进酒馆，观察里面的人

你推开沉重的木门，门轴发出吱呀声响。酒馆内部比你想象的
宽敞，壁炉里的火噼啪作响。你注意到——

吧台后的红发女人擦着同一个杯子，眼睛却盯着门口。
角落里有三个穿深色斗篷的陌生人低声交谈。
一个老水手用报纸挡着脸，但报纸拿反了。

你要做什么？

> 我走向吧台，和那个女人说话

红发女人抬眼看了你一眼，擦杯子的手顿了一下。
"喝点什么，旅行者？"她的声音平淡，但眼神在暗示什么。

> /save
[已保存]

> /end
保存并退出。下次用 `python main.py load 迷雾镇冒险` 继续！
```

### 2.1 玩家输入分两种

**自然语言**（大多数情况）：玩家描述行动，AI GM 判断何时需要掷骰/战斗/查规则，自动调用工具，然后给出叙事。

**斜杠命令**：

| 命令 | 功能 |
|------|------|
| `/save` | 保存当前进度 |
| `/end`, `/quit` | 保存并退出 |
| `/recap` | 回顾当前状态（HP、地点、任务） |
| `/world` | 显示世界设定 |
| `/npcs` | 显示 NPC 列表 |
| `/import <filepath>` | 导入 PDF/DOCX/Markdown 模组 |
| `/help` | 显示可用命令 |

### 2.2 骰子与战斗

当玩家做出需要掷骰的行动时，AI GM 自动处理，玩家不需要手动输入命令：

```
> 我拔出长剑攻击地精

你的剑刃划出一道银弧。
🎲 攻击检定：d20 + 5 = 17 → 命中！
⚔️ 伤害：1d8 + 3 = 7

剑锋切入地精的肩膀，绿色血液溅了一地。
地精发出尖锐的哀嚎。

战斗状态：
  ► 你      HP: 30/30
    地精    HP: 6/13  [流血]

地精红着眼睛举起弯刀反击！
🎲 地精攻击检定：d20 + 4 = 12 → 未命中！

弯刀擦着你的护甲划过，没有造成伤害。

轮到你了。
```

### 2.3 导入外部模组

玩家可以导入网上下载的 D&D 冒险模组（PDF/DOCX/Markdown），让 AI GM 将其内容整合到战役中。

**触发方式：**

```
> /import /path/to/冰风谷模组.pdf

正在解析模组文件...
📄 文件：冰风谷模组.pdf
📝 字数：24,600
📦 分块：7

AI GM 正在读取模组内容...
```

**AI GM 的处理流程：**

```
AI GM 读取 PDF 提取的文本 → 解析模组结构 → 提取关键内容 → 写入战役文件

提取的内容包括：
  - 地点/场景 → 追加到 world.md
  - NPC（姓名、性格、目标） → 追加到 npcs.md
  - 任务/线索/剧情节点 → 追加到 state.md
  - 怪物统计 → 供 GM 战斗时参考

AI GM 基于模组设定开始主持游戏，玩家按模组剧情推进。
```

**大文件分块处理：**

对于超过 4000 词的 PDF，AI GM 分多次读取（通过 `--chunk N` 参数），逐步消化模组内容，避免单次上下文溢出。

**限制：**

- 扫描版 PDF（纯图片）无法提取文字，会提示失败
- 模组内容需由 AI GM 适配和本土化（整合到当前战役世界，调整难度适配玩家等级）

### 2.4 长休与短休

当玩家在游戏中提到休息（或 GM 主动提议）时，系统自动处理：

```
> 我们在山洞里扎营，准备长休

[执行长休机制...]

火把在洞壁上投下摇曳的影子。你们轮流守夜，在不安的睡眠
中度过了8个小时。

长休完成：
  ✓ HP 已完全恢复
  ✓ 法术位已恢复
  ✓ 解除了所有临时状态效果

第二天清晨，雾气弥漫在山谷间...
```

---

## 3. 核心引擎行为

### 3.1 Engine 与上游（LLM）的通信

Engine 通过 OpenAI 兼容 API 与 LLM 通信。向 LLM 发送的 system prompt 由以下部分组成：

1. 项目根目录的 `SKILL.md` — 定义 AI GM 的人格、叙事风格、游戏规则运用方式
2. `systems/dnd5e/system.md` — D&D 5e 规则上下文
3. 当前战役文件（`state.md`、`world.md`）的摘要
4. 可用的工具说明（让 LLM 知道何时调用掷骰、战斗、追踪器等）

### 3.2 Engine 与下游（Python 脚本）的通信

当 LLM 判断需要游戏机制介入时，通过 function calling 请求工具。Engine 将这些请求翻译为命令行调用，执行对应的 Python 脚本，捕获输出，返回给 LLM 继续叙事。

涉及的脚本包括但不限于：

| 脚本 | 用途 |
|------|------|
| `scripts/dice.py` | 掷骰（d20+5、2d6、优势/劣势等） |
| `scripts/combat.py` | 先攻排序、攻击判定、伤害计算 |
| `scripts/tracker.py` | 状态追踪（中毒/流血/昏迷/死亡豁免等） |
| `scripts/calendar.py` | 游戏内时间推进、短休/长休 |
| `systems/dnd5e/lookup.py` | SRD 规则查询（法术/物品/怪物） |

**重要约束**：这些脚本用 `subprocess.run()` 调用，不改动脚本源码。脚本本身是零依赖的标准库工具。

### 3.3 Tool Call Loop

一次典型的游戏回合内部流程：

```
1. 玩家输入自然语言
2. Engine 发送给 LLM
3. LLM 决定"这里需要掷骰" → 返回 tool_calls
4. Engine 调用对应脚本 → 获取结果
5. 结果返回 LLM → LLM 生成叙事
6. 如果 LLM 还需要更多工具（比如先掷骰再算伤害），重复 3-5
7. 最终叙事输出给玩家
```

### 3.4 显示伴侣（可选）

Engine 可以通过 `display/send.py` 和 `display/push_stats.py` 将叙事、骰子结果、角色状态推送到浏览器。如果显示伴侣未启动，推送失败必须静默处理，不中断游戏。

---

## 4. 中文支持

### 4.1 默认语言是中文

首次配置时，默认选项是中文。玩家按回车即可选择。

### 4.2 所有 CLI 界面文本支持中文

- 配置向导用中文
- 斜杠命令的提示/回显用中文
- 错误信息用中文
- 保存路径支持中文文件名（如 `迷雾镇冒险`）

### 4.3 AI GM 用中文叙事

通过 system prompt 中的语言指令块告知 LLM：始终用中文叙事、中文 NPC 对话、中文规则解释。数字保留阿拉伯数字但结果用中文叙述。

### 4.4 脚本输出不改

`dice.py`、`combat.py` 等脚本的输出保持英文（它们是底层工具），LLM 负责将英文结果翻译为中文叙事。不对现有脚本做任何修改。

---

## 5. LLM 提供商支持

必须支持以下提供商，全部通过 OpenAI 兼容 API 接入：

**国际：**
- OpenRouter
- OpenAI
- 本地模型（LM Studio / Ollama）

**中国大陆：**
- 深度求索 DeepSeek
- 阿里云 通义千问 Qwen
- 月之暗面 Kimi
- 智谱 AI GLM
- 字节跳动 豆包
- 百川智能
- MiniMax
- 硅基流动 SiliconFlow

每家提供商的区别只有 `base_url` 和 `model_name`。不需要写任何提供商特定的代码。

---

## 6. 战役管理

### 6.1 创建战役

`python main.py new <name>` 创建一个新存档：
- 在 `~/.local/share/open-tabletop-gm/campaigns/<name>/` 下建立目录
- 复制 `templates/` 下的空白模板文件（`state.md`、`world.md`、`npcs.md`、`character-sheet.md`、`session-log.md`）

### 6.2 保存与读取

- 战役进度保存在本地 Markdown 文件中（纯文本，人工可读）
- 每次 `/save` 或 `/end` 时，当前会话的叙事内容追加到 `session-log.md`
- AI GM 可以通过工具读写 `state.md`、`world.md`、`npcs.md` 来更新游戏状态

### 6.3 列出战役

`python main.py list` 显示所有存档列表。

---

## 7. 战役文件模板

`templates/` 目录下的文件是 AI GM 的工作空间，Engine 将这些文件内容注入到 system prompt 中：

| 文件 | 用途 |
|------|------|
| `state.md` | 当前战役状态（任务进度、HP、状态效果等） |
| `world.md` | 世界设定（地理、势力、威胁弧线） |
| `npcs.md` | NPC 信息（性格、关系、隐藏目标） |
| `character-sheet.md` | 玩家角色卡 |
| `session-log.md` | 会话日志 |

这些文件是上游项目已有的，不动它们。

---

## 8. 非功能性需求

### 8.1 依赖最小化

- 唯一的 Python 包依赖是 `openai>=1.0.0`
- 所有现有的 `scripts/*.py` 保持零外部依赖（纯标准库）
- 如果 `openai` 包未安装，给出友好提示：`pip install -r requirements.txt`

### 8.2 配置安全

- API Key 存储在 `~/.config/open-tabletop-gm/config.json`
- 文件权限设为 `600`（仅所有者可读写）
- 绝不在日志或终端输出中打印 API Key

### 8.3 失败策略

- 显示伴侣调用失败 → 静默忽略，游戏继续
- LLM API 调用失败 → 打印错误信息，等待重试
- 脚本执行失败 → 将错误信息返回给 LLM，LLM 决定如何处理
- 战役文件不存在 → 创建空文件继续

---

## 9. 验收标准

### 场景 A：首次安装与配置
- 用户 `git clone` 项目
- 运行 `pip install -r requirements.txt` 成功
- 运行 `python main.py config`，完成交互式配置（选择提供商、输入 API Key、选择模型、选择中文）
- 配置保存到 `~/.config/open-tabletop-gm/config.json`

### 场景 B：创建并开始游戏
- `python main.py new 迷雾镇冒险` 成功创建存档
- `python main.py load 迷雾镇冒险` 连接 LLM，AI GM 用中文输出开场叙事
- 玩家输入自然语言，AI GM 用中文回应

### 场景 C：战斗中自动掷骰
- 玩家输入"我用长剑攻击地精"
- AI GM 自动调用掷骰脚本、攻击判定脚本
- 玩家看到中文叙述的攻击结果（命中/未命中、伤害数值）
- 不需要玩家手动输入任何 `/roll` 命令

### 场景 D：斜杠命令
- `/save` → 保存当前进度
- `/recap` → 显示当前 HP、地点、任务等状态摘要
- `/end` → 保存并退出
- `/help` → 显示命令列表

### 场景 E：环境变量覆盖
- 删除或重命名配置文件
- 通过 `OPENTTG_API_KEY=xxx OPENTTG_MODEL=yyy python main.py load 迷雾镇冒险` 直接进入游戏
- 环境变量优先级高于配置文件

### 场景 F：国内 LLM
- 配置阿里云 Qwen，游戏正常进行
- 配置月之暗面 Kimi，游戏正常进行
- 叙事为中文，骰子结果用中文叙述

### 场景 G：无配置错误提示
- 在没有配置文件也没有环境变量的情况下运行 `python main.py load xxx`
- 终端显示中文提示："还未配置 LLM API，请先运行：python main.py config"

### 场景 H：导入 PDF 模组
- 准备一个 D&D 冒险模组 PDF 文件
- 在游戏中输入 `/import /path/to/模组.pdf`
- AI GM 读取 PDF 内容，提取地点/NPC/任务
- 模组内容被写入 `world.md`、`npcs.md`、`state.md`
- AI GM 基于模组设定开始主持游戏
- 大文件（>4000词）自动分块处理

---

## 10. 扩展性说明（V1 不做，但架构要预留）

以下功能在 V1 中不需要实现，但架构设计不应阻碍它们：

- **多玩家支持**：多人通过浏览器/手机加入同一游戏
- **Web UI**：除 CLI 外的浏览器界面
- **音频**：自动播放音效和背景音乐
- **非 D&D 5e 系统**：通过 `systems/TEMPLATE.md` 添加新 TTRPG 规则
- **流式输出**：打字机效果的逐字显示
