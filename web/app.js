(() => {
  const state = {
    lang: "ru",
    strings: {},
    games: [],
    sessions: [],
    accounts: [],
    accountFilter: "all",
    filter: "",
    toastTimer: null,
    activeKey: "",
    gamesBuilt: false,
    pendingIdle: null,
    steamWaitTimer: null,
  };

  const el = {
    brand: document.getElementById("brand"),
    tagline: document.getElementById("tagline"),
    taglineMini: document.getElementById("taglineMini"),
    langBtn: document.getElementById("langBtn"),
    libraryTitle: document.getElementById("libraryTitle"),
    sessionsTitle: document.getElementById("sessionsTitle"),
    refreshBtn: document.getElementById("refreshBtn"),
    stopAllBtn: document.getElementById("stopAllBtn"),
    searchInput: document.getElementById("searchInput"),
    accountRow: document.getElementById("accountRow"),
    accountLabel: document.getElementById("accountLabel"),
    accountFilter: document.getElementById("accountFilter"),
    hintMulti: document.getElementById("hintMulti"),
    gameList: document.getElementById("gameList"),
    sessionList: document.getElementById("sessionList"),
    libraryEmpty: document.getElementById("libraryEmpty"),
    sessionsEmpty: document.getElementById("sessionsEmpty"),
    toast: document.getElementById("toast"),
    gamesCount: document.getElementById("gamesCount"),
    gamesCountLabel: document.getElementById("gamesCountLabel"),
    sessionCount: document.getElementById("sessionCount"),
    sessionCountLabel: document.getElementById("sessionCountLabel"),
    titlebar: document.getElementById("titlebar"),
    minBtn: document.getElementById("minBtn"),
    maxBtn: document.getElementById("maxBtn"),
    closeBtn: document.getElementById("closeBtn"),
    steamModal: document.getElementById("steamModal"),
    steamModalTitle: document.getElementById("steamModalTitle"),
    steamModalBody: document.getElementById("steamModalBody"),
    steamModalPath: document.getElementById("steamModalPath"),
    steamModalCancel: document.getElementById("steamModalCancel"),
    steamModalLaunch: document.getElementById("steamModalLaunch"),
    confirmModal: document.getElementById("confirmModal"),
    confirmModalTitle: document.getElementById("confirmModalTitle"),
    confirmModalBody: document.getElementById("confirmModalBody"),
    confirmModalCancel: document.getElementById("confirmModalCancel"),
    confirmModalOk: document.getElementById("confirmModalOk"),
    splash: document.getElementById("splash"),
    splashBrand: document.getElementById("splashBrand"),
    splashSub: document.getElementById("splashSub"),
    splashStatus: document.getElementById("splashStatus"),
    splashBarFill: document.getElementById("splashBarFill"),
    splashQuote: document.getElementById("splashQuote"),
    fxLayer: document.getElementById("fxLayer"),
    achToast: document.getElementById("achToast"),
    achToastLabel: document.getElementById("achToastLabel"),
    achToastTitle: document.getElementById("achToastTitle"),
    achToastDesc: document.getElementById("achToastDesc"),
  };

  const splashStartedAt = performance.now();
  const SPLASH_MIN_MS = 1800;
  const STORE_KEY = "pirat_wow_v1";
  const QUOTES = {
    ru: [
      "Ветер в паруса — часы в рост.",
      "Тихая гавань для громких цифр.",
      "Пират не ждёт — пират накручивает.",
      "Сегодня штиль, завтра — рекорд.",
      "Карта сокровищ? Нет, карта AppID.",
      "Один клик — и курс на часы.",
    ],
    en: [
      "Wind in the sails, hours on the rise.",
      "Quiet harbor for loud playtime.",
      "A pirate doesn’t wait — a pirate boosts.",
      "Calm seas today, records tomorrow.",
      "Not a treasure map — an AppID map.",
      "One click, and set course for hours.",
    ],
  };

  let wow = loadWow();
  let achQueue = [];
  let achBusy = false;
  let achTimer = null;

  function todayKey() {
    const d = new Date();
    return `${d.getFullYear()}-${d.getMonth() + 1}-${d.getDate()}`;
  }

  function loadWow() {
    try {
      const raw = localStorage.getItem(STORE_KEY);
      if (!raw) {
        return { unlocked: {}, starts: 0, lastDay: "", hourglass: false };
      }
      const data = JSON.parse(raw);
      return {
        unlocked: data.unlocked || {},
        starts: Number(data.starts) || 0,
        lastDay: data.lastDay || "",
        hourglass: !!data.hourglass,
      };
    } catch (_) {
      return { unlocked: {}, starts: 0, lastDay: "", hourglass: false };
    }
  }

  function saveWow() {
    try {
      localStorage.setItem(STORE_KEY, JSON.stringify(wow));
    } catch (_) {
      /* ignore */
    }
  }

  function pickQuote(lang) {
    const list = QUOTES[lang] || QUOTES.ru;
    return list[Math.floor(Math.random() * list.length)];
  }

  function setSplashQuote() {
    if (!el.splashQuote) return;
    el.splashQuote.textContent = `«${pickQuote(state.lang || "ru")}»`;
  }

  function burstStartFx(big = false) {
    if (!el.fxLayer) return;
    const flash = document.createElement("div");
    flash.className = "fx-flash";
    el.fxLayer.appendChild(flash);
    window.setTimeout(() => flash.remove(), 900);

    const colors = ["#E8A838", "#F2C46A", "#2BB7A8", "#EEF3FB", "#E36A5D"];
    const count = big ? 28 : 16;
    for (let i = 0; i < count; i += 1) {
      const spark = document.createElement("span");
      spark.className = "fx-spark";
      const angle = (Math.PI * 2 * i) / count + Math.random() * 0.35;
      const dist = 70 + Math.random() * (big ? 160 : 110);
      spark.style.setProperty("--dx", `${Math.cos(angle) * dist}px`);
      spark.style.setProperty("--dy", `${Math.sin(angle) * dist}px`);
      spark.style.background = colors[i % colors.length];
      spark.style.animationDelay = `${Math.random() * 0.08}s`;
      el.fxLayer.appendChild(spark);
      window.setTimeout(() => spark.remove(), 1200);
    }
  }

  function showAchievement(id) {
    achQueue.push(id);
    drainAchievements();
  }

  function drainAchievements() {
    if (achBusy || !achQueue.length || !el.achToast) return;
    achBusy = true;
    const id = achQueue.shift();
    el.achToastLabel.textContent = t("ach_unlocked");
    el.achToastTitle.textContent = t(`ach_${id}`);
    el.achToastDesc.textContent = t(`ach_${id}_desc`);
    el.achToast.hidden = false;
    el.achToast.classList.remove("is-out");
    clearTimeout(achTimer);
    achTimer = window.setTimeout(() => {
      el.achToast.classList.add("is-out");
      window.setTimeout(() => {
        el.achToast.hidden = true;
        el.achToast.classList.remove("is-out");
        achBusy = false;
        drainAchievements();
      }, 320);
    }, 3200);
  }

  function unlockAchievement(id) {
    if (wow.unlocked[id]) return false;
    wow.unlocked[id] = Date.now();
    saveWow();
    showAchievement(id);
    return true;
  }

  function evaluateStartAchievements(sessionCount) {
    const day = todayKey();
    const firstEver = wow.starts === 0;
    const firstToday = wow.lastDay !== day;
    wow.starts += 1;
    wow.lastDay = day;
    saveWow();

    if (firstEver) unlockAchievement("first_sail");
    if (firstToday) unlockAchievement("dawn_raid");
    if (sessionCount >= 2) unlockAchievement("double");
    if (sessionCount >= 5) unlockAchievement("fleet");
    if (wow.starts >= 10) unlockAchievement("treasure");
  }

  function evaluateHourglass(sessions) {
    if (wow.hourglass) return;
    if ((sessions || []).some((s) => Number(s.elapsed) >= 3600)) {
      wow.hourglass = true;
      saveWow();
      unlockAchievement("hourglass");
    }
  }

  setSplashQuote();

  function setSplashProgress(percent, statusText) {
    if (el.splashBarFill) {
      el.splashBarFill.style.width = `${Math.max(6, Math.min(100, percent))}%`;
    }
    if (el.splashStatus && statusText) {
      el.splashStatus.textContent = statusText;
    }
  }

  function hideSplash() {
    document.body.classList.remove("is-booting");
    if (!el.splash) return;
    el.splash.classList.add("is-done");
    el.splash.setAttribute("aria-hidden", "true");
    window.setTimeout(() => {
      if (el.splash && el.splash.parentNode) el.splash.remove();
    }, 700);
  }

  async function finishSplash() {
    const elapsed = performance.now() - splashStartedAt;
    const wait = Math.max(0, SPLASH_MIN_MS - elapsed);
    if (wait) await new Promise((resolve) => setTimeout(resolve, wait));
    setSplashProgress(100, t("splash_ready") || "Готово");
    await new Promise((resolve) => setTimeout(resolve, 220));
    hideSplash();
  }

  function t(key) {
    return state.strings[key] || key;
  }

  function showToast(message) {
    el.toast.hidden = false;
    el.toast.textContent = message;
    clearTimeout(state.toastTimer);
    state.toastTimer = setTimeout(() => {
      el.toast.hidden = true;
    }, 2800);
  }

  function formatElapsed(seconds) {
    const total = Math.max(0, Math.floor(seconds));
    const h = Math.floor(total / 3600);
    const m = Math.floor((total % 3600) / 60);
    const s = total % 60;
    const parts = [];
    if (h > 0) parts.push(`${h}${t("hours_short")}`);
    parts.push(`${m}${t("minutes_short")}`);
    parts.push(`${String(s).padStart(2, "0")}${t("seconds_short")}`);
    return parts.join(" ");
  }

  function sessionsKey(sessions) {
    return sessions
      .map((s) => s.app_id)
      .slice()
      .sort((a, b) => a - b)
      .join(",");
  }

  function activeIds() {
    return new Set(state.sessions.map((s) => s.app_id));
  }

  function filteredGames() {
    const q = state.filter.trim().toLowerCase();
    let games = state.games;
    if (state.accountFilter && state.accountFilter !== "all") {
      const accountId = Number(state.accountFilter);
      games = games.filter((g) =>
        (g.owners || []).some((owner) => Number(owner.id) === accountId)
      );
    }
    if (!q) return games;
    return games.filter(
      (g) =>
        g.name.toLowerCase().includes(q) ||
        String(g.app_id).includes(q) ||
        (g.owners || []).some((owner) =>
          String(owner.name || "").toLowerCase().includes(q)
        )
    );
  }

  function renderAccountFilter() {
    if (!el.accountFilter || !el.accountRow) return;
    const accounts = state.accounts || [];
    el.accountRow.hidden = accounts.length < 2;
    if (el.accountLabel) el.accountLabel.textContent = t("account_label");

    const previous = state.accountFilter || "all";
    el.accountFilter.innerHTML = "";
    const allOpt = document.createElement("option");
    allOpt.value = "all";
    allOpt.textContent = t("account_filter_all");
    el.accountFilter.appendChild(allOpt);

    for (const account of accounts) {
      const opt = document.createElement("option");
      opt.value = String(account.id);
      const mark = account.active ? ` (${t("account_active")})` : "";
      opt.textContent = `${account.name}${mark}`;
      el.accountFilter.appendChild(opt);
    }

    const stillValid =
      previous === "all" || accounts.some((a) => String(a.id) === previous);
    state.accountFilter = stillValid ? previous : "all";
    el.accountFilter.value = state.accountFilter;
  }

  function ownerTagsHtml(owners) {
    const list = owners || [];
    if (!list.length) {
      return `<div class="owner-tags"><span class="owner-tag is-unknown">${t(
        "account_unknown"
      )}</span></div>`;
    }
    return `<div class="owner-tags">${list
      .map((owner) => {
        const cls = owner.active ? "owner-tag is-active" : "owner-tag";
        const name = String(owner.name || "").replace(/[<>&"]/g, "");
        return `<span class="${cls}" title="${name}">${name}</span>`;
      })
      .join("")}</div>`;
  }

  function updateStats() {
    if (el.gamesCount) el.gamesCount.textContent = String(state.games.length);
    if (el.sessionCount) el.sessionCount.textContent = String(state.sessions.length);
  }

  function applyStrings() {
    el.brand.textContent = t("app_title");
    el.tagline.textContent = t("tagline");
    if (el.taglineMini) el.taglineMini.textContent = t("titlebar_sub");
    el.langBtn.textContent = t("lang");
    el.libraryTitle.textContent = t("library");
    el.sessionsTitle.textContent = t("sessions");
    el.refreshBtn.textContent = t("refresh");
    el.stopAllBtn.textContent = t("stop_all");
    el.searchInput.placeholder = t("search_placeholder");
    el.hintMulti.textContent = t("hint_multi");
    if (el.gamesCountLabel) el.gamesCountLabel.textContent = t("games_label");
    if (el.sessionCountLabel) el.sessionCountLabel.textContent = t("sessions_label");
    if (el.steamModal && !el.steamModal.hidden) {
      syncSteamModalStrings(el.steamModal.dataset.mode || "required");
    }
    renderAccountFilter();
    renderGames(true);
    renderSessions(true);
    updateStats();
  }

  function coverUrls(appId, preferred) {
    const id = String(appId);
    const urls = [];
    if (preferred) urls.push(preferred);
    urls.push(
      `https://cdn.cloudflare.steamstatic.com/steam/apps/${id}/library_600x900.jpg`,
      `https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/${id}/library_600x900.jpg`,
      `https://cdn.cloudflare.steamstatic.com/steam/apps/${id}/header.jpg`,
      `https://cdn.cloudflare.steamstatic.com/steam/apps/${id}/capsule_184x69.jpg`
    );
    return [...new Set(urls)];
  }

  function bindCover(img, appId, preferred) {
    const urls = coverUrls(appId, preferred);
    let index = 0;
    img.loading = "lazy";
    img.decoding = "async";
    img.alt = "";
    img.src = urls[0];
    img.onerror = () => {
      index += 1;
      if (index < urls.length) {
        img.src = urls[index];
        return;
      }
      img.classList.add("is-missing");
      img.removeAttribute("src");
      img.onerror = null;
    };
  }

  function updateGameActiveStates() {
    const running = activeIds();
    el.gameList.querySelectorAll(".game-row").forEach((row) => {
      const appId = Number(row.dataset.appId);
      const active = running.has(appId);
      row.classList.toggle("is-active", active);
      const btn = row.querySelector("button");
      if (btn) {
        btn.disabled = active;
        btn.textContent = t("start");
      }
    });
  }

  function renderGames(force = false) {
    const games = filteredGames();
    const signature = games.map((g) => `${g.app_id}:${g.name}`).join("|") + `|f:${state.filter}`;
    if (!force && state.gamesBuilt && state._gamesSig === signature) {
      updateGameActiveStates();
      return;
    }
    state._gamesSig = signature;
    state.gamesBuilt = true;

    const running = activeIds();
    el.gameList.innerHTML = "";

    if (!games.length) {
      el.libraryEmpty.hidden = false;
      el.libraryEmpty.textContent = t("no_games");
      return;
    }
    el.libraryEmpty.hidden = true;

    const frag = document.createDocumentFragment();
    for (const game of games) {
      const row = document.createElement("div");
      row.className = "game-row" + (running.has(game.app_id) ? " is-active" : "");
      row.dataset.appId = String(game.app_id);
      row.innerHTML = `
        <img class="cover" alt="" />
        <div class="game-meta">
          <p class="game-name"></p>
          <p class="game-id"></p>
          <div class="owner-tags"></div>
        </div>
        <button type="button" class="primary-btn small"></button>
      `;
      bindCover(row.querySelector(".cover"), game.app_id, game.cover);
      row.querySelector(".game-name").textContent = game.name;
      const status = game.installed ? t("installed") : t("not_installed");
      row.querySelector(".game-id").textContent = `AppID ${game.app_id} · ${status}`;
      const ownersHost = row.querySelector(".owner-tags");
      ownersHost.outerHTML = ownerTagsHtml(game.owners);
      const btn = row.querySelector("button");
      btn.textContent = t("start");
      btn.disabled = running.has(game.app_id);
      btn.addEventListener("click", () => startIdle(game.app_id, game.name));
      frag.appendChild(row);
    }
    el.gameList.appendChild(frag);
    updateStats();
  }

  function updateSessionTimers() {
    for (const session of state.sessions) {
      const timer = el.sessionList.querySelector(
        `.session-row[data-app-id="${session.app_id}"] .timer`
      );
      if (timer) timer.textContent = formatElapsed(session.elapsed);
    }
    evaluateHourglass(state.sessions);
  }

  function renderSessions(force = false) {
    const key = sessionsKey(state.sessions);
    if (!force && key === state.activeKey && el.sessionList.children.length === state.sessions.length) {
      updateSessionTimers();
      return;
    }
    state.activeKey = key;

    el.sessionList.innerHTML = "";
    if (!state.sessions.length) {
      el.sessionsEmpty.hidden = false;
      el.sessionsEmpty.textContent = t("no_sessions");
      updateGameActiveStates();
      updateStats();
      return;
    }
    el.sessionsEmpty.hidden = true;
    const frag = document.createDocumentFragment();
    for (const session of state.sessions) {
      const row = document.createElement("div");
      row.className = "session-row";
      row.dataset.appId = String(session.app_id);
      row.innerHTML = `
        <img class="cover cover-sm" alt="" />
        <div class="session-meta">
          <p class="session-name"></p>
          <p class="session-sub"><span class="badge"></span> · AppID <span class="aid"></span></p>
        </div>
        <div class="timer"></div>
        <button type="button" class="ghost-btn danger"></button>
      `;
      bindCover(row.querySelector(".cover"), session.app_id, session.cover);
      row.querySelector(".session-name").textContent = session.name;
      row.querySelector(".badge").textContent = t("status_idle");
      row.querySelector(".aid").textContent = String(session.app_id);
      row.querySelector(".timer").textContent = formatElapsed(session.elapsed);
      const btn = row.querySelector("button");
      btn.textContent = t("stop");
      btn.addEventListener("click", () => stopIdle(session.app_id));
      frag.appendChild(row);
    }
    el.sessionList.appendChild(frag);
    updateGameActiveStates();
    updateStats();
  }

  async function call(method, ...args) {
    if (!window.pywebview || !window.pywebview.api) {
      throw new Error("API unavailable");
    }
    return window.pywebview.api[method](...args);
  }

  async function bootstrap() {
    setSplashProgress(18, "Загрузка…");
    const ready = await call("ready");
    state.lang = ready.lang;
    state.strings = ready.strings;
    if (el.splashBrand) el.splashBrand.textContent = t("app_title");
    if (el.splashSub) el.splashSub.textContent = t("titlebar_sub");
    setSplashQuote();
    setSplashProgress(42, t("splash_loading"));
    applyStrings();
    setSplashProgress(62, t("splash_library"));
    await refreshLibrary();
    setSplashProgress(84, t("splash_loading"));
    await refreshSessions(true);
    await syncMaximizeState();
    evaluateHourglass(state.sessions);
    setInterval(() => refreshSessions(false), 1000);
    await finishSplash();
  }

  async function refreshLibrary() {
    const data = await call("refresh_library");
    state.games = data.games || [];
    state.accounts = data.accounts || [];
    renderAccountFilter();
    renderGames(true);
    if (!state.games.length) {
      el.libraryEmpty.hidden = false;
      el.libraryEmpty.textContent = t("steam_missing");
    }
  }

  async function refreshSessions(force = false) {
    try {
      const data = await call("get_sessions");
      const next = data.sessions || [];
      const prevKey = state.activeKey;
      state.sessions = next;
      const nextKey = sessionsKey(next);
      if (force || nextKey !== prevKey) {
        renderSessions(true);
      } else {
        updateSessionTimers();
      }
    } catch (_) {
      /* ignore transient */
    }
  }

  async function startIdle(appId, name) {
    const result = await call("start_idle", appId, name);
    if (!result.ok) {
      if (result.error === "steam_required") {
        openSteamModal({
          appId,
          name,
          steamPath: result.steam_path || "",
          canLaunch: !!result.can_launch,
        });
        return;
      }
      const map = {
        already_running: t("already_running"),
        failed_start: t("failed_start"),
      };
      showToast(map[result.error] || t("failed_start"));
      return;
    }
    state.sessions = result.sessions || [];
    renderSessions(true);
    const count = state.sessions.length;
    const dayFirst = wow.lastDay !== todayKey();
    burstStartFx(dayFirst || count >= 5);
    evaluateStartAchievements(count);
    showToast(t("started"));
  }

  function syncSteamModalStrings(mode) {
    if (!el.steamModalTitle) return;
    el.steamModal.dataset.mode = mode;
    el.steamModalTitle.textContent = t("steam_modal_title");
    el.steamModalBody.textContent =
      mode === "missing" ? t("steam_modal_missing") : t("steam_modal_body");
    el.steamModalCancel.textContent = t("steam_modal_cancel");
    if (!el.steamModalLaunch.disabled) {
      el.steamModalLaunch.textContent = t("steam_modal_launch");
    }
  }

  function openSteamModal(payload) {
    state.pendingIdle = {
      appId: payload.appId,
      name: payload.name,
    };
    const canLaunch = !!payload.canLaunch;
    const mode = canLaunch ? "required" : "missing";
    syncSteamModalStrings(mode);

    if (payload.steamPath) {
      el.steamModalPath.hidden = false;
      el.steamModalPath.textContent = payload.steamPath;
    } else {
      el.steamModalPath.hidden = true;
      el.steamModalPath.textContent = "";
    }

    el.steamModalLaunch.hidden = !canLaunch;
    el.steamModalLaunch.disabled = false;
    el.steamModalLaunch.textContent = t("steam_modal_launch");
    el.steamModalCancel.disabled = false;
    el.steamModal.hidden = false;
  }

  function closeSteamModal(clearPending = true) {
    if (state.steamWaitTimer) {
      clearInterval(state.steamWaitTimer);
      state.steamWaitTimer = null;
    }
    if (clearPending) state.pendingIdle = null;
    if (!el.steamModal) return;
    el.steamModal.hidden = true;
    el.steamModalLaunch.disabled = false;
    el.steamModalCancel.disabled = false;
  }

  async function waitForSteam(timeoutMs = 90000) {
    const started = Date.now();
    while (Date.now() - started < timeoutMs) {
      const status = await call("steam_status");
      if (status && status.steam_running) return true;
      await new Promise((resolve) => setTimeout(resolve, 1200));
    }
    return false;
  }

  async function launchSteamAndRetry() {
    el.steamModalLaunch.disabled = true;
    el.steamModalCancel.disabled = true;
    el.steamModalLaunch.textContent = t("steam_modal_wait");

    const launched = await call("launch_steam");
    if (!launched || !launched.ok) {
      el.steamModalLaunch.disabled = false;
      el.steamModalCancel.disabled = false;
      el.steamModalLaunch.textContent = t("steam_modal_launch");
      if (launched && launched.error === "steam_missing") {
        syncSteamModalStrings("missing");
        el.steamModalLaunch.hidden = true;
      } else {
        showToast(t("steam_launch_failed"));
      }
      return;
    }

    if (launched.steam_path) {
      el.steamModalPath.hidden = false;
      el.steamModalPath.textContent = launched.steam_path;
    }

    const ready = launched.steam_running || (await waitForSteam());
    if (!ready) {
      el.steamModalLaunch.disabled = false;
      el.steamModalCancel.disabled = false;
      el.steamModalLaunch.textContent = t("steam_modal_launch");
      showToast(t("steam_required"));
      return;
    }

    const pending = state.pendingIdle;
    closeSteamModal(true);
    showToast(t("steam_ready"));
    if (pending) {
      await startIdle(pending.appId, pending.name);
    }
  }

  async function stopIdle(appId) {
    const result = await call("stop_idle", appId);
    state.sessions = result.sessions || [];
    renderSessions(true);
    showToast(t("stopped"));
  }

  el.langBtn.addEventListener("click", async () => {
    const next = state.lang === "ru" ? "en" : "ru";
    const data = await call("set_language", next);
    state.lang = data.lang;
    state.strings = data.strings;
    applyStrings();
    setSplashQuote();
  });

  if (el.steamModalCancel) {
    el.steamModalCancel.addEventListener("click", () => closeSteamModal(true));
  }
  if (el.steamModalLaunch) {
    el.steamModalLaunch.addEventListener("click", () => launchSteamAndRetry());
  }
  if (el.steamModal) {
    el.steamModal.addEventListener("click", (event) => {
      if (event.target === el.steamModal && !el.steamModalLaunch.disabled) {
        closeSteamModal(true);
      }
    });
  }

  function bindSpotlight(listEl) {
    if (!listEl) return;
    listEl.addEventListener("pointermove", (event) => {
      const row = event.target.closest(".game-row, .session-row");
      if (!row || !listEl.contains(row)) return;
      const rect = row.getBoundingClientRect();
      const x = ((event.clientX - rect.left) / Math.max(rect.width, 1)) * 100;
      const y = ((event.clientY - rect.top) / Math.max(rect.height, 1)) * 100;
      row.style.setProperty("--spot-x", `${x.toFixed(1)}%`);
      row.style.setProperty("--spot-y", `${y.toFixed(1)}%`);
    });
  }

  bindSpotlight(el.gameList);
  bindSpotlight(el.sessionList);

  el.refreshBtn.addEventListener("click", () => refreshLibrary());
  el.searchInput.addEventListener("input", () => {
    state.filter = el.searchInput.value;
    renderGames(true);
  });
  if (el.accountFilter) {
    el.accountFilter.addEventListener("change", () => {
      state.accountFilter = el.accountFilter.value || "all";
      renderGames(true);
    });
  }

  el.stopAllBtn.addEventListener("click", async () => {
    if (!state.sessions.length) return;
    const confirmed = await askConfirm({
      title: t("confirm_title"),
      body: t("confirm_stop_all"),
      ok: t("confirm_ok"),
      cancel: t("confirm_cancel"),
    });
    if (!confirmed) return;
    const result = await call("stop_all");
    state.sessions = result.sessions || [];
    renderSessions(true);
    showToast(t("stopped"));
  });

  function askConfirm({ title, body, ok, cancel }) {
    return new Promise((resolve) => {
      if (!el.confirmModal) {
        resolve(window.confirm(body));
        return;
      }

      el.confirmModalTitle.textContent = title || t("confirm_title");
      el.confirmModalBody.textContent = body || "";
      el.confirmModalOk.textContent = ok || t("confirm_ok");
      el.confirmModalCancel.textContent = cancel || t("confirm_cancel");
      el.confirmModal.hidden = false;

      const finish = (value) => {
        el.confirmModal.hidden = true;
        el.confirmModalOk.removeEventListener("click", onOk);
        el.confirmModalCancel.removeEventListener("click", onCancel);
        el.confirmModal.removeEventListener("click", onBackdrop);
        document.removeEventListener("keydown", onKey);
        resolve(value);
      };
      const onOk = () => finish(true);
      const onCancel = () => finish(false);
      const onBackdrop = (event) => {
        if (event.target === el.confirmModal) finish(false);
      };
      const onKey = (event) => {
        if (event.key === "Escape") finish(false);
        if (event.key === "Enter") finish(true);
      };

      el.confirmModalOk.addEventListener("click", onOk);
      el.confirmModalCancel.addEventListener("click", onCancel);
      el.confirmModal.addEventListener("click", onBackdrop);
      document.addEventListener("keydown", onKey);
      el.confirmModalOk.focus();
    });
  }

  function setMaximizeVisual(maximized) {
    if (!el.maxBtn) return;
    el.maxBtn.classList.toggle("is-max", !!maximized);
    const restore = el.maxBtn.querySelector(".icon-restore");
    const maxIcon = el.maxBtn.querySelector(".icon-max");
    if (restore) restore.hidden = !maximized;
    if (maxIcon) maxIcon.hidden = !!maximized;
    el.maxBtn.title = maximized ? "Restore" : "Maximize";
    el.maxBtn.setAttribute("aria-label", maximized ? "Restore" : "Maximize");
  }

  el.minBtn.addEventListener("click", async (event) => {
    event.preventDefault();
    event.stopPropagation();
    await call("window_minimize");
  });
  el.maxBtn.addEventListener("click", async (event) => {
    event.preventDefault();
    event.stopPropagation();
    const result = await call("window_toggle_maximize");
    if (result && result.ok) setMaximizeVisual(result.maximized);
  });
  el.closeBtn.addEventListener("click", async (event) => {
    event.preventDefault();
    event.stopPropagation();
    await call("window_close");
  });
  el.titlebar.addEventListener("dblclick", async (event) => {
    if (event.target.closest(".win-btn, .lang-btn, .no-drag")) return;
    const result = await call("window_toggle_maximize");
    if (result && result.ok) setMaximizeVisual(result.maximized);
  });

  async function syncMaximizeState() {
    try {
      const state = await call("window_is_maximized");
      if (state && state.ok) setMaximizeVisual(state.maximized);
    } catch (_) {
      /* ignore */
    }
  }

  // Custom edge resize (no OS frame = no gray/white top strip).
  (() => {
    const minW = 780;
    const minH = 560;
    let drag = null;
    let pending = null;

    async function applyBounds(next) {
      pending = next;
      if (applyBounds._busy) return;
      applyBounds._busy = true;
      while (pending) {
        const job = pending;
        pending = null;
        try {
          await call("window_set_bounds", job.x, job.y, job.width, job.height);
        } catch (_) {
          /* ignore */
        }
      }
      applyBounds._busy = false;
    }

    document.querySelectorAll(".resize-handle").forEach((handle) => {
      handle.addEventListener("mousedown", async (event) => {
        event.preventDefault();
        event.stopPropagation();
        const bounds = await call("window_get_bounds");
        if (!bounds || !bounds.ok) return;
        drag = {
          edge: handle.dataset.edge,
          startX: event.screenX,
          startY: event.screenY,
          x: bounds.x,
          y: bounds.y,
          width: bounds.width,
          height: bounds.height,
        };
      });
    });

    window.addEventListener("mousemove", (event) => {
      if (!drag) return;
      const dx = event.screenX - drag.startX;
      const dy = event.screenY - drag.startY;
      let { x, y, width, height } = drag;
      const edge = drag.edge;

      if (edge.includes("e")) width = drag.width + dx;
      if (edge.includes("s")) height = drag.height + dy;
      if (edge.includes("w")) {
        width = drag.width - dx;
        x = drag.x + dx;
        if (width < minW) {
          x = drag.x + (drag.width - minW);
          width = minW;
        }
      }
      if (edge.includes("n")) {
        height = drag.height - dy;
        y = drag.y + dy;
        if (height < minH) {
          y = drag.y + (drag.height - minH);
          height = minH;
        }
      }

      width = Math.max(minW, width);
      height = Math.max(minH, height);
      applyBounds({ x, y, width, height });
    });

    window.addEventListener("mouseup", () => {
      drag = null;
    });
  })();

  window.addEventListener("pywebviewready", bootstrap);
  if (window.pywebview && window.pywebview.api) {
    bootstrap();
  }
})();
