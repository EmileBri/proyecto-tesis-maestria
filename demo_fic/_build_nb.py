# -*- coding: utf-8 -*-
import nbformat as nbf
from pathlib import Path

nb = nbf.v4.new_notebook()
cells = []

cells.append(nbf.v4.new_markdown_cell(
"""# Demo — Clasificador de Reseñas con IA local

### Proyecto de Tesis · Maestría en Ciencia de Datos

Una página web donde **3 modelos de Inteligencia Artificial** leen el comentario de un cliente
y deciden, votando entre ellos, si la opinión es **positiva**, **neutral** o **negativa**.

Los tres modelos los crearon Alibaba, Google y Microsoft — y aquí corren **100 % locales**
en esta laptop, **sin internet**.

---
*Ejecuta las celdas en orden con ▶ (o Shift+Enter). La última abre la página en el navegador.*"""
))

# ── Celda 1: config ──────────────────────────────────────────────────────────
cells.append(nbf.v4.new_code_cell(
'''import re, json, time, random, httpx
from collections import Counter
import gradio as gr

OLLAMA_URL  = "http://localhost:11434/api/generate"
MODELOS     = ["qwen2.5:1.5b", "gemma2:2b", "phi4-mini"]
ETIQUETAS_VALIDAS = ["negativo", "neutral", "positivo"]
TIMEOUT_SEG = 120
NUM_PREDICT = 150
MAX_CHARS   = 1600

# nombre amigable + empresa creadora (engancha a los chavos)
INFO_MODELO = {
    "qwen2.5:1.5b": ("Qwen 2.5", "alibaba"),
    "gemma2:2b":    ("Gemma 2",  "google"),
    "phi4-mini":    ("Phi-4",    "microsoft"),
}

PROMPT_TEMPLATE = """\\
Eres un sistema de analisis de sentimientos para resenas de productos de jardineria.
Responde UNICAMENTE con un objeto JSON valido, sin texto adicional.

JSON con exactamente estas claves:
- "etiqueta": una de ["negativo", "neutral", "positivo"]
- "justificacion": 15-25 palabras en espanol

Criterio:
  negativo -> insatisfaccion, producto defectuoso, no funciona, mala experiencia
  neutral  -> opinion mixta, ni buena ni mala, sin opinion clara
  positivo -> satisfaccion general o excelente experiencia

Resena: \\"{texto}\\"

JSON:"""

print("Config lista ·", len(MODELOS), "modelos:", ", ".join(n for n,_ in INFO_MODELO.values()))'''
))

# ── Celda 2: logica ──────────────────────────────────────────────────────────
cells.append(nbf.v4.new_code_cell(
'''# Misma logica de parseo y voto que el pipeline de etiquetado de la tesis
ALIAS = {
    "neg":"negativo","malo":"negativo","muy malo":"negativo","bad":"negativo","negative":"negativo",
    "pos":"positivo","bueno":"positivo","muy bueno":"positivo","good":"positivo","positive":"positivo",
    "neut":"neutral","neutral":"neutral",
}
ORDEN_ETIQUETAS = {e: i for i, e in enumerate(ETIQUETAS_VALIDAS)}

def truncar(texto, max_chars=MAX_CHARS):
    if len(texto) <= max_chars: return texto
    corte = texto[:max_chars].rfind(" ")
    return texto[:corte if corte > 0 else max_chars] + " [...]"

def parsear_respuesta(raw):
    raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
    m = re.search(r"\\{.*\\}", raw, re.DOTALL)
    if not m: return {"error": "no se encontro JSON"}
    try:
        datos = json.loads(m.group())
    except json.JSONDecodeError:
        return {"error": "JSON invalido"}
    et = str(datos.get("etiqueta", "")).strip().lower()
    if et not in ETIQUETAS_VALIDAS:
        mapped = ALIAS.get(et)
        if mapped:
            datos["etiqueta"] = mapped
        else:
            for e in ETIQUETAS_VALIDAS:
                if e in et or (et and et in e):
                    datos["etiqueta"] = e; break
            else:
                datos["error"] = f"etiqueta invalida: {et!r}"
    else:
        datos["etiqueta"] = et
    return datos

def calcular_voto(etiquetas_modelos):
    votos = [v.get("etiqueta") for v in etiquetas_modelos.values()
             if "error" not in v and v.get("etiqueta") in ETIQUETAS_VALIDAS]
    if not votos: return {"voto_ensamble": None, "concordancia": 0.0}
    conteo = Counter(votos)
    voto, _ = conteo.most_common(1)[0]
    if len(conteo) == len(votos):  # empate -> mediana por orden
        idx = sorted(ORDEN_ETIQUETAS[v] for v in votos)
        voto = ETIQUETAS_VALIDAS[idx[len(idx)//2]]
    return {"voto_ensamble": voto, "concordancia": round(votos.count(voto)/len(votos), 2)}

def consultar_modelo(modelo, texto):
    payload = {"model": modelo, "prompt": PROMPT_TEMPLATE.format(texto=texto),
               "stream": False, "keep_alive": -1,
               "options": {"temperature": 0.1, "num_predict": NUM_PREDICT}}
    try:
        r = httpx.post(OLLAMA_URL, json=payload, timeout=TIMEOUT_SEG)
        r.raise_for_status()
        return parsear_respuesta(r.json().get("response", ""))
    except Exception as e:
        return {"error": str(e)[:80]}

print("Logica lista.")'''
))

