// پنل مدیریت — اسکریپت تعاملی
(function () {
  "use strict";

  // ---------- منوی کنار در موبایل ----------
  var burger = document.getElementById("adminBurger");
  var side = document.getElementById("adminSide");
  var overlay = document.getElementById("adminOverlay");
  if (burger && side && overlay) {
    burger.addEventListener("click", function () {
      side.classList.toggle("open");
      overlay.classList.toggle("show");
    });
    overlay.addEventListener("click", function () {
      side.classList.remove("open");
      overlay.classList.remove("show");
    });
  }

  // ---------- تأیید حذف ----------
  document.querySelectorAll("form[data-confirm]").forEach(function (form) {
    form.addEventListener("submit", function (e) {
      if (!window.confirm(form.getAttribute("data-confirm"))) {
        e.preventDefault();
      }
    });
  });
})();
