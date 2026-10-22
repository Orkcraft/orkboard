// The app's worker (gui/pwa.py): the shell opens without the network, the town never does. Every file is
// asked of the town first, so a new version arrives the next time it is reachable; the cache is only for
// when it is not. The socket is never cached: what the town is comes live or not at all.
const CACHE = "orkcraft-app-v62";
// Orkboard's phone (pwa/board-app.js; docs/specs/37-board-and-line.md §4) keeps the shell's files only: no camp file
// in its cache; orkUI's styles and faces (docs/specs/40-design-system.md), its race heads as they are drawn.
const SHELL = ["./", "board-app.js", "util.js", "board.js", "shell-top.js", "shell-board.js", "shell-agents.js",
  "shell-review.js", "shell-preview.js", "shell-util.js", "shell-forms.js", "shell-goal.js", "shell-agent.js", "shell-words.js",
  "shell-needs.js", "shell-ideas.js", "shell-projects.js", "shell-drawer.js", "shell-ops.js", "shell-map.js", "shell-map-idea.js", "shell-who.js", "shell-idea-field.js", "shell-limits.js", "shell-goal-new.js", "shell-lens.js", "shell-lens-screen.js", "shell-cards.js", "shell-push.js", "shell-arena.js", "shell-arena-words.js", "shell-arena-field.js", "shell-motion.js", "shell-stops.js", "shell-today.js", "shell-fab.js", "shell-where.js", "shell-gate.js", "shell-marks.js", "shell-phases.js", "shell-goals-words.js", "shell-goals.js", "shell-decks.js", "shell-spread.js", "shell-party.js", "shell-picks.js", "shell-pick-answer.js", "shell-types.js", "fonts.css", "tokens.css", "components.css",
  "elements/meadow.svg", "elements/ice.svg", "elements/dust.svg", "elements/void.svg", "elements/lava.svg",
  "signs/check.svg", "signs/cross.svg", "signs/work.svg", "signs/night.svg", "signs/alert.svg", "signs/flag.svg", "signs/before.svg", "signs/after.svg",
  "signs/play.svg", "signs/pause.svg", "signs/sound.svg", "signs/film.svg", "signs/text.svg",
  "signs/feature.svg", "signs/bug.svg", "signs/tidy.svg", "signs/screen.svg", "signs/picture.svg", "signs/logo.svg",
  "signs/target.svg", "signs/flask.svg", "signs/horn.svg", "signs/chart.svg", "signs/page.svg",
  "icons/icons.svg", "app.css", "manifest.webmanifest", "icon-192.png", "icon-512.png", "apple-touch-icon.png",
  "fonts/ibm-plex-mono-latin-400-normal.woff2", "fonts/ibm-plex-mono-latin-600-normal.woff2", "fonts/pixelify-sans-latin-500-normal.woff2"];
const CACHE_PREFIXES = ["fonts/"];

function isCacheFirst(key) {
  return CACHE_PREFIXES.some((p) => key.startsWith(p)) || key.endsWith(".png") || key.endsWith(".webp");
}

// What the worker hands the page is never fresh to the page's own memory cache: a reloaded page asks the worker
// again (it answers from its cache, no network), so a picture the map dropped is not drawn old from memory.
function toPage(resp) {
  if (!resp.ok) return resp;
  const headers = new Headers(resp.headers);
  headers.set("Cache-Control", "no-cache");
  return new Response(resp.body, { status: resp.status, statusText: resp.statusText, headers });
}

async function updateAssets(newAssets) {
  if (!newAssets || typeof newAssets !== "object") return;
  const cache = await caches.open(CACHE);
  const oldResp = (await cache.match("assets.json")) || (await cache.match("/app/assets.json"));
  if (oldResp) {
    try {
      const oldAssets = await oldResp.json();
      for (const [path, hash] of Object.entries(newAssets)) {
        if (oldAssets[path] && oldAssets[path] !== hash) {
          await cache.delete(path);
          await cache.delete("/app/" + path);
        }
      }
      for (const path of Object.keys(oldAssets)) {
        if (!newAssets[path]) {
          await cache.delete(path);
          await cache.delete("/app/" + path);
        }
      }
    } catch {}
  }
  await cache.put("assets.json", new Response(JSON.stringify(newAssets), {
    headers: { "Content-Type": "application/json" },
  }));
}

