/* ردیابی بازدید — منتقل‌شده از uastemdad (visit-tracker) */
(function () {
  "use strict";
  if (location.pathname.indexOf("/admin") === 0 || location.pathname.indexOf("/api") === 0) return;

  function visitorId() {
    try {
      var k = "rose_visitor_id";
      var v = localStorage.getItem(k);
      if (!v) {
        v = "v-" + Math.random().toString(36).slice(2, 10) + Date.now().toString(36);
        localStorage.setItem(k, v);
      }
      return v;
    } catch (e) { return "anonymous"; }
  }

  var payload = {
    path: location.pathname + (location.search || ""),
    title: document.title || "",
    visitorId: visitorId(),
    referrer: document.referrer || ""
  };

  try {
    var body = JSON.stringify(payload);
    if (navigator.sendBeacon) {
      navigator.sendBeacon("/api/track", new Blob([body], { type: "application/json" }));
    } else {
      fetch("/api/track", {
        method: "POST", keepalive: true,
        headers: { "Content-Type": "application/json" }, body: body
      }).catch(function () {});
    }
  } catch (e) { /* بی‌صدا */ }
})();
