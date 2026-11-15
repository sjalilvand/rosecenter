/* Service Worker مرکز رز — منتقل‌شده از uastemdad
   ─────────────────────────────────────────────
   استراتژی:
   • صفحه‌ها (navigate): شبکه اول؛ در نبود شبکه نسخهٔ کش + هشدار؛ در نبود کش صفحهٔ آفلاین
   • دارایی‌های تغییرناپذیر (استاتیک/تصاویر/فونت/آپلودها): کش اول
   • مسیرهای /admin و /api هرگز کش نمی‌شوند
   افزایش VERSION کش‌های قدیمی را در فعال‌سازی حذف می‌کند. */
const VERSION = "rose-v1";
const STATIC_CACHE = VERSION + "-static";
const PAGE_CACHE = VERSION + "-pages";
const OFFLINE_URL = "/offline.html";

const PRECACHE = [
  OFFLINE_URL,
  "/manifest.webmanifest",
  "/static/img/logo.png",
  "/static/icons/icon-192.png",
  "/static/icons/icon-512.png",
  "/static/fonts/Vazirmatn-Regular.woff2",
  "/static/fonts/Vazirmatn-Bold.woff2"
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then((cache) => Promise.allSettled(PRECACHE.map((u) => cache.add(u))))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(
        keys.filter((k) => !k.startsWith(VERSION)).map((k) => caches.delete(k))
      ))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("message", (event) => {
  if (event.data === "SKIP_WAITING") self.skipWaiting();
});

function notifyStale() {
  self.clients.matchAll({ includeUncontrolled: true, type: "window" }).then((clients) => {
    for (const client of clients) client.postMessage({ type: "OFFLINE_FALLBACK" });
  });
}

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") return;

  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;
  if (url.pathname.startsWith("/admin") || url.pathname.startsWith("/api")) return;

  /* ---------------- صفحه‌ها: شبکه اول ---------------- */
  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request)
        .then((res) => {
          const copy = res.clone();
          caches.open(PAGE_CACHE).then((c) => c.put(request, copy));
          return res;
        })
        .catch(async () => {
          const hit = await caches.match(request);
          if (hit) { notifyStale(); return hit; }
          return (await caches.match(OFFLINE_URL)) || Response.error();
        })
    );
    return;
  }

  /* ---------------- دارایی‌های قابل کش ---------------- */
  const cacheable =
    url.pathname.startsWith("/static/icons") ||
    url.pathname.startsWith("/static/img") ||
    url.pathname.startsWith("/static/fonts") ||
    url.pathname.startsWith("/static/vendor") ||
    url.pathname.startsWith("/uploads") ||
    url.pathname === "/manifest.webmanifest";

  if (cacheable) {
    event.respondWith(
      caches.match(request).then(
        (hit) =>
          hit ||
          fetch(request)
            .then((res) => {
              if (res && res.ok && res.type === "basic") {
                const copy = res.clone();
                caches.open(STATIC_CACHE).then((c) => c.put(request, copy));
              }
              return res;
            })
            .catch(() => Response.error())
      )
    );
  }
});
