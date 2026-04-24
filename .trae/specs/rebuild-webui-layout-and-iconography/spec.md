# WebUI 全新布局与图标统一 Spec

## Why
当前实现仅完成了颜色和局部样式替换，仍然保留了原有的 Gradio 默认布局结构，无法体现该设计系统要求的“页面级仪表板布局”和“组件即机械装置”的体验。
同时，项目还缺少统一的图标与矢量图形规则，导致导航、状态、规则系统语义和视觉语言无法保持一致。

## What Changes
- 以页面布局重构为目标，重新设计 Web UI 的信息架构，而不是继续在现有布局上做配色微调。
- 为战役大厅、游戏室、配置区建立符合设计系统的桌面端主布局与移动端退化策略。
- 引入统一的图标与矢量资源规范，所有导航、状态、检定、规则系统入口都遵守 `ui conponent` 的单线图标规则。
- 为 D&D 5e 与 CoC 7E 定义共享布局骨架和系统差异化模块，例如 CoC 的理智保险丝、d100 检定器、调查员侧栏。
- 明确技术落点：若当前 `webui.py` / Gradio 结构无法承载页面级布局与图标系统，允许迁移到更适合的 Web UI 方案。
- **BREAKING** 现有仅靠 CSS 覆盖的 UI 方案不再视为目标实现，后续将以完整布局重构为准。

## Impact
- Affected specs: Web UI 布局、导航结构、组件系统、图标系统、双规则系统界面语义。
- Affected code: `webui.py`、前端静态资源目录、模板文件、图标/矢量资产、与聊天/战役/配置交互相关的 UI 层。

## ADDED Requirements
### Requirement: 页面级布局重构
系统 SHALL 提供符合 Open Tabletop GM 设计规则的全新页面布局，而不是仅替换现有控件样式。

#### Scenario: Success case
- **WHEN** 用户打开 Web UI
- **THEN** 用户首先看到的是清晰的页面级结构，例如导航区、主舞台区、侧边状态区或系统面板区，而不是默认控件的线性堆叠。

### Requirement: 双系统界面骨架
系统 SHALL 为 D&D 5e 与 CoC 7E 提供共享骨架下的差异化模块，并在界面中正确表达系统语义。

#### Scenario: CoC 7E success case
- **WHEN** 用户进入 CoC 7E 战役
- **THEN** 界面包含调查员信息、理智相关状态、d100 检定语义与 CoC 专属状态反馈。

#### Scenario: D&D 5e success case
- **WHEN** 用户进入 D&D 5e 战役
- **THEN** 界面包含角色资源、行动入口、战斗与规则浏览的 D&D 专属模块表达。

### Requirement: 图标与矢量一致性
系统 SHALL 采用统一的单线图标与矢量图形规范，所有图标、分隔、点阵装饰和状态图形必须遵守 `ui conponent` 技能定义。

#### Scenario: Success case
- **WHEN** 用户浏览导航、按钮、状态标签、规则入口和系统面板
- **THEN** 所有图标具有统一的线宽、轮廓风格、颜色继承规则与尺寸等级，不出现混杂风格或临时图形。

### Requirement: 技术方案适配布局
系统 SHALL 选择能够承载该布局和图标体系的实现方案。

#### Scenario: Success case
- **WHEN** 现有 UI 技术栈无法稳定支持页面布局、图标注入、静态资源组织或响应式结构
- **THEN** 实现可以迁移到更适合的模板化 Web UI 架构，但必须保留现有业务能力。

## MODIFIED Requirements
### Requirement: Web UI 优化范围
“优化 UI” 的定义修改为页面结构、导航、组件、图标和矢量系统的整体重构，而不是仅调整配色、字体和局部 CSS。

### Requirement: 资产组织方式
UI 相关样式、图标和矢量资源必须具备可维护的目录和命名约定，避免继续将所有视觉规则堆叠在单一脚本中的临时 CSS 块中。

## REMOVED Requirements
### Requirement: 仅样式覆盖即可达成设计目标
**Reason**: 该方式无法满足页面级布局、组件系统与图标一致性的要求。
**Migration**: 后续实现需改为基于布局骨架、组件规范和图标资产系统的完整 UI 重构方案。
