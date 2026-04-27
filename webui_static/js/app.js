(function () {
  const stateNode = document.getElementById("webui-state");
  if (!stateNode) {
    return;
  }

  const spriteUrl = document.body.dataset.spriteUrl || "";
  const state = JSON.parse(stateNode.textContent || "{}");
  const uiState = {
    apiKeyModified: false,
    loadingCampaignName: "",
    importingModule: false,
  };
  const CAMPAIGN_NAME_DISPLAY_LIMIT = 14;

  const elements = {
    navLinks: Array.from(document.querySelectorAll("[data-view-target]")),
    stages: Array.from(document.querySelectorAll("[data-view]")),
    campaignGrid: document.getElementById("campaign-grid"),
    campaignCount: document.getElementById("campaign-count"),
    campaignForm: document.getElementById("campaign-form"),
    campaignName: document.getElementById("campaign-name"),
    campaignSystem: document.getElementById("campaign-system"),
    importForm: document.getElementById("import-form"),
    importCampaignName: document.getElementById("import-campaign-name"),
    importCampaignSystem: document.getElementById("import-campaign-system"),
    importSource: document.getElementById("import-source"),
    importSourceTrigger: document.getElementById("import-source-trigger"),
    importSubmit: document.getElementById("import-submit"),
    importFeedback: document.getElementById("import-feedback"),
    chatForm: document.getElementById("chat-form"),
    chatInput: document.getElementById("chat-input"),
    chatSubmit: document.getElementById("chat-submit"),
    chatLog: document.getElementById("chat-log"),
    chatCampaign: document.getElementById("chat-campaign"),
    chatSystem: document.getElementById("chat-system"),
    saveCampaignButton: document.getElementById("save-campaign-button"),
    deleteCurrentCampaignButton: document.getElementById("delete-current-campaign-button"),
    configForm: document.getElementById("config-form"),
    provider: document.getElementById("config-provider"),
    apiKey: document.getElementById("config-api-key"),
    apiKeyToggle: document.getElementById("config-api-key-toggle"),
    apiKeyHint: document.getElementById("config-api-key-hint"),
    model: document.getElementById("config-model"),
    providerHint: document.getElementById("config-provider-hint"),
    configSaveFeedback: document.getElementById("config-save-feedback"),
    configSubmit: document.getElementById("config-submit"),
    statusCampaign: document.getElementById("status-campaign"),
    statusSystem: document.getElementById("status-system"),
    statusReady: document.getElementById("status-ready"),
    statusMessage: document.getElementById("status-message"),
    modulePanel: document.getElementById("module-panel") || document.querySelector(".system-panel"),
    moduleIcon: document.getElementById("module-icon"),
    moduleTitle: document.getElementById("module-title"),
    moduleTagline: document.getElementById("module-tagline"),
    moduleResourceLabel: document.getElementById("module-resource-label"),
    moduleResourceValue: document.getElementById("module-resource-value"),
    moduleResourceMeter: document.getElementById("module-resource-meter"),
    moduleInsightLabel: document.getElementById("module-insight-label"),
    moduleInsightValue: document.getElementById("module-insight-value"),
    specializedSystemBlock: document.getElementById("specialized-system-block"),
  };

  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function escapeAttribute(value) {
    return escapeHtml(value).replace(/`/g, "&#96;");
  }

  function renderInlineMarkdown(text) {
    const inlineCodeTokens = [];
    let html = escapeHtml(text);

    html = html.replace(/`([^`\n]+)`/g, (_, code) => {
      const token = `@@INLINE_CODE_${inlineCodeTokens.length}@@`;
      inlineCodeTokens.push(`<code>${code}</code>`);
      return token;
    });

    html = html.replace(
      /\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/gi,
      (_, label, url) =>
        `<a href="${escapeAttribute(url)}" target="_blank" rel="noreferrer noopener">${label}</a>`,
    );
    html = html.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
    html = html.replace(/\*([^*\n]+)\*/g, "<em>$1</em>");

    return html.replace(/@@INLINE_CODE_(\d+)@@/g, (_, index) => inlineCodeTokens[Number(index)] || "");
  }

  function renderMarkdown(source) {
    const normalized = String(source || "").replace(/\r\n/g, "\n").trim();
    if (!normalized) {
      return "";
    }

    const codeBlockTokens = [];
    const tokenized = normalized.replace(/```([a-z0-9_-]+)?\n([\s\S]*?)```/gi, (_, language = "", code) => {
      const token = `@@CODE_BLOCK_${codeBlockTokens.length}@@`;
      const languageClass = language ? ` class="language-${escapeAttribute(language)}"` : "";
      const safeCode = escapeHtml(code.replace(/\n$/, ""));
      codeBlockTokens.push(`<pre class="md-code-block"><code${languageClass}>${safeCode}</code></pre>`);
      return token;
    });

    const lines = tokenized.split("\n");
    const blocks = [];

    function isSpecialLine(line) {
      return (
        /^@@CODE_BLOCK_\d+@@$/.test(line) ||
        /^#{1,3}\s+/.test(line) ||
        /^\s*(?:---+|\*\*\*+|___+)\s*$/.test(line) ||
        /^>\s?/.test(line) ||
        /^[-*]\s+/.test(line) ||
        /^\d+\.\s+/.test(line)
      );
    }

    for (let index = 0; index < lines.length; ) {
      const line = lines[index];

      if (!line.trim()) {
        index += 1;
        continue;
      }

      if (/^@@CODE_BLOCK_\d+@@$/.test(line)) {
        blocks.push(line);
        index += 1;
        continue;
      }

      if (/^\s*(?:---+|\*\*\*+|___+)\s*$/.test(line)) {
        blocks.push("<hr>");
        index += 1;
        continue;
      }

      const headingMatch = line.match(/^(#{1,3})\s+(.*)$/);
      if (headingMatch) {
        const level = headingMatch[1].length;
        blocks.push(`<h${level}>${renderInlineMarkdown(headingMatch[2].trim())}</h${level}>`);
        index += 1;
        continue;
      }

      if (/^>\s?/.test(line)) {
        const quoteLines = [];
        while (index < lines.length && /^>\s?/.test(lines[index])) {
          quoteLines.push(lines[index].replace(/^>\s?/, ""));
          index += 1;
        }
        blocks.push(`<blockquote>${renderInlineMarkdown(quoteLines.join("\n")).replace(/\n/g, "<br>")}</blockquote>`);
        continue;
      }

      if (/^[-*]\s+/.test(line)) {
        const items = [];
        while (index < lines.length && /^[-*]\s+/.test(lines[index])) {
          items.push(`<li>${renderInlineMarkdown(lines[index].replace(/^[-*]\s+/, "").trim())}</li>`);
          index += 1;
        }
        blocks.push(`<ul>${items.join("")}</ul>`);
        continue;
      }

      if (/^\d+\.\s+/.test(line)) {
        const items = [];
        while (index < lines.length && /^\d+\.\s+/.test(lines[index])) {
          items.push(`<li>${renderInlineMarkdown(lines[index].replace(/^\d+\.\s+/, "").trim())}</li>`);
          index += 1;
        }
        blocks.push(`<ol>${items.join("")}</ol>`);
        continue;
      }

      const paragraphLines = [];
      while (index < lines.length && lines[index].trim() && !isSpecialLine(lines[index])) {
        paragraphLines.push(lines[index]);
        index += 1;
      }
      blocks.push(`<p>${renderInlineMarkdown(paragraphLines.join("\n")).replace(/\n/g, "<br>")}</p>`);
    }

    return blocks
      .join("")
      .replace(/@@CODE_BLOCK_(\d+)@@/g, (_, tokenIndex) => codeBlockTokens[Number(tokenIndex)] || "");
  }

  function truncateCampaignName(value) {
    const text = String(value || "").trim();
    if (text.length <= CAMPAIGN_NAME_DISPLAY_LIMIT) {
      return text;
    }
    return `${text.slice(0, CAMPAIGN_NAME_DISPLAY_LIMIT)}...`;
  }

  function renderIcon(name, className = "icon") {
    return `<svg class="${className}" aria-hidden="true"><use href="${spriteUrl}#icon-${name}"></use></svg>`;
  }

  function activateView(viewName) {
    elements.navLinks.forEach((link) => {
      link.classList.toggle("is-active", link.dataset.viewTarget === viewName);
    });
    elements.stages.forEach((stage) => {
      stage.classList.toggle("is-active", stage.dataset.view === viewName);
    });
  }

  function buildMeter(ratio, system) {
    const safeRatio = Math.max(0, Math.min(1, Number(ratio) || 0));
    const filledCount = Math.round(safeRatio * 10);
    const segments = [];

    for (let index = 0; index < 10; index += 1) {
      let className = "segment";
      if (index < filledCount) {
        className += " filled";
      }
      if (system === "coc7e" && index >= 7) {
        className = index < filledCount ? "segment filled" : "segment insanity";
      }
      segments.push(`<span class="${className}"></span>`);
    }

    return segments.join("");
  }

  function currentSystemMeta() {
    const fallback = {
      label: "DND",
      tagline: "英雄史诗",
      theme: "dnd5e",
      module_icon: "shield",
      resource_label: "HP / AC / 先攻",
      resource_value: "32 / 16 / +3",
      resource_ratio: 0.72,
      resource_meter: "heroic",
      insight_label: "会话摘要",
      insight_value: "集中维持中 / 法术位 3 / 4 / 死亡豁免 0 / 3",
      specialized_panel: null,
    };
    return state.system_meta || fallback;
  }

  function systemIcon(system) {
    return system === "coc7e" ? "brain" : "shield";
  }

  function messageIcon(role) {
    return role === "user" ? "user" : "spark";
  }

  function pushInlineStatus(message) {
    state.status_message = message;
    renderStatus();
  }

  function setConfigFeedback(message, tone = "neutral") {
    if (!elements.configSaveFeedback) {
      return;
    }
    elements.configSaveFeedback.textContent = message;
    elements.configSaveFeedback.dataset.tone = tone;
  }

  function setImportFeedback(message, tone = "neutral") {
    if (!elements.importFeedback) {
      return;
    }
    elements.importFeedback.textContent = message;
    elements.importFeedback.dataset.tone = tone;
  }

  function setButtonBusy(button, busy, busyLabel) {
    if (!button) {
      return;
    }
    const labelNode = button.querySelector("span");
    if (!button.dataset.idleLabel && labelNode) {
      button.dataset.idleLabel = labelNode.textContent || "";
    }
    button.disabled = busy;
    button.classList.toggle("is-loading", busy);
    button.setAttribute("aria-busy", busy ? "true" : "false");
    if (labelNode) {
      labelNode.textContent = busy ? busyLabel : (button.dataset.idleLabel || labelNode.textContent);
    }
  }

  function syncImportSourceButton() {
    if (!elements.importSourceTrigger) {
      return;
    }
    const source = elements.importSource.files && elements.importSource.files[0];
    const labelNode = elements.importSourceTrigger.querySelector("span");
    if (!elements.importSourceTrigger.dataset.idleLabel && labelNode) {
      elements.importSourceTrigger.dataset.idleLabel = labelNode.textContent || "导入模组";
    }
    if (labelNode) {
      labelNode.textContent = source ? source.name : (elements.importSourceTrigger.dataset.idleLabel || "导入模组");
    }
    elements.importSourceTrigger.classList.toggle("is-selected", Boolean(source));
  }

  function renderApiKeyHint() {
    if (!elements.apiKeyHint) {
      return;
    }

    const config = state.config || {};
    if (uiState.apiKeyModified) {
      elements.apiKeyHint.textContent = "检测到 API Key 已修改，保存时会写入新值。";
      return;
    }

    if (config.api_key_configured) {
      elements.apiKeyHint.textContent = "已检测到现有 API Key；前端不会回填明文，留空提交会保留原 Key。";
      return;
    }

    elements.apiKeyHint.textContent = "尚未保存 API Key；输入后仅在保存时提交。";
  }

  function renderCampaigns() {
    const campaigns = Array.isArray(state.campaigns) ? state.campaigns : [];
    elements.campaignCount.textContent = `${campaigns.length} 个项目`;

    if (!campaigns.length) {
      elements.campaignGrid.innerHTML = [
        '<article class="empty-card">',
        '<p class="eyebrow">空状态</p>',
        renderIcon("book-open", "icon icon-empty"),
        "<h3>暂无战役</h3>",
        "<p class=\"card-copy\">先创建一个 DND 或 COC 战役，布局会自动切换到对应系统语义。</p>",
        "</article>",
      ].join("");
      return;
    }

    elements.campaignGrid.innerHTML = campaigns
      .map((campaign) => {
        const icon = systemIcon(campaign.system);
        return [
          `<article class="campaign-card" data-campaign="${escapeHtml(campaign.name)}">`,
          '<div class="card-header">',
          "<div>",
          '<p class="eyebrow">战役</p>',
          `<h3 class="campaign-card-title" title="${escapeHtml(campaign.name)}">${escapeHtml(campaign.display_name || truncateCampaignName(campaign.name))}</h3>`,
          "</div>",
          `<span class="chip">${renderIcon(icon, "icon icon-xs")}<span>${escapeHtml(campaign.system_label)}</span></span>`,
          "</div>",
          `<p class="card-copy">${escapeHtml(campaign.tagline)}</p>`,
          '<div class="resource-meter" aria-hidden="true">',
          "<span class=\"segment filled\"></span>".repeat(6) +
            "<span class=\"segment\"></span>".repeat(4),
          "</div>",
          '<div class="card-actions">',
          `<button class="button secondary card-action-main" type="button" data-action="load-campaign" data-campaign="${escapeHtml(campaign.name)}">${renderIcon("door")}<span>进入游戏室</span></button>`,
          `<button class="button ghost danger icon-only" type="button" data-action="delete-campaign" data-campaign="${escapeHtml(campaign.name)}" aria-label="删除战役" title="删除战役">${renderIcon("trash")}<span class="sr-only">删除</span></button>`,
          "</div>",
          "</article>",
        ].join("");
      })
      .join("");
  }

  function renderChat() {
    const history = Array.isArray(state.chat_history) ? state.chat_history : [];
    const isLoadingCampaign = Boolean(uiState.loadingCampaignName);
    elements.chatSubmit.disabled = !state.chat_ready || isLoadingCampaign;
    elements.chatInput.disabled = !state.chat_ready || isLoadingCampaign;
    if (elements.saveCampaignButton) {
      elements.saveCampaignButton.disabled = !state.current_campaign;
    }
    if (elements.deleteCurrentCampaignButton) {
      elements.deleteCurrentCampaignButton.disabled = !state.current_campaign;
    }

    if (isLoadingCampaign) {
      elements.chatCampaign.textContent = uiState.loadingCampaignName;
      elements.chatSystem.textContent = "INITIALIZING";
    } else if (state.current_campaign) {
      elements.chatCampaign.textContent = state.current_campaign.name;
      elements.chatSystem.textContent = state.current_campaign.system_label;
    } else {
      elements.chatCampaign.textContent = "等待载入战役";
      elements.chatSystem.textContent = "SYSTEM OFFLINE";
    }

    if (isLoadingCampaign) {
      elements.chatLog.innerHTML = [
        '<article class="empty-card chat-empty is-loading-state">',
        '<p class="eyebrow">载入中</p>',
        renderIcon("spark", "icon icon-empty"),
        `<h3>正在进入 ${escapeHtml(uiState.loadingCampaignName)}</h3>`,
        '<p class="card-copy">正在初始化 AI GM、读取战役文件并生成开场内容，请稍候。</p>',
        "</article>",
      ].join("");
      return;
    }

    if (!history.length) {
      elements.chatLog.innerHTML = [
        '<article class="empty-card chat-empty">',
        '<p class="eyebrow">待机</p>',
        renderIcon("chat", "icon icon-empty"),
        "<h3>尚未进入战役</h3>",
        "<p class=\"card-copy\">加载战役后会在这里显示开场白与后续聊天记录。</p>",
        "</article>",
      ].join("");
      return;
    }

    elements.chatLog.innerHTML = history
      .map((message) => {
        const roleLabel = message.role === "user" ? "玩家输入" : "AI GM";
        const content = renderMarkdown(message.content);
        return [
          `<article class="chat-message ${escapeHtml(message.role)}">`,
          `<p class="eyebrow">${renderIcon(messageIcon(message.role), "icon icon-xs")}<span>${roleLabel}</span></p>`,
          `<div class="message-body">${content}</div>`,
          "</article>",
        ].join("");
      })
      .join("");

    elements.chatLog.scrollTop = elements.chatLog.scrollHeight;
  }

  function renderStatus() {
    const systemMeta = currentSystemMeta();
    if (
      !elements.modulePanel ||
      !elements.moduleIcon ||
      !elements.moduleTitle ||
      !elements.moduleTagline ||
      !elements.moduleResourceLabel ||
      !elements.moduleResourceValue ||
      !elements.moduleResourceMeter ||
      !elements.moduleInsightLabel ||
      !elements.moduleInsightValue ||
      !elements.specializedSystemBlock
    ) {
      return;
    }

    elements.statusCampaign.textContent = state.current_campaign ? state.current_campaign.name : "未载入";
    elements.statusSystem.textContent = state.current_campaign ? state.current_campaign.system_label : "待选择";
    if (uiState.loadingCampaignName) {
      elements.statusCampaign.textContent = uiState.loadingCampaignName;
      elements.statusReady.textContent = "加载中";
      elements.statusMessage.textContent = `正在载入战役：${uiState.loadingCampaignName}`;
    } else {
      elements.statusReady.textContent = state.chat_ready ? "在线" : "待命";
      elements.statusMessage.textContent = state.status_message || "等待操作。";
    }

    elements.modulePanel.className = `panel system-panel system-panel-${systemMeta.theme || "dnd5e"}`;
    elements.moduleIcon.innerHTML = `<use href="${spriteUrl}#icon-${systemMeta.module_icon || "shield"}"></use>`;
    elements.moduleTitle.textContent = systemMeta.label;
    elements.moduleTagline.textContent = systemMeta.tagline;
    elements.moduleResourceLabel.textContent = systemMeta.resource_label;
    elements.moduleResourceValue.textContent = systemMeta.resource_value;
    elements.moduleInsightLabel.textContent = systemMeta.insight_label;
    elements.moduleInsightValue.textContent = systemMeta.insight_value;
    elements.moduleResourceMeter.className = `resource-meter ${systemMeta.resource_meter || "heroic"}`;
    elements.moduleResourceMeter.innerHTML = buildMeter(systemMeta.resource_ratio, state.current_campaign && state.current_campaign.system);
    elements.specializedSystemBlock.innerHTML = renderSpecializedPanel(systemMeta);
  }

  function buildSegments(total, filled, toneClass = "") {
    const segments = [];
    for (let index = 0; index < total; index += 1) {
      const classes = ["segment"];
      if (index < filled) {
        classes.push("filled");
      }
      if (toneClass) {
        classes.push(toneClass);
      }
      segments.push(`<span class="${classes.join(" ")}"></span>`);
    }
    return segments.join("");
  }

  function renderDndPanel(panel) {
    const stats = (panel.battle_stats || [])
      .map((stat) => {
        return [
          '<div class="battle-stat-card">',
          `<span class="feature-stat-label">${renderIcon(stat.icon || "shield", "icon icon-xs")}<span>${escapeHtml(stat.label)}</span></span>`,
          `<strong>${escapeHtml(stat.value)}</strong>`,
          "</div>",
        ].join("");
      })
      .join("");

    const tracks = (panel.resource_tracks || [])
      .map((track) => {
        return [
          '<div class="resource-track-card">',
          '<div class="meter-meta">',
          `<span>${renderIcon(track.icon || "heart", "icon icon-xs")}${escapeHtml(track.label)}</span>`,
          `<strong>${escapeHtml(track.value)}</strong>`,
          "</div>",
          `<div class="resource-meter ${escapeHtml(track.tone || "")} compact">${buildSegments(Number(track.segments) || 0, Number(track.filled) || 0)}</div>`,
          "</div>",
        ].join("");
      })
      .join("");

    return [
      '<section class="specialized-panel specialized-panel-dnd">',
      '<div class="specialized-panel-head">',
      "<div>",
      `<p class="eyebrow">${escapeHtml(panel.eyebrow || "专属组件")}</p>`,
      `<h4>${escapeHtml(panel.title || "")}</h4>`,
      "</div>",
      renderIcon("swords"),
      "</div>",
      `<div class="battle-stat-grid">${stats}</div>`,
      '<div class="resource-track-stack">',
      tracks,
      "</div>",
      "</section>",
    ].join("");
  }

  function renderCocPanel(panel) {
    const sanity = panel.sanity || {};
    const current = Number(sanity.current) || 0;
    const max = Number(sanity.max) || 1;
    const erosion = Number(sanity.erosion) || 0;
    const filled = Math.max(0, Math.min(10, Math.round((current / max) * 10)));
    const erosionSegments = Math.max(0, Math.min(10, Math.round((erosion / 100) * 10)));
    const fuse = [];
    for (let index = 0; index < 10; index += 1) {
      const classes = ["segment"];
      if (index < filled) {
        classes.push("filled");
      } else if (index >= 10 - erosionSegments) {
        classes.push("insanity");
      }
      fuse.push(`<span class="${classes.join(" ")}"></span>`);
    }

    const check = panel.d100_check || {};
    return [
      '<section class="specialized-panel specialized-panel-coc">',
      '<div class="specialized-panel-head">',
      "<div>",
      `<p class="eyebrow">${escapeHtml(panel.eyebrow || "专属组件")}</p>`,
      `<h4>${escapeHtml(panel.title || "")}</h4>`,
      "</div>",
      renderIcon("brain"),
      "</div>",
      '<div class="sanity-fuse-card">',
      '<div class="meter-meta">',
      `<span>${renderIcon("brain", "icon icon-xs")}${escapeHtml(sanity.label || "Sanity Fuse")}</span>`,
      `<strong>${escapeHtml(String(current))} / ${escapeHtml(String(max))}</strong>`,
      "</div>",
      `<div class="resource-meter sanity fuse">${fuse.join("")}</div>`,
      `<p class="sanity-footnote">Mythos ${escapeHtml(String(erosion))}% / Breakpoint ${escapeHtml(sanity.breakpoint || "")}</p>`,
      "</div>",
      '<div class="d100-check-card">',
      '<p class="eyebrow">d100 检定</p>',
      '<div class="d100-head">',
      `<strong>${escapeHtml(check.skill || "Skill Check")}</strong>`,
      `<span class="chip chip-tone-${(check.outcome || "").includes("成功") ? "success" : "danger"}">${escapeHtml(check.outcome || "")}</span>`,
      "</div>",
      '<div class="d100-roll">',
      `<span class="d100-digit">${escapeHtml(String(check.tens ?? ""))}</span>`,
      `<span class="d100-digit">${escapeHtml(String(check.ones ?? ""))}</span>`,
      "</div>",
      `<p class="d100-footnote">Target ≤ ${escapeHtml(String(check.target ?? ""))} / Hard ≤ ${escapeHtml(String(check.hard ?? ""))} / Extreme ≤ ${escapeHtml(String(check.extreme ?? ""))}</p>`,
      "</div>",
      "</section>",
    ].join("");
  }

  function renderSpecializedPanel(systemMeta) {
    const panel = systemMeta.specialized_panel;
    if (!panel) {
      return "";
    }
    if (panel.kind === "coc7e") {
      return renderCocPanel(panel);
    }
    return renderDndPanel(panel);
  }

  function renderConfig() {
    const config = state.config || {};
    elements.provider.value = config.provider || "openai";
    elements.model.value = config.model || "";
    elements.apiKey.placeholder = config.api_key_configured ? "已存在，留空则保持不变" : "sk-...";
    if (elements.apiKeyToggle) {
      const isVisible = elements.apiKey.type === "text";
      elements.apiKeyToggle.setAttribute("aria-pressed", isVisible ? "true" : "false");
      elements.apiKeyToggle.querySelector("span").textContent = isVisible ? "隐藏" : "显示";
    }
    renderApiKeyHint();
    renderProviderHint();
  }

  function renderImport() {
    syncImportSourceButton();
    setButtonBusy(elements.importSubmit, uiState.importingModule, "正在导入...");
    if (elements.importSourceTrigger) {
      elements.importSourceTrigger.disabled = uiState.importingModule;
    }
  }

  function renderProviderHint() {
    const selectedOption = elements.provider.options[elements.provider.selectedIndex];
    if (!selectedOption) {
      return;
    }

    const baseUrl = selectedOption.dataset.baseUrl || "";
    const modelPlaceholder = selectedOption.dataset.modelPlaceholder || "gpt-4o";
    elements.model.placeholder = modelPlaceholder;

    if (elements.providerHint) {
      elements.providerHint.textContent = `当前提供商地址：${baseUrl}`;
    }
  }

  function renderAll() {
    renderCampaigns();
    renderChat();
    renderStatus();
    renderConfig();
    renderImport();
  }

  async function requestJson(url, method, payload) {
    const options = {
      method,
      headers: {},
    };
    if (payload !== undefined) {
      options.headers["Content-Type"] = "application/json";
      options.body = JSON.stringify(payload);
    }

    const response = await fetch(url, options);

    const data = await response.json();
    if (!response.ok || !data.ok) {
      throw new Error(data.message || "请求失败");
    }
    return data;
  }

  async function postJson(url, payload) {
    return requestJson(url, "POST", payload);
  }

  async function deleteJson(url) {
    return requestJson(url, "DELETE");
  }

  async function postForm(url, formData) {
    const response = await fetch(url, {
      method: "POST",
      body: formData,
    });

    const data = await response.json();
    if (!response.ok || !data.ok) {
      throw new Error(data.message || "请求失败");
    }
    return data;
  }

  function mergeState(nextState) {
    Object.keys(state).forEach((key) => {
      delete state[key];
    });
    Object.assign(state, nextState);
    renderAll();
  }

  elements.navLinks.forEach((link) => {
    link.addEventListener("click", () => {
      activateView(link.dataset.viewTarget);
    });
  });

  elements.campaignGrid.addEventListener("click", async (event) => {
    const button = event.target.closest("[data-action]");
    if (!button) {
      return;
    }

    if (button.dataset.action === "delete-campaign") {
      const campaignName = button.dataset.campaign || "";
      const confirmed = window.confirm(`确定要删除战役“${campaignName}”吗？此操作不可撤销。`);
      if (!confirmed) {
        return;
      }

      button.disabled = true;
      try {
        const data = await deleteJson(`/api/campaigns/${encodeURIComponent(campaignName)}`);
        mergeState(data.state);
        if (!state.current_campaign) {
          activateView("campaigns");
        }
      } catch (error) {
        pushInlineStatus(error.message);
      } finally {
        button.disabled = false;
      }
      return;
    }

    if (button.dataset.action !== "load-campaign") {
      return;
    }

    uiState.loadingCampaignName = button.dataset.campaign || "";
    setButtonBusy(button, true, "载入中...");
    pushInlineStatus(`正在载入战役：${uiState.loadingCampaignName}`);
    activateView("chat");
    renderAll();
    try {
      const [data] = await Promise.all([
        postJson("/api/campaigns/load", { name: button.dataset.campaign }),
        new Promise((resolve) => window.setTimeout(resolve, 600)),
      ]);
      uiState.loadingCampaignName = "";
      mergeState(data.state);
      activateView("chat");
    } catch (error) {
      uiState.loadingCampaignName = "";
      activateView("campaigns");
      pushInlineStatus(error.message);
    } finally {
      setButtonBusy(button, false, "载入中...");
      renderAll();
    }
  });

  if (elements.saveCampaignButton) {
    elements.saveCampaignButton.addEventListener("click", async () => {
      elements.saveCampaignButton.disabled = true;
      try {
        const data = await postJson("/api/campaigns/save", {});
        mergeState(data.state);
      } catch (error) {
        pushInlineStatus(error.message);
      } finally {
        elements.saveCampaignButton.disabled = !state.current_campaign;
      }
    });
  }

  if (elements.deleteCurrentCampaignButton) {
    elements.deleteCurrentCampaignButton.addEventListener("click", async () => {
      const currentCampaign = state.current_campaign && state.current_campaign.name;
      if (!currentCampaign) {
        pushInlineStatus("当前没有可删除的战役。");
        return;
      }

      const confirmed = window.confirm(`确定要删除当前战役“${currentCampaign}”吗？此操作不可撤销。`);
      if (!confirmed) {
        return;
      }

      elements.deleteCurrentCampaignButton.disabled = true;
      try {
        const data = await deleteJson(`/api/campaigns/${encodeURIComponent(currentCampaign)}`);
        mergeState(data.state);
        activateView("campaigns");
      } catch (error) {
        pushInlineStatus(error.message);
      } finally {
        elements.deleteCurrentCampaignButton.disabled = !state.current_campaign;
      }
    });
  }

  elements.campaignForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const payload = {
      name: elements.campaignName.value,
      system: elements.campaignSystem.value,
    };

    try {
      const data = await postJson("/api/campaigns", payload);
      mergeState(data.state);
      elements.campaignForm.reset();
    } catch (error) {
      pushInlineStatus(error.message);
    }
  });

  elements.importForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const source = elements.importSource.files && elements.importSource.files[0];
    if (!source) {
      setImportFeedback("请先选择要导入的模组文件。", "danger");
      pushInlineStatus("请先选择要导入的模组文件。");
      return;
    }

    try {
      uiState.importingModule = true;
      renderImport();
      setImportFeedback(`正在导入 ${source.name}...`, "neutral");
      pushInlineStatus("正在导入模组...");
      const formData = new FormData();
      formData.append("name", elements.importCampaignName.value.trim());
      formData.append("system", elements.importCampaignSystem.value);
      formData.append("source", source);
      const data = await postForm("/api/import-module", formData);
      mergeState(data.state);
      elements.importForm.reset();
      syncImportSourceButton();
      setImportFeedback(data.message || "导入成功。", "success");
      pushInlineStatus(data.message);
    } catch (error) {
      setImportFeedback(error.message, "danger");
      pushInlineStatus(error.message);
    } finally {
      uiState.importingModule = false;
      renderAll();
    }
  });

  elements.configForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const payload = {
      provider: elements.provider.value,
      api_key: uiState.apiKeyModified ? elements.apiKey.value : "",
      api_key_modified: uiState.apiKeyModified,
      model: elements.model.value,
    };

    try {
      setConfigFeedback("正在保存配置...", "neutral");
      setButtonBusy(elements.configSubmit, true, "正在保存...");
      const data = await postJson("/api/config", payload);
      uiState.apiKeyModified = false;
      elements.apiKey.value = "";
      mergeState(data.state);
      setConfigFeedback(data.message || "配置保存成功。", "success");
    } catch (error) {
      setConfigFeedback(error.message, "danger");
      pushInlineStatus(error.message);
    } finally {
      setButtonBusy(elements.configSubmit, false, "正在保存...");
    }
  });

  elements.provider.addEventListener("change", () => {
    renderProviderHint();
  });

  if (elements.importSourceTrigger) {
    elements.importSourceTrigger.addEventListener("click", () => {
      elements.importSource.click();
    });
  }

  if (elements.importSource) {
    elements.importSource.addEventListener("change", () => {
      syncImportSourceButton();
      if (elements.importSource.files && elements.importSource.files[0]) {
        setImportFeedback(`已选择文件：${elements.importSource.files[0].name}`, "neutral");
      } else {
        setImportFeedback("等待导入。", "neutral");
      }
    });
  }

  if (elements.apiKey) {
    elements.apiKey.addEventListener("input", () => {
      uiState.apiKeyModified = true;
      renderApiKeyHint();
    });
  }

  if (elements.apiKeyToggle) {
    elements.apiKeyToggle.addEventListener("click", () => {
      const isVisible = elements.apiKey.type === "text";
      elements.apiKey.type = isVisible ? "password" : "text";
      elements.apiKeyToggle.setAttribute("aria-pressed", isVisible ? "false" : "true");
      elements.apiKeyToggle.querySelector("span").textContent = isVisible ? "显示" : "隐藏";
    });
  }

  elements.chatForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const message = elements.chatInput.value.trim();
    if (!message) {
      return;
    }

    elements.chatSubmit.disabled = true;
    try {
      const data = await postJson("/api/chat", { message });
      mergeState(data.state);
      elements.chatInput.value = "";
    } catch (error) {
      pushInlineStatus(error.message);
    } finally {
      elements.chatSubmit.disabled = !state.chat_ready;
    }
  });

  renderAll();
  elements.moduleResourceMeter.innerHTML = buildMeter(
    currentSystemMeta().resource_ratio,
    state.current_campaign && state.current_campaign.system
  );
})();
