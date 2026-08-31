(async function () {
  const boot = window.TMC_REOPEN_BOOT || {};
  let data = boot;
  if (!data.decision) {
    const path = location.pathname.replace(/\/$/, "");
    const idx = path.indexOf("/reopen/");
    const apiPath = idx >= 0 ? path.slice(idx) : "/reopen/CA-1/PM12";
    const rv = await fetch(window.TMC.api(apiPath) + (apiPath.includes("?") ? "&" : "?") + "format=json", {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({ actor: "fixture-tmc-lead", reason: "reopen-attempt" }),
    });
    data = await rv.json();
  }

  const dec = document.getElementById("decision");
  dec.textContent = data.decision || "—";
  dec.className = "state huge " + (data.decision === "REFUSED" ? "refused" : "allowed");

  const now = new Date().toISOString();
  document.getElementById("path-echo").textContent = `POST /reopen/${data.route || "CA-1"}/PM${data.pm || "12"} · ${now}`;

  const q = document.getElementById("quotes");
  if (data.decision === "REFUSED") {
    const span = data.quoted_shn_span || {};
    const z = data.quoted_z_delta;
    q.innerHTML = `
      <div class="quote-block">
        <p class="mono-line">Quoted FIRMS: acq_time = ${data.quoted_firms_acq_time || "—"} · confidence = ${
          data.quoted_firms_confidence || "nominal"
        } · FRP = ${data.quoted_firms_frp ?? "—"} · satellite = ${data.quoted_firms_satellite || "NOAA-20"}</p>
        <p class="cite">[R2] NOAA-20 VIIRS 24h CSV</p>
      </div>
      <div class="quote-block">
        <p class="mono-line">Quoted SHN span: ${span.county || "MON"} · ${span.route ? "CA-" + String(span.route).replace(/^CA-/, "") : data.route || "CA-1"} · bPM ${span.bPM ?? "—"} · ePM ${span.ePM ?? "—"}</p>
        <p class="cite">D5 SHN clip</p>
      </div>
      <div class="quote-block">
        <p class="mono-line">Quoted z_delta: ${z != null ? (Number(z) >= 0 ? "+" : "") + Number(z).toFixed(1) + " m" : "—"} (NASADEM)</p>
        <p class="cite">upslope conjunct</p>
      </div>`;
    document.getElementById("reason").textContent =
      data.reason === "upslope_footprint_still_intersects"
        ? `FIRMS footprint still upslope of ${data.route} PM ${data.pm}; rock assessment has not been completed.`
        : data.reason || "";
  } else {
    q.innerHTML = `<p class="note">No CLOSED_FIRE conjunct on this postmile. ALLOWED is not a county reopen.</p>`;
    document.getElementById("reason").textContent = data.reason || "no_closed_fire_conjunct";
  }

  document.getElementById("write-log").textContent = `write_happened: ${!!data.write_happened} · status: ${
    data.status || "—"
  } · reopen_log_id: ${data.reopen_log_id || "reopen-…"}`;
})();
