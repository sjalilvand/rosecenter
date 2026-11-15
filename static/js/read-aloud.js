/* خواندن متن (TTS) با صدای مرورگر — منتقل‌شده از uastemdad (read-aloud) */
(function () {
  "use strict";

  function init() {
    var bar = document.querySelector(".read-aloud-bar");
    if (!bar || !("speechSynthesis" in window)) {
      if (bar) bar.hidden = true;
      return;
    }
    var target = document.querySelector("[data-read-aloud]");
    if (!target) { bar.hidden = true; return; }

    var playBtn = bar.querySelector(".ra-play");
    var stopBtn = bar.querySelector(".ra-stop");

    function pickVoice() {
      var vs = window.speechSynthesis.getVoices() || [];
      var lang = document.documentElement.lang || "fa";
      var pref = { fa: "fa-IR", fa_IR: "fa-IR", en: "en-US", ar: "ar-SA", ru: "ru-RU", zh: "zh-CN" }[lang] || lang;
      return vs.find(function (v) { return v.lang && v.lang.toLowerCase().indexOf(pref.toLowerCase()) === 0; }) ||
             vs.find(function (v) { return v.lang && v.lang.toLowerCase().indexOf(lang.toLowerCase()) === 0; }) || null;
    }

    function speak() {
      window.speechSynthesis.cancel();
      var text = (target.innerText || "").trim().slice(0, 6000);
      if (!text) return;
      var u = new SpeechSynthesisUtterance(text);
      var v = pickVoice();
      if (v) u.voice = v;
      u.lang = (v && v.lang) || document.documentElement.lang || "fa-IR";
      u.rate = 0.95;
      u.onend = function () { bar.classList.remove("ra-playing"); };
      u.onerror = function () { bar.classList.remove("ra-playing"); };
      bar.classList.add("ra-playing");
      window.speechSynthesis.speak(u);
    }

    if (playBtn) playBtn.addEventListener("click", speak);
    if (stopBtn) stopBtn.addEventListener("click", function () {
      window.speechSynthesis.cancel();
      bar.classList.remove("ra-playing");
    });
    window.addEventListener("beforeunload", function () { window.speechSynthesis.cancel(); });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else { init(); }
})();
