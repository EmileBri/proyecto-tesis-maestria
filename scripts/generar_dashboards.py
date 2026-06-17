#!/usr/bin/env python3
import json, sys
from collections import Counter
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import numpy as np

DARK_GREEN   = '#1B5E20'
MED_GREEN    = '#2E7D32'
LIGHT_GREEN  = '#E8F5E9'
BORDER_GREEN = '#43A047'
WHITE        = '#FFFFFF'
GRAY_SUB     = '#777777'

def load_checkpoint(path):
    votes, concs = [], []
    with open(path, encoding='utf-8', errors='replace') as f:
        for line in f:
            line = line.strip()
            if not line: continue
            try:
                r = json.loads(line)
                votes.append(str(r.get('voto_ensamble', 'indeterminado')).strip().lower())
                concs.append(float(r.get('concordancia', 0)))
            except: pass
    return votes, concs

print("Cargando checkpoints...", flush=True)
v5, c5 = load_checkpoint("/Users/emiliano/Desktop/Proyecto de Tesis/datos/resultados/etiquetado/pipeline_pipeline_5estrellas/etiquetado_5est_semillas_checkpoint.jsonl")
v3, c3 = load_checkpoint("/Users/emiliano/Desktop/Proyecto de Tesis/datos/resultados/etiquetado/pipeline_llm/_archivo_checkpoint_full.jsonl")

for label, votes, concs in [("5cls", v5, c5), ("3cls", v3, c3)]:
    print(f"{label}: n={len(votes)}, uniq={set(votes)}")
    print(f"  concordancia_media={np.mean(concs)*100:.1f}%")
    print(f"  unanime={sum(1 for x in concs if x>=0.999)/len(concs)*100:.1f}%")
    print(f"  dist={Counter(votes).most_common()}")

def pct_dist(votes, order):
    n = len(votes)
    cnt = Counter(votes)
    return [(k, cnt.get(k, 0)/n*100) for k in order if cnt.get(k, 0) > 0]

