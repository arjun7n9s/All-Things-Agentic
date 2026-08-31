const $ = (s, r = document) => r.querySelector(s);
const api = (p) => window.TMC.api(p);
const ran = {};

document.querySelectorAll(".tabs button").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tabs button").forEach((b) => b.classList.remove("on"));
    btn.classList.add("on");
    document.querySelectorAll(".pane").forEach((p) => p.classList.remove("on"));
    $("#" + btn.dataset.pane).classList.add("on");
    onPane(btn.dataset.pane);
  });
});

function chip(label, value, kind) {
  const el = document.createElement("span");
  el.className = "chip" + (kind ? " " + kind : "");
  el.textContent = `${label} · ${value}`;
  return el;
}

function fillChips(node, items) {
  node.innerHTML = "";
  items.forEach(([l, v, k]) => node.appendChild(chip(l, v, k)));
}

function reopenHref(path) {
  if (!path) return api("/reopen/CA-1/PM12");
  return path.startsWith("http") ? path : api(path.startsWith("/") ? path : `/${path}`);
}

async function wake(caseName) {
  const rv = await fetch(api(`/wake?case=${caseName}`));
  return rv.json();
}

function renderA(data, recorded) {
  const pm = (data.postmiles && data.postmiles[0]) || recorded || {};
  const z = pm.z_delta != null ? `+${Number(pm.z_delta).toFixed(1)} m` : "—";
  const spanLine =
    pm.route != null
      ? `${pm.route} · PM ${pm.bPM ?? pm.bpm} – PM ${pm.ePM ?? pm.epm} · CLOSED_FIRE`
      : "—";
  const firmsId = (pm.firms_ids && pm.firms_ids[0]) || (data.firms_ids && data.firms_ids[0]) || "—";
  const q = data.quotes || {};
  $("#a-firms").textContent =
    data.firms_line ||
    `acq_time = ${q.firms_acq_time || pm.quoted_firms_acq_time || "—"} · confidence = ${
      q.firms_confidence || pm.quoted_firms_confidence || "nominal"
    } · FRP = ${q.firms_frp ?? pm.quoted_firms_frp ?? "—"} · satellite = ${
      q.firms_satellite || pm.quoted_firms_satellite || "NOAA-20"
    }`;
  const matched = data.matches > 0 || pm.status === "CLOSED_FIRE";
  const cant = data.cant_read;
  $("#a-result").textContent = matched ? "MATCH" : cant ? "CAN'T READ" : "NON-MATCH";
  $("#a-result").className = "state huge " + (matched ? "" : cant ? "cant" : "non");
  $("#a-span").textContent = spanLine;
  $("#a-span").className = matched ? "state closed" : "note";
  $("#a-firms-id").textContent = `FIRMS id: ${firmsId}`;
  const url = data.reopen_url || "/reopen/CA-1/PM12";
  const a = $("#a-reopen");
  a.href = reopenHref(url);
  a.textContent = `→ POST ${url}`;
  a.target = "_blank";
  fillChips($("#a-chips"), [
    ["confidence", q.firms_confidence || pm.quoted_firms_confidence || "nominal", ""],
    [
      "intersects SHN",
      pm.route ? `${pm.route} PM${pm.bPM ?? pm.bpm}–PM${pm.ePM ?? pm.epm}` : "no",
      pm.route ? "" : "slate",
    ],
    ["z_hotspot > z_shn", z, pm.z_delta != null || pm.quoted_z_delta != null ? "" : "slate"],
    ["route on D5 SHN clip", pm.route ? "yes" : "no", pm.route ? "" : "slate"],
  ]);
  const tb = $("#a-writes");
  const wrote = data.write_happened || pm.status === "CLOSED_FIRE";
  if (wrote) {
    tb.innerHTML = `
      <tr><td>TMCAL</td><td>${pm.route || "CA-1"}</td><td>${pm.bPM ?? pm.bpm}–${pm.ePM ?? pm.epm}</td><td>status=CLOSED_FIRE</td><td>write_happened=true</td></tr>
      <tr><td>HCRR</td><td>${data.hcrr_row_id || "hcrr-…"}</td><td colspan="2">county/route/postmile/reason/time</td><td>write_happened=true</td></tr>`;
  } else {
    tb.innerHTML = `<tr><td>write_happened=false · matches=${data.matches ?? 0}</td></tr>`;
  }
}

