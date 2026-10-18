/* اسلایدر صفحه اصلی رز — autoplay + دات + فلش + سوایپ لمسی (RTL) */
(function () {
  "use strict";
  var slider = document.getElementById("heroSlider");
  if (!slider) return;

  var slides = Array.prototype.slice.call(slider.querySelectorAll(".hs-slide"));
  if (!slides.length) return;

  var dotsWrap = slider.querySelector(".hs-dots");
  var dots = [];
  var current = 0;
  var timer = null;
  var DELAY = 6000;

  // اگر تنها یک اسلاید است، همان را نمایش بده
  if (slides.length === 1) {
    slides[0].classList.add("active");
    return;
  }

  // ساخت دات‌ها
  if (dotsWrap) {
    slides.forEach(function (_, i) {
      var b = document.createElement("button");
      b.type = "button";
      b.className = "hs-dot" + (i === 0 ? " active" : "");
      b.setAttribute("aria-label", "اسلاید " + (i + 1));
      b.addEventListener("click", function () { go(i); restart(); });
      dotsWrap.appendChild(b);
      dots.push(b);
    });
  }

  function go(n) {
    slides[current].classList.remove("active");
    if (dots[current]) dots[current].classList.remove("active");
    current = (n + slides.length) % slides.length;
    slides[current].classList.add("active");
    if (dots[current]) dots[current].classList.add("active");
  }

  function next() { go(current + 1); }
  function prev() { go(current - 1); }

  function restart() {
    if (timer) clearInterval(timer);
    timer = setInterval(next, DELAY);
  }

  var btnNext = slider.querySelector(".hs-next");
  var btnPrev = slider.querySelector(".hs-prev");
  if (btnNext) btnNext.addEventListener("click", function () { next(); restart(); });
  if (btnPrev) btnPrev.addEventListener("click", function () { prev(); restart(); });

  // توقف با هاور
  slider.addEventListener("mouseenter", function () { if (timer) clearInterval(timer); });
  slider.addEventListener("mouseleave", restart);

  // سوایپ لمسی — در RTL کشیدن به راست = اسلاید بعدی
  var x0 = null;
  slider.addEventListener("touchstart", function (e) {
    x0 = e.touches[0].clientX;
  }, { passive: true });
  slider.addEventListener("touchend", function (e) {
    if (x0 === null) return;
    var dx = e.changedTouches[0].clientX - x0;
    if (Math.abs(dx) > 50) { (dx > 0 ? next() : prev()); restart(); }
    x0 = null;
  }, { passive: true });

  restart();
})();