def draw_dashboard(path_out, n_rows, conc_pct, unan_pct,
                   hours, dist_items, model_rows):
    """
    dist_items : list of (display_label, pct, bar_color)
    model_rows : list of (name, company, params, errors, rate, rol)
    """
    W, H = 14, 8
    fig = plt.figure(figsize=(W, H))
    fig.patch.set_facecolor(WHITE)

    # Use gridspec: header row + KPI row + content row
    # All drawing in data coords on a hidden host ax
    ax = fig.add_axes([0.02, 0.02, 0.96, 0.96])   # 2% margin all sides
    ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    ax.axis('off')
    fig.patch.set_facecolor(WHITE)

    # ── Header (y: 0.87–1.0) ──────────────────────────────────────────────────
    ax.add_patch(FancyBboxPatch((0, 0.87), 1, 0.13,
                  boxstyle="square,pad=0", fc=DARK_GREEN, ec='none',
                  transform=ax.transAxes))
    ax.text(0.025, 0.935,
            f"Resultados del etiquetado ensamble  ·  n = {n_rows:,}",
            color=WHITE, fontsize=21, fontweight='bold', va='center',
            transform=ax.transAxes)

    # ── KPI cards (y: 0.670–0.860) ────────────────────────────────────────────
    KPI_Y = 0.670; KPI_H = 0.185; KPI_W = 0.295; GAP = 0.0125
    kpis = [
        (f"{n_rows:,}",       "reseñas etiquetadas",   "Seeds & Grasses"),
        (f"{conc_pct:.1f}%",  "concordancia media",    f"3 modelos · {hours} hs"),
        (f"{unan_pct:.1f}%",  "acuerdo unánime (3/3)", f"{int(n_rows*unan_pct/100):,} coincidencias"),
    ]
    xs = [GAP, GAP + KPI_W + GAP, GAP + 2*(KPI_W + GAP)]
    for i, (val, lbl, sub) in enumerate(kpis):
        ax.add_patch(FancyBboxPatch((xs[i], KPI_Y), KPI_W, KPI_H,
                      boxstyle="round,pad=0.008", fc=LIGHT_GREEN,
                      ec=BORDER_GREEN, lw=1.8, transform=ax.transAxes))
        ax.text(xs[i]+0.018, KPI_Y+KPI_H-0.018, val,
                color=MED_GREEN, fontsize=28, fontweight='bold', va='top',
                transform=ax.transAxes)
        ax.text(xs[i]+0.018, KPI_Y+0.062, lbl,
                color=MED_GREEN, fontsize=11, fontweight='bold', va='center',
                transform=ax.transAxes)
        ax.text(xs[i]+0.018, KPI_Y+0.022, sub,
                color=GRAY_SUB, fontsize=9, va='center', transform=ax.transAxes)

    # ── Layout constants ──────────────────────────────────────────────────────
    C_BOT     = 0.035   # bottom margin
    TITLE_Y   = 0.638   # section title top
    BAR_TOP   = 0.545   # first bar top
    LBAR_X    = 0.220   # bar start x (after labels)
    LBAR_XMAX = 0.335   # max bar width (ends at 0.555)
    TX  = 0.600         # table left edge
    TW  = 0.380         # table width (ends at 0.980)
    TRH = 0.072         # row height
    TY  = 0.635         # table header TOP y (header occupies TY-TRH → TY)

    # ── Right: model table drawn first ───────────────────────────────────────
    cols = ["Modelo", "Empresa", "Params", "Errores", "Tasa", "Rol"]
    cw   = [0.098, 0.076, 0.064, 0.052, 0.046, 0.038]  # sum=0.374

    ax.add_patch(FancyBboxPatch((TX, TY - TRH), TW, TRH,
                  boxstyle="square,pad=0", fc=DARK_GREEN, ec='none',
                  transform=ax.transAxes))
    cx = TX + 0.005
    for col, w in zip(cols, cw):
        ax.text(cx + w/2, TY - TRH/2, col, color=WHITE,
                fontsize=9, fontweight='bold', va='center', ha='center',
                transform=ax.transAxes)
        cx += w

    row_fc = [LIGHT_GREEN, WHITE]
    for ri, row in enumerate(model_rows):
        ry = TY - TRH - (ri+1)*TRH
        ax.add_patch(FancyBboxPatch((TX, ry), TW, TRH,
                      boxstyle="square,pad=0", fc=row_fc[ri%2],
                      ec='#CCCCCC', lw=0.5, transform=ax.transAxes))
        cx = TX + 0.005
        for val, w in zip(row, cw):
            ax.text(cx + w/2, ry + TRH/2, str(val), color='#1A1A1A',
                    fontsize=10, va='center', ha='center', transform=ax.transAxes)
            cx += w

    # ── Left: bar chart drawn second ─────────────────────────────────────────
    n_bars  = len(dist_items)
    avail   = BAR_TOP - C_BOT
    spacing = avail / max(n_bars, 1)
    bar_h   = min(spacing * 0.60, 0.080)

    for i, (lbl, pct, color) in enumerate(dist_items):
        by = BAR_TOP - i * spacing
        ax.text(0.012, by + bar_h/2, lbl, color='#1A1A1A', fontsize=12,
                fontweight='bold', va='center', ha='left', transform=ax.transAxes)
        ax.add_patch(FancyBboxPatch((LBAR_X, by+0.003), LBAR_XMAX, bar_h-0.006,
                      boxstyle="round,pad=0.002", fc='#E0E0E0', ec='none',
                      transform=ax.transAxes))
        blen = max((pct/100)*LBAR_XMAX, 0.003)
        ax.add_patch(FancyBboxPatch((LBAR_X, by+0.003), blen, bar_h-0.006,
                      boxstyle="round,pad=0.002", fc=color, ec='none',
                      transform=ax.transAxes))
        ax.text(LBAR_X + blen + 0.010, by + bar_h/2,
                f"{pct:.1f}%", color=color, fontsize=11, fontweight='bold',
                va='center', transform=ax.transAxes)

    # ── Section title drawn LAST (on top of everything in left panel) ─────────
    ax.text(0.012, TITLE_Y,
            "Distribución de votos del ensamble",
            color=MED_GREEN, fontsize=12, fontweight='bold', va='top',
            transform=ax.transAxes, zorder=10)

    plt.savefig(path_out, dpi=150, facecolor=WHITE)
    plt.close(fig)
    print(f"  → {path_out}")