function renderB(data) {
  $("#b-result").textContent = "NON-MATCH";
  $("#b-note").textContent = `zero closure writes · write_happened: ${!!(data && data.write_happened)}`;
  const a = $("#b-reopen");
  a.href = reopenHref("/reopen/CA-1/PM47");
  fillChips($("#b-chips"), [
    ["confidence", "nominal", ""],
    ["intersects SHN", "no", "slate"],
    ["z", "downslope", "slate"],
    ["route on D5 SHN clip", "n/a", "slate"],
  ]);
}

function renderLive(data) {
  const strip = $("#live-strip");
  const url = data.live_get_url || "https://firms.modaps.eosdis.nasa.gov/data/active_fire/noaa-20-viirs-c2/csv/J1_VIIRS_C2_USA_contiguous_and_Hawaii_24h.csv";
  const rows = data.national_csv_rows ?? data.detections ?? "—";
  const at = data.live_get_at || new Date().toISOString();
  const bytes = data.live_get_bytes != null ? ` · ${Number(data.live_get_bytes).toLocaleString()} bytes` : "";
  if (data.error) {
    strip.textContent = `GET failed: ${data.error} · zero writes`;
    $("#live-result").textContent = "CAN'T READ";
    $("#live-result").className = "state huge cant";
    $("#live-note").textContent = "Honest failure. Zero writes.";
    return;
  }
  strip.textContent = `GET ${url} · ${at} · ${Number(rows).toLocaleString()} rows${bytes}`;
  if (data.matches > 0) {
    const pm = (data.postmiles && data.postmiles[0]) || {};
    $("#live-result").textContent = "MATCH";
    $("#live-result").className = "state huge";
    $("#live-note").textContent = `${pm.route} · PM ${pm.bPM} – PM ${pm.ePM} · CLOSED_FIRE`;
    $("#live-note").className = "state closed";
    const link = $("#live-reopen");
    link.hidden = false;
    link.href = reopenHref(data.reopen_url || "/reopen/CA-1/PM12");
    link.textContent = `→ POST ${data.reopen_url || "/reopen/CA-1/PM12"}`;
    fillChips($("#live-chips"), [
      ["confidence", "nominal", ""],
      ["intersects SHN", `${pm.route} PM${pm.bPM}–PM${pm.ePM}`, ""],
      ["z_hotspot > z_shn", pm.z_delta != null ? `+${Number(pm.z_delta).toFixed(1)} m` : "yes", ""],
      ["route on D5 SHN clip", "yes", ""],
    ]);
  } else {
    $("#live-result").textContent = "NON-MATCH";
    $("#live-result").className = "state huge non";
    $("#live-note").textContent =
      "No match in this morning's 24h CSV against the D5 SHN clip. Zero writes. Sky may not cooperate at film time. Honest empty wake allowed. Do not backdate acq_time.";
    $("#live-reopen").hidden = true;
    fillChips($("#live-chips"), [
      ["confidence", "low · can't read", "slate"],
      ["intersects SHN", "no", "slate"],
      ["z", "low · can't read", "slate"],
      ["route on D5 SHN clip", "—", "slate"],
    ]);
  }
}

const UNREACHABLE = [
  ["/publish", "POST", "occupant: traveler-info", "R-OCC-5"],
  ["/traveler-info", "GET", "occupant: traveler-info board", "R-OCC-5"],
  ["/cad", "POST", "occupant: scene / hard-closure CAD", "not this desk"],
  ["/hard-closure", "POST", "occupant: field / scene desk", "not this desk"],
  ["/cones", "POST", "occupant: maintenance traffic control", "not this desk"],
  ["/blast", "POST", "occupant: road engineers", "rock assessment"],
  ["/facility-reopen", "POST", "occupant: field assessment", "not reachable"],
  ["/email", "POST", "occupant: banned channel", "no email"],
  ["/cloud-run", "GET", "occupant: host is Functions", "not .run.app"],
  ["/sigalert", "POST", "occupant: SigAlert issuance", "not in schema"],
];

