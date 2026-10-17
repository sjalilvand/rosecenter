/* ============================================================
   اسکریپت اصلی سایت مرکز رز
   ============================================================ */
document.addEventListener('DOMContentLoaded', function () {

  // ---------- منوی موبایل ----------
  const menuToggle = document.getElementById('menuToggle');
  const nav = document.getElementById('nav');
  if (menuToggle && nav) {
    menuToggle.addEventListener('click', function (e) {
      e.stopPropagation();
      nav.classList.toggle('open');
      menuToggle.textContent = nav.classList.contains('open') ? '×' : '☰';
    });
    document.addEventListener('click', function (e) {
      if (nav.classList.contains('open') && !nav.contains(e.target) && e.target !== menuToggle) {
        nav.classList.remove('open');
        menuToggle.textContent = '☰';
      }
    });
  }

  // ---------- زیرمنوی موبایل ----------
  document.querySelectorAll('.has-dropdown > a').forEach(function (link) {
    link.addEventListener('click', function (e) {
      if (window.innerWidth <= 768) {
        e.preventDefault();
        link.parentElement.classList.toggle('open');
      }
    });
  });

  // ---------- سایه هدر هنگام اسکرول ----------
  const header = document.getElementById('header');
  if (header) {
    window.addEventListener('scroll', function () {
      header.classList.toggle('scrolled', window.scrollY > 10);
    });
  }

  // ---------- آکاردئون سوالات متداول ----------
  document.querySelectorAll('.faq-q').forEach(function (btn) {
    btn.addEventListener('click', function () {
      const item = btn.parentElement;
      const group = item.closest('.faq-list');
      if (group) {
        group.querySelectorAll('.faq-item.open').forEach(function (other) {
          if (other !== item) other.classList.remove('open');
        });
      }
      item.classList.toggle('open');
    });
  });

  // ---------- بازگشت به بالا ----------
  const backTop = document.getElementById('backTop');
  if (backTop) {
    window.addEventListener('scroll', function () {
      backTop.classList.toggle('show', window.scrollY > 500);
    });
    backTop.addEventListener('click', function () {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
  }

  // ---------- انیمیشن ظهور تدریجی ----------
  const reveals = document.querySelectorAll('.reveal');
  if (reveals.length && 'IntersectionObserver' in window) {
    const io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
          io.unobserve(entry.target);
        }
      });
    }, { threshold: 0.12 });
    reveals.forEach(function (el) { io.observe(el); });
  } else {
    reveals.forEach(function (el) { el.classList.add('visible'); });
  }

  // ---------- بستن خودکار پیام‌ها ----------
  document.querySelectorAll('.flash').forEach(function (flash) {
    setTimeout(function () {
      flash.style.transition = 'opacity .5s';
      flash.style.opacity = '0';
      setTimeout(function () { flash.remove(); }, 500);
    }, 6000);
  });
});
