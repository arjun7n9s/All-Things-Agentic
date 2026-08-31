function chip(label, value, kind) {
  const el = document.createElement("span");
  el.className = "chip" + (kind ? " " + kind : "");
  el.textContent = `${label} · ${value}`;
  return el;
}

function paint(data) {
  const score = document.getElementById("conf-score");
  const cold = data.cold;
  score.textContent = cold
    ? `score · ${data.score} cold · cold start`
    : `score · ${data.score}`;
  if (cold) score.classList.add("warn");
  const box = document.getElementById("conf-chips");
  box.innerHTML = "";
  Object.entries(data.checks || {}).forEach(([k, v]) => {
    const c = chip(k, v ? "pass" : "pass · no", v ? "pass" : "bad");
    if (!v) {
      c.addEventListener("click", () => {
        let acc = c.nextElementSibling;
        if (!acc || !acc.classList.contains("accordion")) {
          acc = document.createElement("div");
          acc.className = "accordion";
          acc.textContent = `Missing: ${k}. The live Firestore record does not yet hold this claim.`;
          c.after(acc);
        }
        acc.classList.toggle("on");
      });
    }
    box.appendChild(c);
  });
  document.getElementById("conf-raw").textContent = JSON.stringify(data, null, 2);
}

const boot = window.TMC_CONF_BOOT;
if (boot && boot.score) {
  paint(boot);
} else {
  fetch(window.TMC.api("/conformance?format=json"))
    .then((r) => r.json())
    .then(paint);
}

document.getElementById("toggle-raw").addEventListener("click", () => {
  document.getElementById("conf-raw").classList.toggle("on");
});
