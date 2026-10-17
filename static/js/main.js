// وب‌سایت مرکز رز — اسکریپت تعاملی
(function () {
  "use strict";

  // ---------- سایه سربرگ هنگام اسکرول ----------
  var header = document.getElementById("siteHeader");
  var scrollTop = document.getElementById("scrollTop");
  function onScroll() {
    var y = window.scrollY || document.documentElement.scrollTop;
    if (header) header.classList.toggle("scrolled", y > 10);
    if (scrollTop) scrollTop.classList.toggle("show", y > 400);
  }
  window.addEventListener("scroll", onScroll, { passive: true });
  onScroll();

  if (scrollTop) {
    scrollTop.addEventListener("click", function () {
      window.scrollTo({ top: 0, behavior: "smooth" });
    });
  }

  // ---------- منوی موبایل ----------
  var navToggle = document.getElementById("navToggle");
  var mobileNav = document.getElementById("mobileNav");
  var overlay = document.getElementById("navOverlay");
  function closeNav() {
    if (!mobileNav || !overlay) return;
    mobileNav.classList.remove("open");
    overlay.classList.remove("show");
    setTimeout(function () {
      mobileNav.hidden = true;
      overlay.hidden = true;
    }, 300);
    document.body.style.overflow = "";
  }
  if (navToggle && mobileNav && overlay) {
    navToggle.addEventListener("click", function () {
      mobileNav.hidden = false;
      overlay.hidden = false;
      requestAnimationFrame(function () {
        mobileNav.classList.add("open");
        overlay.classList.add("show");
      });
      document.body.style.overflow = "hidden";
    });
    overlay.addEventListener("click", closeNav);
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") closeNav();
    });
  }

  // ---------- نوار جستجو ----------
  var searchToggle = document.getElementById("searchToggle");
  var searchBar = document.getElementById("searchBar");
  if (searchToggle && searchBar) {
    searchToggle.addEventListener("click", function () {
      searchBar.hidden = !searchBar.hidden;
      if (!searchBar.hidden) {
        var input = searchBar.querySelector("input");
        if (input) input.focus();
      }
    });
  }

  // ---------- فیلتر دسته سوالات متداول ----------
  var faqCats = document.querySelectorAll(".faq-cat");
  if (faqCats.length) {
    faqCats.forEach(function (btn) {
      btn.addEventListener("click", function () {
        var cat = btn.getAttribute("data-cat");
        faqCats.forEach(function (b) { b.classList.remove("active"); });
        btn.classList.add("active");
        document.querySelectorAll(".faq-item").forEach(function (item) {
          item.style.display = (cat === "all" || item.getAttribute("data-cat") === cat) ? "" : "none";
        });
      });
    });
  }
})();