# ── Celda 3: calentar ────────────────────────────────────────────────────────
cells.append(nbf.v4.new_code_cell(
'''# Carga los modelos en memoria para que la demo responda rapido
print("Calentando modelos (la 1a vez tarda unos segundos)...")
for m in MODELOS:
    r = consultar_modelo(m, "Las semillas germinaron perfecto, muy contento.")
    print(f"  {INFO_MODELO[m][0]:<10} -> {r.get('etiqueta', r.get('error','?'))}")
print("Modelos listos y calientes.")'''
))

# ── Celda 4: interfaz ────────────────────────────────────────────────────────
ui = r'''# ── Interfaz web ───────────────────────────────────────────────────────────────
import webbrowser
from pathlib import Path

IMG = Path("imgs")
PRODUCTOS = [
    (str(IMG / "semillas.jpg"),    "Semillas de hortaliza"),
    (str(IMG / "plantula.jpg"),    "Plantula germinada"),
    (str(IMG / "tierra.jpg"),      "Tierra y abono"),
    (str(IMG / "flores.jpg"),      "Plantas con flor"),
    (str(IMG / "tomates.jpg"),     "Tomates cherry"),
    (str(IMG / "girasoles.jpg"),   "Girasoles"),
    (str(IMG / "albahaca.jpg"),    "Albahaca en maceta"),
    (str(IMG / "suculenta.jpg"),   "Suculenta en maceta"),
    (str(IMG / "fresas.jpg"),      "Fresas"),
    (str(IMG / "jardin.jpg"),      "Jardin de flores"),
    (str(IMG / "trasplante.jpg"),  "Kit de trasplante"),
    (str(IMG / "riego.jpg"),       "Riego del huerto"),
]

SENT = {
    "positivo": {"c": "#15a34a", "soft": "#dcfce7", "lbl": "Positivo", "ic": "&#10003;"},
    "neutral":  {"c": "#d97706", "soft": "#fef3c7", "lbl": "Neutral",  "ic": "&#8211;"},
    "negativo": {"c": "#e11d48", "soft": "#ffe4e6", "lbl": "Negativo", "ic": "&#10007;"},
}

EJEMPLOS = [
    # claros
    "Las semillas germinaron en una semana, calidad excelente y muy buen precio.",
    "No germino ni una sola, perdi mi dinero y el empaque llego maltratado.",
    # trampa / ambiguos (suelen hacer que los modelos no coincidan)
    "El producto es muy bueno, pero el envio fue un desastre y llego tardisimo.",
    "Cumple lo que promete, nada del otro mundo la verdad.",
    "Excelente, si lo que querias era no cosechar absolutamente nada.",
    "No esta mal del todo, aunque por el precio esperaba bastante mas.",
    "Crecieron algunas plantas pero muchas otras no, resultado regular.",
]

# ── Logos de marca con sus colores reales ──
def logo_empresa(emp):
    if emp == "google":
        cols = [("G","#4285F4"),("o","#EA4335"),("o","#FBBC05"),("g","#4285F4"),("l","#34A853"),("e","#EA4335")]
        letras = "".join(f"<span style='color:{c}'>{ch}</span>" for ch,c in cols)
        return f"<span class='brand'>{letras}</span>"
    if emp == "microsoft":
        sq = ("<span class='ms-grid'>"
              "<i style='background:#F25022'></i><i style='background:#7FBA00'></i>"
              "<i style='background:#00A4EF'></i><i style='background:#FFB900'></i></span>")
        return f"<span class='brand ms'>{sq}<span style='color:#5e5e5e'>Microsoft</span></span>"
    if emp == "alibaba":
        return "<span class='brand' style='color:#FF6A00;font-weight:800'>Alibaba</span>"
    return f"<span class='brand'>{emp}</span>"

def chip_modelo(modelo):
    nombre, emp = INFO_MODELO[modelo]
    return (f"<div class='m-id'><span class='m-ava'>{nombre[0]}</span>"
            f"<span class='m-name'>{nombre}</span>"
            f"<span class='m-org'>{logo_empresa(emp)}</span></div>")

def card_pendiente(modelo, activo):
    estado = ("<span class='typing'><i></i><i></i><i></i></span>" if activo
              else "<span class='m-wait'>en espera</span>")
    cls = "m-card thinking" if activo else "m-card waiting"
    return f"<div class='{cls}'>{chip_modelo(modelo)}{estado}</div>"

def card_resultado(modelo, res, t=None):
    if "error" in res:
        return (f"<div class='m-card done'>{chip_modelo(modelo)}"
                f"<span class='m-wait'>sin respuesta</span></div>")
    et = res.get("etiqueta", "neutral"); s = SENT.get(et, SENT["neutral"])
    just = res.get("justificacion", "")
    chip_t = f"<span class='m-time'>{t:.1f}s</span>" if t is not None else ""
    raw = json.dumps({"etiqueta": et, "justificacion": just}, ensure_ascii=False, indent=2)
    detalle = (f"<details class='m-raw'><summary>ver cómo piensa la IA</summary>"
               f"<pre>{raw}</pre></details>")
    return (f"<div class='m-card done pop'>{chip_modelo(modelo)}"
            f"<div class='m-row'><span class='m-badge' style='background:{s['soft']};color:{s['c']}'>"
            f"{s['ic']} {s['lbl']}</span>{chip_t}</div>"
            f"<p class='m-just'>{just}</p>{detalle}</div>")

def render_modelos(resultados, activo, tiempos=None):
    tiempos = tiempos or {}
    out = []
    for m in MODELOS:
        if m in resultados:
            out.append(card_resultado(m, resultados[m], tiempos.get(m)))
        else:
            out.append(card_pendiente(m, activo == m))
    return f"<div class='m-grid'>{''.join(out)}</div>"

def render_veredicto(voto=None, hechos=0, dist=None, total_t=None, vacio=False):
    total = len(MODELOS)
    if vacio:
        return ("<div class='verdict empty'><div class='v-eyebrow'>Esperando comentario</div>"
                "<div class='v-hint'>Elige un producto y escribe una opinion de cliente</div></div>")
    pct = int(hechos / total * 100)
    if voto is None:
        return ("<div class='verdict working'>"
                "<div class='v-eyebrow'>La IA esta analizando</div>"
                "<div class='v-spinner'></div>"
                f"<div class='v-bar'><div class='v-bar-fill' style='width:{pct}%'></div></div>"
                f"<div class='v-count'>{hechos} de {total} modelos han votado</div></div>")
    s = SENT[voto["voto_ensamble"]]; pc = int(voto["concordancia"] * 100)
    desglose = ""
    if dist:
        partes = [f"<span style='color:{SENT[e]['c']};font-weight:700'>{dist[e]} {SENT[e]['lbl'].lower()}</span>"
                  for e in ETIQUETAS_VALIDAS if dist.get(e)]
        desglose = "<div class='v-tally'>" + " · ".join(partes) + "</div>"
    tt = f"<div class='v-count'>analizado en {total_t:.1f} segundos &middot; 100% local</div>" if total_t else ""
    # confeti cuando los 3 modelos coinciden en POSITIVO
    confeti = ""
    if voto["voto_ensamble"] == "positivo" and voto["concordancia"] == 1.0:
        cols = ["#15a34a", "#34d399", "#fbbf24", "#60a5fa", "#f472b6", "#fb7185"]
        piezas = "".join(
            f"<span class='cf' style='left:{random.randint(0,100)}%;background:{random.choice(cols)};"
            f"animation-delay:{random.uniform(0,.6):.2f}s;animation-duration:{random.uniform(1.6,2.8):.2f}s'></span>"
            for _ in range(28))
        confeti = f"<div class='confetti'>{piezas}</div>"
    return (f"<div class='verdict reveal' style='--c:{s['c']};--soft:{s['soft']}'>"
            f"{confeti}"
            f"<div class='v-eyebrow'>Veredicto del ensamble</div>"
            f"<div class='v-big'><span class='v-ic'>{s['ic']}</span>{s['lbl']}</div>"
            f"<div class='v-agree'>{pc}% de los modelos coinciden</div>"
            f"{desglose}"
            f"<div class='v-bar'><div class='v-bar-fill done' style='width:100%'></div></div>"
            f"{tt}</div>")

def render_aviso(titulo, hint):
    return (f"<div class='verdict empty'><div class='v-eyebrow'>{titulo}</div>"
            f"<div class='v-hint'>{hint}</div></div>")

def render_error(detalle=""):
    extra = f"<div class='err-detail'>{detalle}</div>" if detalle else ""
    return ("<div class='verdict err'>"
            "<div class='err-ic'>!</div>"
            "<div class='v-big' style='color:#e11d48;font-size:1.5rem'>No se pudo analizar</div>"
            "<div class='v-hint'>Parece que los modelos no respondieron. "
            "Verifica que <b>ollama</b> esté corriendo y vuelve a ejecutar la "
            "<b>celda 4</b> (▶) del notebook.</div>"
            f"{extra}</div>")

# Estados del boton (se deshabilita mientras la IA piensa -> no se puede clickear 2 veces)
BTN_OFF = gr.update(interactive=False, value="Analizando…")
BTN_ON  = gr.update(interactive=True,  value="Analizar con la IA")

def clasificar(comentario):
    comentario = (comentario or "").strip()
    # 1) bloquear envios vacios
    if not comentario:
        yield (render_aviso("Escribe un comentario primero",
                            "Elige un producto y cuéntale a la IA qué opinas, como si fueras un cliente."),
               render_modelos({}, None), BTN_ON)
        return
    try:
        texto = truncar(comentario)
        resultados, tiempos = {}, {}
        t_ini = time.time()
        # 2) boton OFF durante todo el analisis
        yield render_veredicto(hechos=0), render_modelos(resultados, MODELOS[0]), BTN_OFF
        for i, m in enumerate(MODELOS):
            t0 = time.time()
            resultados[m] = consultar_modelo(m, texto)
            tiempos[m] = time.time() - t0
            siguiente = MODELOS[i + 1] if i + 1 < len(MODELOS) else None
            yield (render_veredicto(hechos=len(resultados)),
                   render_modelos(resultados, siguiente, tiempos), BTN_OFF)
        voto = calcular_voto(resultados)
        # 3) si NINGUN modelo respondio -> aviso de error (no se cuelga)
        if voto["voto_ensamble"] is None:
            yield render_error(), render_modelos(resultados, None, tiempos), BTN_ON
            return
        dist = Counter(v.get("etiqueta") for v in resultados.values() if "error" not in v)
        yield (render_veredicto(voto=voto, hechos=len(MODELOS), dist=dist, total_t=time.time()-t_ini),
               render_modelos(resultados, None, tiempos), BTN_ON)
    except Exception as e:
        # 4) cualquier fallo inesperado -> aviso claro y boton reactivado
        yield render_error(str(e)[:120]), render_modelos({}, None), BTN_ON

def elegir_producto(evt: gr.SelectData):
    nombre = PRODUCTOS[evt.index][1]
    return (f"<div class='picked'><span class='picked-dot'></span>"
            f"Opinando sobre: <b>{nombre}</b></div>")

def badge_contador(n):
    return (f"<div class='counter'><span class='counter-dot'></span>"
            f"Reseñas analizadas en esta sesión: <b>{n}</b></div>")

def incrementar(n, texto):
    if (texto or "").strip():
        n += 1
    return n, badge_contador(n)

CSS = """
:root{ --ink:#0f172a; --muted:#64748b; --line:#e7e9ee; --brand:#0e7c5a; --brand2:#34d399; }
.gradio-container{max-width:100% !important; padding:0 !important; background:#f4f6f8 !important;
  font-family:'Inter',system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;}
#hero{background:linear-gradient(120deg,#0b3d2e,#0e7c5a 45%,#10b981);
  background-size:200% 200%; animation:flow 14s ease infinite;
  color:#fff; padding:26px 36px; border-radius:0 0 24px 24px; margin-bottom:18px;
  box-shadow:0 18px 40px -22px rgba(14,124,90,.7);}
@keyframes flow{0%{background-position:0% 50%}50%{background-position:100% 50%}100%{background-position:0% 50%}}
#hero h1{margin:0; font-size:1.9rem; font-weight:800; letter-spacing:-.5px; color:#fff;}
#hero p{margin:6px 0 0; opacity:.92; font-size:1rem; max-width:720px; color:#fff;}
#hero .tags{margin-top:14px; display:flex; gap:8px; flex-wrap:wrap;}
#hero .tags span{background:rgba(255,255,255,.16); padding:5px 12px; border-radius:999px;
  font-size:.8rem; font-weight:600;}
.panel{background:#fff !important; border:1px solid var(--line); border-radius:18px; padding:18px;}
.step{font-size:.72rem; font-weight:800; letter-spacing:.12em; text-transform:uppercase;
  color:var(--brand); margin:2px 0 10px;}
#go-btn{background:linear-gradient(120deg,#0e7c5a,#10b981) !important; border:0 !important;
  color:#fff !important; font-weight:700 !important; font-size:1.05rem !important;
  border-radius:14px !important; box-shadow:0 10px 24px -10px rgba(16,185,129,.8) !important;
  transition:transform .15s ease, box-shadow .15s ease !important;}
#go-btn:hover{transform:translateY(-2px) !important; box-shadow:0 16px 30px -10px rgba(16,185,129,.9) !important;}
#go-btn:active{transform:translateY(0) scale(.99) !important;}
.picked{font-size:.92rem; color:var(--ink); background:#f1fdf8; border:1px solid #c7f0de;
  padding:9px 14px; border-radius:12px; display:flex; align-items:center; gap:9px; font-weight:500;}
.picked b{color:var(--brand);}
.picked-dot{width:9px;height:9px;border-radius:50%;background:var(--brand2);
  box-shadow:0 0 0 0 rgba(52,211,153,.6); animation:ping 1.6s infinite; flex:none;}
@keyframes ping{0%{box-shadow:0 0 0 0 rgba(52,211,153,.55)}70%{box-shadow:0 0 0 10px rgba(52,211,153,0)}100%{box-shadow:0 0 0 0 rgba(52,211,153,0)}}

.counter{font-size:.8rem; color:var(--muted); display:flex; align-items:center; gap:7px; font-weight:500;}
.counter b{color:var(--brand); font-size:.95rem;}
.counter-dot{width:7px;height:7px;border-radius:50%;background:var(--brand2);}

/* Veredicto */
.verdict{position:relative; overflow:hidden; border-radius:18px; padding:26px; text-align:center; min-height:200px;
  display:flex; flex-direction:column; align-items:center; justify-content:center; gap:10px;
  background:#fff; border:1px solid var(--line);}
/* Confeti (solo CSS) */
.confetti{position:absolute; inset:0; pointer-events:none; z-index:2;}
.cf{position:absolute; top:-16px; width:9px; height:15px; border-radius:2px; opacity:0;
  animation-name:fall; animation-timing-function:ease-in; animation-iteration-count:1;}
@keyframes fall{0%{transform:translateY(-20px) rotate(0); opacity:1}
  100%{transform:translateY(320px) rotate(540deg); opacity:0}}
.verdict.empty{color:var(--muted); border-style:dashed;}
.verdict.err{background:#fff5f6; border:2px solid #fecdd3;}
.err-ic{width:48px;height:48px;border-radius:50%;background:#e11d48;color:#fff;
  display:grid;place-items:center;font-size:1.8rem;font-weight:800;}
.err-detail{font-size:.74rem;color:#9f1239;background:#ffe4e6;border-radius:8px;
  padding:6px 10px;font-family:ui-monospace,Menlo,monospace;}
#go-btn[disabled], #go-btn:disabled{opacity:.6 !important; cursor:not-allowed !important;
  transform:none !important; filter:saturate(.7);}
.v-eyebrow{font-size:.74rem; font-weight:800; letter-spacing:.14em; text-transform:uppercase; color:var(--muted);}
.v-hint{font-size:1.05rem; color:var(--muted);}
.verdict.reveal{background:linear-gradient(180deg,#fff,var(--soft)); border:2px solid var(--c);
  animation:vpop .55s cubic-bezier(.2,.9,.3,1.4);}
@keyframes vpop{0%{transform:scale(.9); opacity:0}100%{transform:scale(1); opacity:1}}
.v-big{font-size:2.7rem; font-weight:850; color:var(--c); display:flex; align-items:center; gap:12px; line-height:1;}
.v-ic{display:inline-grid; place-items:center; width:50px;height:50px;border-radius:50%;
  background:var(--c); color:#fff; font-size:1.6rem;}
.v-agree{color:var(--muted); font-size:1rem; font-weight:600;}
.v-tally{font-size:.95rem;}
.v-spinner{width:40px;height:40px;border-radius:50%;border:4px solid #e2e8f0;border-top-color:var(--brand);
  animation:spin .8s linear infinite;}
@keyframes spin{to{transform:rotate(360deg)}}
.v-bar{width:80%; height:9px; background:#eef1f5; border-radius:99px; overflow:hidden; margin-top:6px;}
.v-bar-fill{height:100%; background:linear-gradient(90deg,#0e7c5a,#34d399); border-radius:99px;
  transition:width .5s cubic-bezier(.4,0,.2,1);}
.v-bar-fill.done{background:linear-gradient(90deg,var(--c),var(--c));}
.v-count{font-size:.82rem; color:var(--muted); margin-top:4px;}

/* Tarjetas de modelo */
.m-grid{display:grid; grid-template-columns:1fr; gap:12px; margin-top:14px;}
.m-card{position:relative; min-width:0; border:1px solid var(--line); border-radius:16px; padding:14px 16px;
  background:#fff; display:flex; flex-direction:column; gap:8px; transition:.25s;}
.m-card.waiting{opacity:.55;}
.m-card.thinking{border-color:var(--brand2); box-shadow:0 0 0 3px rgba(52,211,153,.15);}
.m-card.pop{animation:cardin .45s cubic-bezier(.2,.9,.3,1.3);}
@keyframes cardin{0%{transform:translateY(8px); opacity:0}100%{transform:translateY(0); opacity:1}}
.m-id{display:flex; align-items:center; gap:9px;}
.m-ava{width:30px;height:30px;border-radius:9px;display:grid;place-items:center;font-weight:800;color:#fff;
  background:linear-gradient(135deg,#0e7c5a,#34d399); font-size:.95rem; flex:none;}
.m-name{font-weight:700; color:var(--ink);}
.m-org{margin-left:auto;}
.brand{font-size:.9rem; font-weight:700; letter-spacing:-.2px; display:inline-flex; align-items:center; gap:0;}
.brand.ms{font-weight:600; gap:6px;}
.ms-grid{display:inline-grid; grid-template-columns:1fr 1fr; gap:1.5px; width:15px; height:15px;}
.ms-grid i{display:block; width:100%; height:100%;}
.m-row{display:flex; align-items:center; justify-content:space-between; gap:8px;}
.m-badge{padding:5px 12px; border-radius:99px; font-weight:800; font-size:.92rem;}
.m-just{margin:0; color:#475569; font-size:.9rem; line-height:1.45;}
.m-time{font-size:.72rem; color:#94a3b8; background:#f1f5f9; padding:2px 8px;
  border-radius:99px; font-weight:600; flex:none;}
.m-raw{margin-top:2px;}
.m-raw summary{cursor:pointer; font-size:.78rem; color:var(--brand); font-weight:600;
  list-style:none; user-select:none;}
.m-raw summary::-webkit-details-marker{display:none;}
.m-raw summary::before{content:'›'; display:inline-block; margin-right:5px; transition:.2s;}
.m-raw[open] summary::before{transform:rotate(90deg);}
.m-raw pre{margin:8px 0 0; background:#0f172a; color:#a7f3d0; border-radius:10px;
  padding:10px 12px; font-size:.78rem; line-height:1.4;
  white-space:pre-wrap; word-break:break-word; overflow-wrap:anywhere;
  font-family:ui-monospace,'SF Mono',Menlo,monospace;}
.m-wait{color:var(--muted); font-size:.85rem; font-style:italic;}
.typing{display:inline-flex; gap:5px; padding:3px 0;}
.typing i{width:8px;height:8px;border-radius:50%;background:var(--brand2);animation:bounce 1s infinite;}
.typing i:nth-child(2){animation-delay:.15s} .typing i:nth-child(3){animation-delay:.3s}
@keyframes bounce{0%,80%,100%{transform:translateY(0);opacity:.4}40%{transform:translateY(-6px);opacity:1}}
@media (min-width:1100px){ .m-grid{grid-template-columns:repeat(3,1fr);} }
footer{display:none !important;}
"""

with gr.Blocks(title="Clasificador de Reseñas con IA") as demo:
    gr.HTML("""
    <div id='hero'>
      <h1>¿Qué opina la Inteligencia Artificial de tu comentario?</h1>
      <p>Escribe la opinión de un cliente sobre un producto de jardinería y deja que
      tres modelos de IA la lean y voten si es positiva, neutral o negativa.</p>
      <div class='tags'><span>3 modelos votan</span><span>100% local</span>
      <span>sin internet</span><span>creados por Alibaba · Google · Microsoft</span></div>
    </div>
    """)
    with gr.Row(equal_height=False):
        with gr.Column(scale=5, min_width=380):
            with gr.Group(elem_classes="panel"):
                gr.HTML("<div class='step'>Paso 1 · Elige un producto</div>")
                galeria = gr.Gallery(value=PRODUCTOS, columns=1, height=360,
                                     object_fit="cover", allow_preview=False, show_label=False)
                elegido = gr.HTML("<div class='picked'><span class='picked-dot'></span>"
                                  "Opinando sobre: <b>Semillas de hortaliza</b></div>")
                gr.HTML("<div class='step' style='margin-top:14px'>Paso 2 · Escribe el comentario</div>")
                comentario = gr.Textbox(show_label=False, lines=3,
                    placeholder="Ej: Las semillas germinaron rapidísimo, súper recomendado!")
                boton = gr.Button("Analizar con la IA", elem_id="go-btn", size="lg")
                gr.Examples(EJEMPLOS, inputs=comentario, label="¿Sin ideas? Prueba uno:")
        with gr.Column(scale=7, min_width=420):
            with gr.Group(elem_classes="panel"):
                with gr.Row():
                    gr.HTML("<div class='step'>Resultado</div>")
                    salida_contador = gr.HTML(badge_contador(0))
                salida_veredicto = gr.HTML(render_veredicto(vacio=True))
                salida_modelos = gr.HTML(render_modelos({}, None))

    contador = gr.State(0)
    salidas = [salida_veredicto, salida_modelos, boton]
    galeria.select(elegir_producto, outputs=elegido)
    # concurrency_limit=1 + boton deshabilitado => imposible disparar 2 analisis a la vez
    boton.click(clasificar, inputs=comentario, outputs=salidas, concurrency_limit=1
        ).then(incrementar, inputs=[contador, comentario], outputs=[contador, salida_contador])
    comentario.submit(clasificar, inputs=comentario, outputs=salidas, concurrency_limit=1
        ).then(incrementar, inputs=[contador, comentario], outputs=[contador, salida_contador])

# inbrowser=False + abrir con ?__theme=light para forzar tema claro (el diseno es para fondo claro)
_app, _url, _ = demo.launch(prevent_thread_lock=True, inbrowser=False, quiet=True, css=CSS)
webbrowser.open(_url.rstrip("/") + "/?__theme=light")
print("Demo abierta (tema claro forzado):", _url + "?__theme=light")
'''
cells.append(nbf.v4.new_code_cell(ui))

nb["cells"] = cells
out = Path(__file__).parent / "demo_secundaria.ipynb"
nbf.write(nb, str(out))
print("Notebook escrito:", out)