// A new cache is filled from the town, never from the browser's HTTP cache (the PNGs and fonts are immutable
// there), and starts with the assets' map, so the next sync has one to compare against.
self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then(async (c) => {
    await Promise.all(SHELL.map(async (path) => {
      const resp = await fetch(path, { cache: "reload" });
      if (!resp.ok) throw new Error(`${path}: ${resp.status}`);
      await c.put(path, resp);
    }));
    try {
      const map = await fetch("assets.json", { cache: "reload" });
      if (map.ok) await c.put("assets.json", map);
    } catch {}
  }).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys()
    .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
    .then(() => self.clients.claim()));
});

// A pick's files (docs/specs/51-pick-one.md §3, `/media/<goal>/<pick>/<file>?s=…`) are never kept: network only. The worker does not answer for them at all, so the browser asks the town itself,
// with its Range requests (a sound or a clip seeks) and its own address's signature; a copy kept here would outlive the pick, and a signature of an earlier run is dead.
const isMedia = (address) => { try { return new URL(address, self.location.href).pathname.startsWith("/media/"); } catch { return false; } };

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (isMedia(e.request.url)) return;
  if (e.request.method !== "GET" || url.origin !== self.location.origin || !url.pathname.startsWith("/app/")) return;
  const key = url.pathname.endsWith("/") ? "./" : url.pathname.slice("/app/".length);
  if (key.startsWith("manifest")) return;             // it may carry a token (?k=): never kept

  if (isCacheFirst(key)) {
    e.respondWith(caches.open(CACHE).then(async (cache) => {
      const hit = (await cache.match(e.request)) || (await cache.match(key));
      if (hit) return toPage(hit);
      const resp = await fetch(e.request, { cache: "reload" });
      if (resp.ok) cache.put(key, resp.clone());
      return toPage(resp);
    }));
    return;
  }

  if (key === "assets.json") {
    e.respondWith(fetch(e.request).then(async (r) => {
      if (r.ok) {
        try {
          const newAssets = await r.clone().json();
          await updateAssets(newAssets);
        } catch {}
      }
      return r;
    }).catch(() => caches.open(CACHE).then((c) => c.match(key)).then((r) => r || Response.error())));
    return;
  }

  e.respondWith(fetch(e.request).then((r) => {
    if (r.ok) {
      const copy = r.clone();
      caches.open(CACHE).then((c) => c.put(key, copy));
    }
    return r;
  }).catch(() => caches.open(CACHE).then((c) => c.match(key)).then((r) => r || Response.error())));
});

self.addEventListener("message", (e) => {
  if (e.data?.type === "precache" && Array.isArray(e.data.paths)) {
    const port = e.ports?.[0];
    const paths = e.data.paths.filter((path) => typeof path === "string" && !isMedia(path));
    const p = caches.open(CACHE).then(async (c) => {
      for (let i = 0; i < paths.length; i += 20) {
        const batch = paths.slice(i, i + 20);
        await Promise.all(batch.map(async (path) => {
          try {
            const resp = await fetch(path, { cache: "reload" });
            if (resp.ok) await c.put(path, resp);
          } catch {}
        }));
        port?.postMessage({ type: "progress", loaded: Math.min(i + 20, paths.length), total: paths.length });
      }
      port?.postMessage({ type: "done", loaded: paths.length, total: paths.length });
    });
    e.waitUntil(p);
  }
});

// A push from the computer (gui/phone_push.py): it always shows a notification (a browser revokes a push that does not), and sets the
// icon's badge to the number of answers that wait.
self.addEventListener("push", (e) => {
  let d = {};
  try { d = e.data ? e.data.json() : {}; } catch {}
  const tag = d.tag || "orkline";
  const badge = typeof d.badge === "number" && self.navigator.setAppBadge ? (d.badge > 0 ? self.navigator.setAppBadge(d.badge) : self.navigator.clearAppBadge()).catch(() => {}) : null;
  e.waitUntil(Promise.all([self.registration.showNotification(d.title || "Orkline", { body: d.body || "", tag, icon: "icon-192.png", data: { url: d.url || "./", tag } }), badge]));
});

// A tap: the app's window is focused (and told which push it came from) or opened at the push's address, `#from=push-<tag>` added so the
// page logs that it was opened from a push once and takes it out of its address.
self.addEventListener("notificationclick", (e) => {
  e.notification.close();
  const { url = "./", tag = "" } = e.notification.data || {};
  const from = `from=push-${tag}`;
  const target = url.includes("#") ? `${url}&${from}` : `${url}#${from}`;
  e.waitUntil(self.clients.matchAll({ type: "window" }).then((all) => {
    if (!all[0]) return self.clients.openWindow(target);
    all[0].postMessage({ type: "push-open", tag, url });
    return all[0].focus();
  }));
});