# ══════════════════════════════════════════════════════════════════════════════
# Experiment A — 5 clases
# ══════════════════════════════════════════════════════════════════════════════
n5 = len(v5)
conc5 = np.mean(c5)*100
unan5 = sum(1 for x in c5 if x >= 0.999)/n5*100

ORDER_5   = ['muy_bueno','bueno','neutral','malo','muy_malo','indeterminado',
             'muy bueno','bueno','neutral','malo','muy malo','indeterminado']
COLORS_5  = {'muy_bueno':'#2E7D32','bueno':'#66BB6A','neutral':'#827717',
             'malo':'#E53935','muy_malo':'#B71C1C',
             'muy bueno':'#2E7D32','muy malo':'#B71C1C',
             'indeterminado':'#9E9E9E'}
LABELS_5  = {'muy_bueno':'Muy bueno','bueno':'Bueno','neutral':'Neutral',
             'malo':'Malo','muy_malo':'Muy malo',
             'muy bueno':'Muy bueno','muy malo':'Muy malo',
             'indeterminado':'Indeterminado'}

cnt5 = Counter(v5)
# build ordered list
seen = set()
dist5 = []
for key in ['muy_bueno','muy bueno','bueno','neutral','malo','muy_malo','muy malo','indeterminado']:
    if key in cnt5 and key not in seen:
        seen.add(key)
        pct = cnt5[key]/n5*100
        if pct > 0.05:
            dist5.append((LABELS_5.get(key, key).capitalize(), pct, COLORS_5.get(key,'#9E9E9E')))

models_5 = [
    ("gemma2:9b",  "Google",     "9 B",   "—", "—", "Votante"),
    ("mistral:7b", "Mistral AI", "7 B",   "—", "—", "Votante"),
    ("llama3.2",   "Meta",       "3.2 B", "—", "—", "Votante"),
]

print("Generando dashboard 5 clases...")
draw_dashboard(
    "/Users/emiliano/Desktop/dashboard_5clases.png",
    n5, conc5, unan5, "~48", dist5, models_5
)

# ══════════════════════════════════════════════════════════════════════════════
# Experiment B — 3 clases
# ══════════════════════════════════════════════════════════════════════════════
n3 = len(v3)
conc3 = np.mean(c3)*100
unan3 = sum(1 for x in c3 if x >= 0.999)/n3*100

COLORS_3 = {'positivo':'#2E7D32','neutral':'#827717','negativo':'#E53935','indeterminado':'#9E9E9E'}
cnt3 = Counter(v3)
dist3 = []
for key in ['positivo','neutral','negativo','indeterminado']:
    if key in cnt3:
        pct = cnt3[key]/n3*100
        if pct > 0.05:
            dist3.append((key.capitalize(), pct, COLORS_3[key]))

models_3 = [
    ("qwen2.5:1.5b", "Alibaba",   "1.5 B", "54",  "0.09%", "Votante"),
    ("gemma2:2b",    "Google",    "2.6 B",  "16",  "0.03%", "Votante"),
    ("phi4-mini",    "Microsoft", "3.8 B",  "20",  "0.03%", "Votante"),
]

print("Generando dashboard 3 clases...")
draw_dashboard(
    "/Users/emiliano/Desktop/dashboard_3clases.png",
    n3, conc3, unan3, "~26", dist3, models_3
)

print("Listo.")
