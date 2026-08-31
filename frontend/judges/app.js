const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];

/** Function mount prefix (/tmc-gate on cloudfunctions.net, empty on *.run.app / local). */
const BASE = (() => {
  const p = location.pathname.replace(/\/+$/, "");
  const i = p.indexOf("/judges");
  return i >= 0 ? p.slice(0, i) : "";
})();
const api = (path) => BASE + (path.startsWith("/") ? path : `/${path}`);

function setOut(id, data) {
  $(id).textContent = typeof data === "string" ? data : JSON.stringify(data, null, 2);
}

$$(".steps button").forEach((btn) => {
  btn.addEventListener("click", () => {
    $$(".steps button").forEach((b) => b.classList.remove("on"));
    btn.classList.add("on");
    $$(".pane").forEach((p) => p.classList.remove("on"));
    $("#" + btn.dataset.pane).classList.add("on");
  });
});

$$("[data-wake]").forEach((btn) => {
  btn.addEventListener("click", async () => {
    const caseName = btn.dataset.wake;
    setOut("#out-" + caseName.replace("_", "-"), "running…");
    const rv = await fetch(api("/wake?case=" + caseName));
    const data = await rv.json();
    setOut("#out-" + caseName.replace("_", "-"), data);
    if (data.reopen_url) {
      reopenPath = data.reopen_url;
      const a = document.getElementById("reopen-link");
      if (a) {
        a.href = api(data.reopen_url);
        a.textContent = data.reopen_url;
        a.dataset.api = data.reopen_url;
      }
    }
    await refreshBoard();
  });
});

let reopenPath = "/reopen/CA-1/PM12";

$("#btn-reopen").addEventListener("click", async () => {
  const rv = await fetch(api(reopenPath), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ actor: "fixture-tmc-lead", reason: "reopen-attempt" }),
  });
  setOut("#out-reopen", await rv.json());
});

$$("[data-404]").forEach((btn) => {
  btn.addEventListener("click", async () => {
    const path = btn.dataset["404"];
    const rv = await fetch(api(path));
    setOut("#out-404", { path, status: rv.status, body: await rv.text() });
  });
});

$("#btn-conf").addEventListener("click", async () => {
  setOut("#out-conf", await (await fetch(api("/conformance"))).json());
});

$("#clock-mode").addEventListener("change", async () => {
  const health = await (await fetch(api("/health"))).json();
  health.ui_clock_mode = $("#clock-mode").value;
  setOut("#out-clock", health);
});

async function refreshBoard() {
  const rv = await fetch(api("/board"));
  const data = await rv.json();
  const rows = data.postmiles || [];
  const tb = $("#board");
  if (!rows.length) {
    tb.innerHTML = "<tr><td colspan='4'>empty</td></tr>";
  } else {
    const seen = new Set();
    tb.innerHTML = rows
      .filter((r) => {
        const k = r.route + r.bpm + r.epm;
        if (seen.has(k)) return false;
        seen.add(k);
        return true;
      })
      .map(
        (r) =>
          `<tr><td>${r.route}</td><td>${Number(r.bpm).toFixed(2)}–${Number(r.epm).toFixed(2)}</td><td>${r.status}</td><td>${r.z_delta ?? "—"}</td></tr>`
      )
      .join("");
  }
  const hcrr = (data.hcrr || [])[0];
  $("#hcrr").textContent = hcrr
    ? `HCRR ${hcrr.id} · ${hcrr.county} / route ${hcrr.route} / ${hcrr.postmile} · ${hcrr.time}`
    : "";
}

function tick() {
  $("#wall").textContent = new Date().toLocaleString("en-US", { timeZone: "America/Los_Angeles" }) + " PT";
}
tick();
setInterval(tick, 1000);

$$("a[data-api]").forEach((a) => {
  a.href = api(a.dataset.api);
});

fetch(api("/health")).then((r) => r.json()).then((h) => setOut("#out-clock", h));
refreshBoard();