function fill404() {
  const ul = $("#list-404");
  ul.innerHTML = UNREACHABLE.map(
    ([path, method, who, note]) =>
      `<li><span>${method} ${path}</span> · <span class="state">404</span> · <span class="who">${who} · ${note}</span></li>`
  ).join("");
}

async function renderConf() {
  const data = await (await fetch(api("/conformance?format=json"))).json();
  const cold = data.cold;
  $("#conf-score").textContent = cold
    ? `score · ${data.score} cold · cold start`
    : `score · ${data.score}`;
  $("#conf-score").classList.toggle("warn", !!cold);
  const box = $("#conf-chips");
  box.innerHTML = "";
  Object.entries(data.checks || {}).forEach(([k, v]) => {
    const c = chip(k, v ? "pass" : "pass · no", v ? "pass" : "bad");
    if (!v) {
      c.addEventListener("click", () => {
        let acc = c.nextElementSibling;
        if (!acc || !acc.classList.contains("accordion")) {
          acc = document.createElement("div");
          acc.className = "accordion";
          acc.textContent = `Missing object for ${k}. The live Firestore record does not yet hold this claim.`;
          c.after(acc);
        }
        acc.classList.toggle("on");
      });
    }
    box.appendChild(c);
  });
}

async function loadFrozenA() {
  if (ran.a) return;
  ran.a = true;
  try {
    const board = await (await fetch(api("/board"))).json();
    const closed = (board.postmiles || []).find((p) => p.status === "CLOSED_FIRE");
    if (closed) {
      renderA(
        {
          matches: 1,
          write_happened: true,
          postmiles: [
            {
              route: closed.route,
              bPM: closed.bpm,
              ePM: closed.epm,
              firms_ids: closed.firms_ids,
              z_delta: closed.z_delta ?? closed.quoted_z_delta,
              quoted_firms_acq_time: closed.quoted_firms_acq_time,
              quoted_firms_confidence: closed.quoted_firms_confidence,
              quoted_firms_frp: closed.quoted_firms_frp,
              quoted_firms_satellite: closed.quoted_firms_satellite,
            },
          ],
          hcrr_row_id: (board.hcrr && board.hcrr[0] && board.hcrr[0].id) || "hcrr-…",
          reopen_url: "/reopen/CA-1/PM12",
        },
        closed
      );
      return;
    }
  } catch (_) {
    /* wake below */
  }
  $("#a-result").textContent = "MATCH";
  renderA(await wake("frozen_a"));
}

async function loadFrozenB() {
  if (ran.b) return;
  ran.b = true;
  renderB(await wake("frozen_b"));
}

async function loadLive() {
  if (ran.live) return;
  ran.live = true;
  $("#live-strip").textContent =
    "GET firms.modaps.eosdis.nasa.gov/data/active_fire/noaa-20-viirs-c2/csv/J1_VIIRS_C2_USA_contiguous_and_Hawaii_24h.csv · in progress";
  try {
    renderLive(await wake("live"));
  } catch (err) {
    renderLive({ error: String(err), matches: 0 });
  }
}

function onPane(id) {
  if (id === "frozen-a") loadFrozenA();
  if (id === "frozen-b") loadFrozenB();
  if (id === "live") loadLive();
  if (id === "conformance") renderConf();
}

fill404();
fillChips($("#b-chips"), [
  ["confidence", "nominal", ""],
  ["intersects SHN", "no", "slate"],
  ["z", "downslope", "slate"],
  ["route on D5 SHN clip", "n/a", "slate"],
]);
$("#a-reopen").href = reopenHref("/reopen/CA-1/PM12");
$("#b-reopen").href = reopenHref("/reopen/CA-1/PM47");
loadFrozenA();
