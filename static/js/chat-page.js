// نسخه تمام‌صفحه چت هوشمند (صفحه /chat/)
(function () {
  "use strict";
  var body = document.getElementById("pageChatBody");
  var form = document.getElementById("pageChatForm");
  var input = document.getElementById("pageChatInput");
  var quick = document.getElementById("pageChatQuick");
  if (!body || !form) return;

  var sessionKey = "";
  try {
    sessionKey = localStorage.getItem("rc_chat_key") || ("chat-" + Date.now());
    localStorage.setItem("rc_chat_key", sessionKey);
  } catch (e) { sessionKey = "chat-anon"; }

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
    div.id = "pageChatTyping";
    div.innerHTML = "<span></span><span></span><span></span>";
    body.appendChild(div);
    body.scrollTop = body.scrollHeight;
  }
  function removeTyping() {
    var t = document.getElementById("pageChatTyping");
    if (t) t.remove();
  }
  var busy = false;
  function ask(q) {
    if (!q || busy) return;
    busy = true;
    addMsg(q, "user");
    addTyping();
    fetch("/chat/api/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: q, session_key: sessionKey })
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        removeTyping();
        if (data && data.ok) addMsg(data.answer || "پاسخی یافت نشد.", "bot", data.links || []);
        else addMsg("ارتباط با سرور برقرار نشد. دوباره تلاش کنید.", "bot");
      })
      .catch(function () {
        removeTyping();
        addMsg("خطا در ارتباط با سرور.", "bot");
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
