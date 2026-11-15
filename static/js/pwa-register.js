/* ثبت سرویس‌ورکر PWA + دکمه نصب — منتقل‌شده از uastemdad (pwa-register) */
(function () {
  "use strict";

  if ("serviceWorker" in navigator) {
    window.addEventListener("load", function () {
      navigator.serviceWorker.register("/sw.js").catch(function () { /* بی‌صدا */ });
    });
  }

  /* دکمه نصب در صفحه /app/ */
  var deferredPrompt = null;
  var btn = document.getElementById("pwaInstallBtn");

  window.addEventListener("beforeinstallprompt", function (e) {
    e.preventDefault();
    deferredPrompt = e;
    if (btn) btn.hidden = false;
  });

  if (btn) {
    btn.addEventListener("click", function () {
      if (!deferredPrompt) return;
      deferredPrompt.prompt();
      deferredPrompt.userChoice.then(function () { deferredPrompt = null; btn.hidden = true; });
    });
  }

  window.addEventListener("appinstalled", function () {
    if (btn) btn.hidden = true;
  });
})();
