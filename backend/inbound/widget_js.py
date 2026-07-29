# Snippet embebible del widget web (vanilla JS, sin dependencias). Se sirve en
# GET /widget.js. Uso en la web del cliente:
#   <script src="https://TU_DOMINIO/widget.js"
#           data-key="CLAVE_PUBLICA" data-api="https://TU_DOMINIO"></script>
WIDGET_JS = r"""
(function () {
  var s = document.currentScript;
  var KEY = s && s.getAttribute("data-key");
  var API = (s && s.getAttribute("data-api")) || "";
  if (!KEY) { console.error("[AllSafe widget] falta data-key"); return; }
  var ACCENT = (s && s.getAttribute("data-accent")) || "#0038FF";

  var css = ""
    + ".asw-bubble{position:fixed;bottom:20px;right:20px;width:56px;height:56px;border-radius:50%;"
    + "background:" + ACCENT + ";color:#fff;font-size:26px;border:none;cursor:pointer;box-shadow:0 6px 20px rgba(0,0,0,.25);z-index:2147483000}"
    + ".asw-panel{position:fixed;bottom:88px;right:20px;width:340px;max-width:92vw;max-height:70vh;background:#fff;color:#111;"
    + "border-radius:14px;box-shadow:0 12px 40px rgba(0,0,0,.28);display:none;flex-direction:column;overflow:hidden;z-index:2147483000;font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif}"
    + ".asw-open{display:flex}"
    + ".asw-head{background:" + ACCENT + ";color:#fff;padding:12px 14px;font-weight:600;font-size:14px}"
    + ".asw-body{padding:12px 14px;overflow-y:auto;font-size:14px;line-height:1.5}"
    + ".asw-msg{margin:0 0 10px;white-space:pre-wrap}"
    + ".asw-src{font-size:11px;color:#666;margin-top:6px}"
    + ".asw-foot{border-top:1px solid #eee;padding:10px;display:flex;gap:6px}"
    + ".asw-inp{flex:1;border:1px solid #ddd;border-radius:8px;padding:8px 10px;font-size:14px;outline:none}"
    + ".asw-send{border:none;background:" + ACCENT + ";color:#fff;border-radius:8px;padding:0 12px;cursor:pointer}"
    + ".asw-btn{border:none;background:" + ACCENT + ";color:#fff;border-radius:8px;padding:8px 12px;cursor:pointer;font-size:13px;margin-top:6px}"
    + ".asw-btn.sec{background:#eee;color:#333}";
  var st = document.createElement("style"); st.textContent = css; document.head.appendChild(st);

  var bubble = document.createElement("button");
  bubble.className = "asw-bubble"; bubble.setAttribute("aria-label", "Ayuda"); bubble.textContent = "💬";
  var panel = document.createElement("div"); panel.className = "asw-panel";
  panel.innerHTML =
    '<div class="asw-head">¿En qué te ayudamos?</div>'
    + '<div class="asw-body" id="asw-body"><p class="asw-msg">Holá 👋 Escribí tu consulta y te respondo al toque.</p></div>'
    + '<div class="asw-foot"><input class="asw-inp" id="asw-inp" placeholder="Tu consulta…" />'
    + '<button class="asw-send" id="asw-send">Enviar</button></div>';
  document.body.appendChild(bubble); document.body.appendChild(panel);

  var body = panel.querySelector("#asw-body");
  var inp = panel.querySelector("#asw-inp");
  var lastQuery = "";

  bubble.onclick = function () { panel.classList.toggle("asw-open"); if (panel.classList.contains("asw-open")) inp.focus(); };

  function add(html) { var d = document.createElement("div"); d.innerHTML = html; body.appendChild(d); body.scrollTop = body.scrollHeight; return d; }
  function esc(t) { var e = document.createElement("div"); e.textContent = t; return e.innerHTML; }

  function ask() {
    var q = (inp.value || "").trim(); if (!q) return; lastQuery = q; inp.value = "";
    add('<p class="asw-msg" style="text-align:right;color:#333"><b>' + esc(q) + "</b></p>");
    var wait = add('<p class="asw-msg" style="color:#888">Pensando…</p>');
    fetch(API + "/api/widget/" + encodeURIComponent(KEY) + "/ask/", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: q })
    }).then(function (r) { return r.json(); }).then(function (d) {
      wait.remove();
      if (d && d.resolved && d.answer) {
        var src = (d.sources || []).map(function (x) { return esc(x.title); }).join(" · ");
        add('<p class="asw-msg">' + esc(d.answer) + "</p>" + (src ? '<div class="asw-src">📄 ' + src + "</div>" : ""));
      } else {
        add('<p class="asw-msg">No encontré una respuesta exacta. ¿Querés que te contactemos?</p>');
        contactForm();
      }
    }).catch(function () { wait.remove(); add('<p class="asw-msg" style="color:#c33">Hubo un error. Probá de nuevo.</p>'); });
  }

  function contactForm() {
    var box = add('<input class="asw-inp" id="asw-email" placeholder="Tu email" style="width:100%;margin-bottom:6px" />'
      + '<button class="asw-btn" id="asw-contact">Crear ticket</button>');
    box.querySelector("#asw-contact").onclick = function () {
      var email = (box.querySelector("#asw-email").value || "").trim();
      if (!email) { box.querySelector("#asw-email").focus(); return; }
      fetch(API + "/api/widget/" + encodeURIComponent(KEY) + "/contact/", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: lastQuery, email: email })
      }).then(function (r) { return r.json(); }).then(function (d) {
        box.remove();
        add('<p class="asw-msg">✅ ¡Listo! Creamos tu ticket' + (d && d.reference ? " <b>" + esc(d.reference) + "</b>" : "") + " y te vamos a contactar por email.</p>");
      }).catch(function () { add('<p class="asw-msg" style="color:#c33">No se pudo crear el ticket.</p>'); });
    };
  }

  panel.querySelector("#asw-send").onclick = ask;
  inp.addEventListener("keydown", function (e) { if (e.key === "Enter") ask(); });
})();
"""
