/** Shared desk chrome: mount prefix, clock, wall⇄sim. Zero chat. */
(function () {
  const path = location.pathname.replace(/\/+$/, "");
  const mount = path.includes("/tmc-gate")
    ? path.slice(0, path.indexOf("/tmc-gate") + "/tmc-gate".length)
    : "";
  window.TMC = {
    mount,
    api: (p) => mount + (p.startsWith("/") ? p : `/${p}`),
    clockMode: localStorage.getItem("tmc_clock") || "wall",
  };

  function pad(n) {
    return String(n).padStart(2, "0");
  }

  function fmtBudget(sec) {
    if (sec == null || sec < 0) return "10:00";
    const mm = pad(Math.floor(sec / 60));
    const ss = pad(sec % 60);
    return `${mm}:${ss}`;
  }

  function laParts(d) {
    const fmt = new Intl.DateTimeFormat("en-US", {
      timeZone: "America/Los_Angeles",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
    });
    return Object.fromEntries(fmt.formatToParts(d).map((x) => [x.type, x.value]));
  }

  function secondsToOpen(d) {
    const parts = new Intl.DateTimeFormat("en-US", {
      timeZone: "America/Los_Angeles",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
      weekday: "short",
    }).formatToParts(d);
    const get = (t) => parts.find((p) => p.type === t)?.value;
    const wd = get("weekday");
    const h = Number(get("hour"));
    const m = Number(get("minute"));
    const s = Number(get("second"));
    const nowSec = h * 3600 + m * 60 + s;
    const openSec = 6 * 3600;
    const closeSec = 18 * 3600;
    const dayLeft = 86400 - nowSec;
    const weekend = wd === "Sat" || wd === "Sun";
    if (!weekend && nowSec < openSec) return openSec - nowSec;
    if (!weekend && nowSec < closeSec) return null;
    if (wd === "Fri" && nowSec >= closeSec) return dayLeft + 2 * 86400 + openSec;
    if (wd === "Sat") return dayLeft + 86400 + openSec;
    if (wd === "Sun") return dayLeft + openSec;
    return dayLeft + openSec;
  }

  function hcrrLeft() {
    const iso = window.TMC.hcrrAt;
    if (!iso) return 600;
    const t = Date.parse(iso);
    if (Number.isNaN(t)) return 600;
    const left = 600 - Math.floor((Date.now() - t) / 1000);
    return Math.max(0, left);
  }

  function tick() {
    const el = document.getElementById("chrome-time");
    const meta = document.getElementById("chrome-meta");
    if (!el) return;
    const mode = window.TMC.clockMode;
    const budget = fmtBudget(hcrrLeft());
    if (mode === "sim") {
      el.textContent = "06:00:00";
      if (meta) meta.textContent = `TMC open in 00:00:00 · HCRR budget ${budget} left`;
      return;
    }
    const d = new Date();
    const p = laParts(d);
    el.textContent = `${p.hour}:${p.minute}:${p.second}`;
    const toOpen = secondsToOpen(d);
    let line = `America/Los_Angeles · HCRR budget ${budget} left`;
    if (toOpen != null) {
      const hh = pad(Math.floor(toOpen / 3600));
      const mm = pad(Math.floor((toOpen % 3600) / 60));
      const ss = pad(toOpen % 60);
      line = `TMC open in ${hh}:${mm}:${ss} · HCRR budget ${budget} left`;
    } else if (window.TMC.lastWakeAt) {
      line = `last_wake_at ${window.TMC.lastWakeAt} · HCRR budget ${budget} left`;
    } else {
      line = `D5 window 06:00–18:00 weekdays · HCRR budget ${budget} left`;
    }
    if (meta) meta.textContent = line;
  }

  function wireToggle() {
    document.querySelectorAll("[data-clock]").forEach((btn) => {
      btn.classList.toggle("on", btn.dataset.clock === window.TMC.clockMode);
      btn.addEventListener("click", () => {
        window.TMC.clockMode = btn.dataset.clock;
        localStorage.setItem("tmc_clock", window.TMC.clockMode);
        document.querySelectorAll("[data-clock]").forEach((b) => {
          b.classList.toggle("on", b.dataset.clock === window.TMC.clockMode);
        });
        fetch(window.TMC.api("/clock?format=json"), {
          method: "POST",
          headers: { "Content-Type": "application/json", Accept: "application/json" },
          body: JSON.stringify({ mode: window.TMC.clockMode }),
        }).catch(() => {});
        tick();
      });
    });
  }

  function markNav() {
    const here = location.pathname;
    document.querySelectorAll(".chrome-nav a").forEach((a) => {
      const href = a.getAttribute("href") || "";
      if (here.includes("/judges") && href.includes("judges")) a.classList.add("on");
      if (here.includes("/reopen") && href.includes("reopen")) a.classList.add("on");
      if (here.includes("/conformance") && href.includes("conformance")) a.classList.add("on");
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("[data-nav]").forEach((a) => {
      a.href = window.TMC.api(a.dataset.nav);
    });
    wireToggle();
    markNav();
    tick();
    setInterval(tick, 1000);
    fetch(window.TMC.api("/health?format=json"))
      .then((r) => r.json())
      .then((h) => {
        const u = h.last_unattended_wake;
        if (u && u.at) {
          window.TMC.lastWakeAt = u.at;
          window.TMC.hcrrAt = u.at;
        }
        tick();
      })
      .catch(() => {});
  });
})();
