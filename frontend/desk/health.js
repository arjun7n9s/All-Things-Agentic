const LETTERS = [
  ["A1", "earth_engine", "Earth Engine"],
  ["A2", "bigquery", "BigQuery"],
  ["A3", "pubsub", "Pub/Sub"],
  ["A4", "model_armor", "Model Armor"],
  ["A5", "cloud_functions", "Cloud Functions"],
  ["A6", "firestore", "Firestore"],
  ["A7", "secret_manager", "Secret Manager"],
  ["A8", "cloud_storage", "Cloud Storage"],
];

function paint(h) {
  const box = document.getElementById("letters");
  const checked = h.checked_at || new Date().toISOString();
  const svc = h.services || {};
  const fromLetters = {};
  (h.letters || []).forEach((row) => {
    fromLetters[row.key] = row;
  });
  box.innerHTML = LETTERS.map(([ltr, key, name]) => {
    const row = fromLetters[key];
    const st = (row && row.status) || svc[key] || "not-configured";
    const when = (row && row.last_checked_iso) || checked;
    const failed = st === "failed";
    return `<div class="letter-row${failed ? " failed" : ""}"><span class="ltr">${ltr}</span><span>${name}</span><span>${st} · ${when}</span></div>`;
  }).join("");
  const note = document.getElementById("fail-note");
  const ee = (fromLetters.earth_engine && fromLetters.earth_engine.status) || svc.earth_engine;
  if (h.failed_letter) {
    note.hidden = false;
    note.textContent = h.failed_letter;
  } else if (ee === "failed") {
    note.hidden = false;
    note.textContent =
      "Earth Engine FAILED — join cannot MATCH without NASADEM; do not close on intersect-only.";
  }
  document.getElementById("clock-mode").textContent = `mode · ${(h.clock && h.clock.mode) || "wall"}`;
  document.getElementById("clock-window").textContent = `D5 window ${
    (h.clock && h.clock.d5_tmc_open) || "06:00"
  }–${(h.clock && h.clock.d5_tmc_close) || "18:00"} ${
    (h.clock && h.clock.tz) || "America/Los_Angeles"
  } · weekdays_only=${!!(h.clock && h.clock.weekdays_only)}`;
  document.getElementById("live-gun").textContent = `live_gun · ${h.live_gun}`;
  document.getElementById("ee-firms").textContent = `ee_firms_not_live_gun · ${h.ee_firms_not_live_gun}`;
  const elig = h.eligibility || {};
  const route = elig.gemini_routing || {};
  const overnight = (route.overnight && route.overnight.model) || elig.gemini || "gemini-3.7-flash";
  const quote = (route.quote && route.quote.model) || overnight;
  document.getElementById("elig-gemini").textContent = `gemini · primary ${overnight} · quote ${quote} · ${
    elig.gemini_access || "Vertex AI"
  }`;
  document.getElementById("elig-adk").textContent = `agent_framework · ${elig.agent_framework || "Google ADK"} · ${
    elig.agent_framework_detail || "LlmAgent + AgentTool + FunctionTool"
  }`;
  const cloud = elig.cloud_infrastructure || [];
  document.getElementById("elig-cloud").textContent = `cloud_infrastructure · ${
    cloud.length ? cloud.join(" · ") : "Cloud Functions · Firestore · Pub/Sub · …"
  }`;
  document.getElementById("elig-track").textContent = `track · ${elig.track || "Taskmaster"} · not a chatbot`;
}

const boot = window.TMC_HEALTH_BOOT;
if (boot && boot.services) {
  paint(boot);
} else {
  fetch(window.TMC.api("/health?format=json"))
    .then((r) => r.json())
    .then(paint);
}
