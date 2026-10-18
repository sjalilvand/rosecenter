// ویجت چت آنلاین هوشمند مرکز رز
(function () {
  "use strict";

  var fab = document.getElementById("chatFab");
  var panel = document.getElementById("chatPanel");
  var closeBtn = document.getElementById("chatClose");
  var body = document.getElementById("chatBody");
  var form = document.getElementById("chatForm");
  var input = document.getElementById("chatInput");
  var quick = document.getElementById("chatQuick");
  if (!fab || !panel) return;

  var sessionKey = "";
  try {
    sessionKey = localStorage.getItem("rc_chat_key");
    if (!sessionKey) {
      sessionKey = "chat-" + Math.random().toString(36).slice(2) + Date.now().toString(36);
      localStorage.setItem("rc_chat_key", sessionKey);
    }
  } catch (e) {
    sessionKey = "chat-anon";
  }

  function openPanel() {
    panel.classList.add("open");
    setTimeout(function () { input.focus(); }, 250);
  }
  function closePanel() { panel.classList.remove("open"); }

  fab.addEventListener("click", function () {
    if (panel.classList.contains("open")) closePanel(); else openPanel();
  });
  closeBtn.addEventListener("click", closePanel);
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") closePanel();
  });

  function esc(s) {
    var d = document.createElement("div");
    d.textContent = s == null ? "" : String(s);
    return d.innerHTML;
  }

  function addMsg(text, who, links) {
    var div = document.createElement("div");
    div.className = "chat-msg " + who;
    div.innerHTML = esc(text);
    if (links && links.length) {
      var wrap = document.createElement("div");
      wrap.className = "chat-links";
      links.forEach(function (l) {
        var a = document.createElement("a");
        a.href = l.url;
        a.textContent = l.label || "مشاهده";
        wrap.appendChild(a);
      });
      div.appendChild(wrap);
    }
    body.appendChild(div);
    body.scrollTop = body.scrollHeight;
  }

  function addTyping() {
    var div = document.createElement("div");
    div.className = "chat-msg bot chat-typing";
    div.id = "chatTyping";
    div.innerHTML = "<span></span><span></span><span></span>";
    body.appendChild(div);
    body.scrollTop = body.scrollHeight;
  }
  function removeTyping() {
    var t = document.getElementById("chatTyping");
    if (t) t.remove();
  }

  var busy = false;

  function ask(question) {
    if (!question || busy) return;
    busy = true;
    addMsg(question, "user");
    addTyping();
    fetch("/chat/api/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: question, session_key: sessionKey })
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        removeTyping();
        if (data && data.ok) {
          addMsg(data.answer || "پاسخی یافت نشد.", "bot", data.links || []);
          if (data.suggestions && data.suggestions.length && !data.links) {
            addMsg("ممکن است این موارد هم کمک کند:", "bot", data.suggestions);
          }
        } else {
          addMsg("متأسفانه ارتباط با سرور برقرار نشد. لطفاً دوباره تلاش کنید.", "bot");
        }
      })
      .catch(function () {
        removeTyping();
        addMsg("خطا در ارتباط با سرور. لطفاً اتصال اینترنت را بررسی کنید.", "bot");
      })
      .finally(function () { busy = false; });
  }

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    var q = input.value.trim();
    if (!q) return;
    input.value = "";
    ask(q);
  });

  if (quick) {
    quick.addEventListener("click", function (e) {
      var btn = e.target.closest("button[data-q]");
      if (btn) ask(btn.getAttribute("data-q"));
    });
  }
})();
