(function () {
  const stateNode = document.getElementById("webui-state");
  if (!stateNode) {
    return;
  }

  const spriteUrl = document.body.dataset.spriteUrl || "";
  const state = JSON.parse(stateNode.textContent || "{}");

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
    chatForm: document.getElementById("chat-form"),
    chatInput: document.getElementById("chat-input"),
    chatSubmit: document.getElementById("chat-submit"),
    chatLog: document.getElementById("chat-log"),
    chatCampaign: document.getElementById("chat-campaign"),
    chatSystem: document.getElementById("chat-system"),
    configForm: document.getElementById("config-form"),
    apiKey: document.getElementById("config-api-key"),
    baseUrl: document.getElementById("config-base-url"),
    model: document.getElementById("config-model"),
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
    featureModules: document.getElementById("feature-modules"),
    quickActions: document.getElementById("quick-actions"),
    statusTags: document.getElementById("status-tags"),
    ruleEntries: document.getElementById("rule-entries"),
  };

  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
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
      label: "D&D 5E",
      tagline: "英雄史诗",
      theme: "dnd5e",
      module_icon: "shield",
      resource_label: "HP / AC / 先攻",
      resource_value: "32 / 16 / +3",
      resource_ratio: 0.72,
      resource_meter: "heroic",
      insight_label: "战斗面板",
      insight_value: "资源、条件、行动入口",
      status_tags: [],
      quick_actions: [],
      rule_entries: [],
      feature_modules: [],
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

  function renderCampaigns() {
    const campaigns = Array.isArray(state.campaigns) ? state.campaigns : [];
    elements.campaignCount.textContent = `${campaigns.length} 个项目`;

    if (!campaigns.length) {
      elements.campaignGrid.innerHTML = [
        '<article class="empty-card">',
        '<p class="eyebrow">空状态</p>',
        renderIcon("book-open", "icon icon-empty"),
        "<h3>暂无战役</h3>",
        "<p class=\"card-copy\">先创建一个 D&D 5E 或 CoC 7E 战役，布局会自动切换到对应系统语义。</p>",
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
          `<h3>${escapeHtml(campaign.name)}</h3>`,
          "</div>",
          `<span class="chip">${renderIcon(icon, "icon icon-xs")}<span>${escapeHtml(campaign.system_label)}</span></span>`,
          "</div>",
          `<p class="card-copy">${escapeHtml(campaign.tagline)}</p>`,
          '<div class="resource-meter" aria-hidden="true">',
          "<span class=\"segment filled\"></span>".repeat(6) +
            "<span class=\"segment\"></span>".repeat(4),
          "</div>",
          '<div class="card-actions">',
          `<button class="button secondary" type="button" data-action="load-campaign" data-campaign="${escapeHtml(campaign.name)}">${renderIcon("door")}<span>进入游戏室</span></button>`,
          "</div>",
          "</article>",
        ].join("");
      })
      .join("");
  }

  function renderChat() {
    const history = Array.isArray(state.chat_history) ? state.chat_history : [];
    elements.chatSubmit.disabled = !state.chat_ready;
    elements.chatInput.disabled = !state.chat_ready;

    if (state.current_campaign) {
      elements.chatCampaign.textContent = state.current_campaign.name;
      elements.chatSystem.textContent = state.current_campaign.system_label;
    } else {
      elements.chatCampaign.textContent = "等待载入战役";
      elements.chatSystem.textContent = "SYSTEM OFFLINE";
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
        const content = escapeHtml(message.content).replace(/\n/g, "<br>");
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
      !elements.specializedSystemBlock ||
      !elements.featureModules ||
      !elements.quickActions ||
      !elements.statusTags ||
      !elements.ruleEntries
    ) {
      return;
    }

    elements.statusCampaign.textContent = state.current_campaign ? state.current_campaign.name : "未载入";
    elements.statusSystem.textContent = state.current_campaign ? state.current_campaign.system_label : "待选择";
    elements.statusReady.textContent = state.chat_ready ? "在线" : "待命";
    elements.statusMessage.textContent = state.status_message || "等待操作。";

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

    elements.featureModules.innerHTML = (systemMeta.feature_modules || [])
      .map((module) => {
        const stats = (module.stats || [])
          .map((stat) => {
            return [
              `<div class="feature-stat tone-${escapeHtml(stat.tone || "neutral")}">`,
              `<span class="feature-stat-label">${renderIcon(stat.icon || "shield", "icon icon-xs")}<span>${escapeHtml(stat.label)}</span></span>`,
              `<strong>${escapeHtml(stat.value)}</strong>`,
              "</div>",
            ].join("");
          })
          .join("");

        return [
          '<article class="feature-module-card">',
          '<div class="feature-module-head">',
          "<div>",
          `<p class="eyebrow">${escapeHtml(module.eyebrow || "专属模块")}</p>`,
          `<h4>${escapeHtml(module.title)}</h4>`,
          "</div>",
          renderIcon(module.icon || "shield"),
          "</div>",
          `<p class="card-copy">${escapeHtml(module.description)}</p>`,
          `<div class="feature-stat-list">${stats}</div>`,
          "</article>",
        ].join("");
      })
      .join("");

    elements.quickActions.innerHTML = (systemMeta.quick_actions || [])
      .map((action) => {
        return `<button class="button ${escapeHtml(action.variant || "secondary")}" type="button">${renderIcon(action.icon || "spark")}<span>${escapeHtml(action.label)}</span></button>`;
      })
      .join("");

    elements.statusTags.innerHTML = (systemMeta.status_tags || [])
      .map((tag) => {
        return `<span class="chip chip-tone-${escapeHtml(tag.tone || "neutral")}">${renderIcon(tag.icon || "spark", "icon icon-xs")}<span>${escapeHtml(tag.label)}</span></span>`;
      })
      .join("");

    elements.ruleEntries.innerHTML = (systemMeta.rule_entries || [])
      .map((rule) => {
        return [
          '<article class="rule-entry">',
          '<div class="rule-entry-head">',
          renderIcon(rule.icon || "book-open"),
          `<strong>${escapeHtml(rule.title)}</strong>`,
          "</div>",
          `<p>${escapeHtml(rule.detail)}</p>`,
          "</article>",
        ].join("");
      })
      .join("");
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

    const actions = (panel.action_steps || [])
      .map((action) => {
        return [
          '<div class="action-lane-row">',
          `<span class="feature-stat-label">${renderIcon(action.icon || "spark", "icon icon-xs")}<span>${escapeHtml(action.label)}</span></span>`,
          `<strong>${escapeHtml(action.detail)}</strong>`,
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
      `<p class="card-copy">${escapeHtml(panel.summary || "")}</p>`,
      `<div class="battle-stat-grid">${stats}</div>`,
      '<div class="resource-track-stack">',
      tracks,
      "</div>",
      '<div class="action-lane">',
      '<p class="eyebrow">行动经济</p>',
      actions,
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
    const clues = (panel.clue_chain || [])
      .map((clue) => {
        return `<span class="chip chip-tone-${escapeHtml(clue.tone || "neutral")}">${renderIcon(clue.icon || "fingerprint", "icon icon-xs")}<span>${escapeHtml(clue.label)}</span></span>`;
      })
      .join("");

    return [
      '<section class="specialized-panel specialized-panel-coc">',
      '<div class="specialized-panel-head">',
      "<div>",
      `<p class="eyebrow">${escapeHtml(panel.eyebrow || "专属组件")}</p>`,
      `<h4>${escapeHtml(panel.title || "")}</h4>`,
      "</div>",
      renderIcon("brain"),
      "</div>",
      `<p class="card-copy">${escapeHtml(panel.summary || "")}</p>`,
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
      '<div class="clue-chain">',
      '<p class="eyebrow">调查链路</p>',
      `<div class="chip-grid">${clues}</div>`,
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
    elements.apiKey.value = config.api_key || "";
    elements.baseUrl.value = config.base_url || "";
    elements.model.value = config.model || "";
  }

  function renderAll() {
    renderCampaigns();
    renderChat();
    renderStatus();
    renderConfig();
  }

  async function postJson(url, payload) {
    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });

    const data = await response.json();
    if (!response.ok || !data.ok) {
      throw new Error(data.message || "请求失败");
    }
    return data;
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
    const button = event.target.closest("[data-action='load-campaign']");
    if (!button) {
      return;
    }

    button.disabled = true;
    try {
      const data = await postJson("/api/campaigns/load", { name: button.dataset.campaign });
      mergeState(data.state);
      activateView("chat");
    } catch (error) {
      pushInlineStatus(error.message);
    } finally {
      button.disabled = false;
    }
  });

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
      pushInlineStatus("请先选择要导入的模组文件。");
      return;
    }

    try {
      pushInlineStatus("正在导入模组...");
      const formData = new FormData();
      formData.append("name", elements.importCampaignName.value.trim());
      formData.append("system", elements.importCampaignSystem.value);
      formData.append("source", source);
      const data = await postForm("/api/import-module", formData);
      mergeState(data.state);
      renderAll();
      elements.importForm.reset();
      pushInlineStatus(data.message);
    } catch (error) {
      pushInlineStatus(error.message);
    }
  });

  elements.configForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const payload = {
      api_key: elements.apiKey.value,
      base_url: elements.baseUrl.value,
      model: elements.model.value,
    };

    try {
      const data = await postJson("/api/config", payload);
      mergeState(data.state);
    } catch (error) {
      pushInlineStatus(error.message);
    }
  });

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
