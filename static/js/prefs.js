/* ==================================================================
   شخصی‌سازی و دسترسی‌پذیری + همگام‌سازی زبان — منتقل‌شده از uastemdad
   ذخیره در localStorage (rose_prefs_v1) و کوکی rose_locale
   ================================================================== */
(function () {
  "use strict";

  var STORAGE_KEY = "rose_prefs_v1";
  var DEFAULTS = {
    font: "vazir", size: "md", bg: "default",
    theme: "rose", contrast: "normal", links: "off",
    motion: "on", lines: "normal", dark: "off"
  };

  function loadPrefs() {
    try {
      var raw = localStorage.getItem(STORAGE_KEY);
      return raw ? Object.assign({}, DEFAULTS, JSON.parse(raw)) : Object.assign({}, DEFAULTS);
    } catch (e) { return Object.assign({}, DEFAULTS); }
  }

  function savePrefs(p) {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(p)); } catch (e) { /* ignore */ }
  }

  function applyPrefs(p) {
    var el = document.documentElement;
    el.dataset.font = p.font;
    el.dataset.size = p.size;
    el.dataset.bg = p.bg;
    el.dataset.theme = p.theme;
    el.dataset.contrast = p.contrast;
    el.dataset.links = p.links;
    el.dataset.motion = p.motion;
    el.dataset.lines = p.lines;
    el.dataset.dark = p.dark;
  }

  var prefs = loadPrefs();

  // اسکریپت ضدپرش (FOUT) — باید در head اجرا شود؛ اینجا فقط اطمینان
  applyPrefs(prefs);

  /* ---------------- پنل شخصی‌سازی ---------------- */
  function bindPanel() {
    var fab = document.getElementById("prefsFab");
    var panel = document.getElementById("prefsPanel");
    if (!fab || !panel) return;

    fab.addEventListener("click", function () {
      var open = panel.classList.toggle("open");
      fab.setAttribute("aria-expanded", open ? "true" : "false");
    });
    document.addEventListener("click", function (e) {
      if (panel.classList.contains("open") && !panel.contains(e.target) && e.target !== fab && !fab.contains(e.target)) {
        panel.classList.remove("open");
      }
    });

    // دکمه‌های چیپ (فونت/اندازه/پس‌زمینه/تم)
    panel.querySelectorAll(".prefs-chip[data-group]").forEach(function (chip) {
      chip.addEventListener("click", function () {
        var group = chip.getAttribute("data-group");
        var value = chip.getAttribute("data-value");
        prefs[group] = value;
        applyPrefs(prefs);
        savePrefs(prefs);
        syncChips();
      });
    });

    // سوییچ‌ها (کنتراست/زیرخط/حرکت/سطر/شب)
    panel.querySelectorAll(".prefs-switch input[data-group]").forEach(function (sw) {
      sw.addEventListener("change", function () {
        prefs[sw.getAttribute("data-group")] = sw.checked ? (sw.getAttribute("data-on") || "on") : "off";
        applyPrefs(prefs);
        savePrefs(prefs);
      });
    });

    var reset = document.getElementById("prefsReset");
    if (reset) {
      reset.addEventListener("click", function () {
        prefs = Object.assign({}, DEFAULTS);
        applyPrefs(prefs);
        savePrefs(prefs);
        syncChips();
        syncSwitches();
      });
    }

    function syncChips() {
      panel.querySelectorAll(".prefs-chip[data-group]").forEach(function (chip) {
        chip.classList.toggle("active",
          prefs[chip.getAttribute("data-group")] === chip.getAttribute("data-value"));
      });
    }
    function syncSwitches() {
      panel.querySelectorAll(".prefs-switch input[data-group]").forEach(function (sw) {
        var on = prefs[sw.getAttribute("data-group")] === "on" ||
                 prefs[sw.getAttribute("data-group")] === "high" || false;
        sw.checked = on;
      });
    }
    syncChips();
    syncSwitches();
  }

  /* ---------------- سوییچ زبان در topbar ---------------- */
  function bindLocale() {
    var btn = document.getElementById("localeBtn");
    var menu = document.getElementById("localeMenu");
    if (!btn || !menu) return;
    btn.addEventListener("click", function (e) {
      e.stopPropagation();
      menu.classList.toggle("open");
    });
    document.addEventListener("click", function () { menu.classList.remove("open"); });

    // کلیک روی زبان‌ها: هم کوکی ست می‌شود (server-side) و هم localStorage
    menu.querySelectorAll("[data-locale]").forEach(function (item) {
      item.addEventListener("click", function (e) {
        // link href="/set-locale/xx" — ذخیره در prefs هم انجام می‌شود
        try {
          var p = loadPrefs();
          p.locale = item.getAttribute("data-locale");
          savePrefs(p);
        } catch (err) { /* ignore */ }
        // اجازه ادامه لینک
      });
    });

    // همگام‌سازی: اگر localStorage زبان متفاوتی داشت، کوکی به‌روز شود
    try {
      var p = loadPrefs();
      var cookieLocale = (document.cookie.match(/(?:^|;\s*)rose_locale=([^;]+)/) || [])[1];
      if (p.locale && cookieLocale && p.locale !== cookieLocale) {
        document.cookie = "rose_locale=" + p.locale + ";path=/;max-age=31536000;samesite=lax";
        window.location.reload();
      }
    } catch (err) { /* ignore */ }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () { bindPanel(); bindLocale(); });
  } else {
    bindPanel(); bindLocale();
  }
})();
