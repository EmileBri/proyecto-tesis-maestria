#!/usr/bin/env python3
import json
from collections import Counter
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
import numpy as np

def load_ckpt(path):
    votes, concs = [], []
    with open(path, encoding='utf-8', errors='replace') as f:
        for line in f:
            s = line.strip()
            if not s: continue
            try:
                r = json.loads(s)
                votes.append(str(r.get('voto_ensamble','?')).strip().lower())
                concs.append(float(r.get('concordancia', 0)))
            except: pass
    return votes, concs

print("Cargando...", flush=True)
v5, c5 = load_ckpt("/Users/emiliano/Desktop/Proyecto de Tesis/datos/resultados/"
                    "etiquetado_5est_semillas_checkpoint.jsonl")
v3, c3 = load_ckpt("/Users/emiliano/Desktop/Proyecto de Tesis/datos/resultados/"
                    "etiquetado_3cls_semillas_FULL_checkpoint.jsonl")

OLIVE    = '#6E7A28'
OLIVE_BG = '#EEF2D4'
OLIVE_DK = '#3A4010'

def kpi_ax(ax, value, label, sublabel, bg='#F4F7E4'):
    ax.set_facecolor(bg)
    ax.axis('off')
    ax.text(0.5, 0.70, value, transform=ax.transAxes,
            fontsize=24, fontweight='bold', color=OLIVE_DK,
            ha='center', va='center')
    ax.text(0.5, 0.36, label, transform=ax.transAxes,
            fontsize=10, fontweight='bold', color='#444444',
            ha='center', va='center')
    ax.text(0.5, 0.14, sublabel, transform=ax.transAxes,
            fontsize=8.5, color='#888888',
            ha='center', va='center')
    for spine in ax.spines.values():
        spine.set_edgecolor(OLIVE)
        spine.set_linewidth(1.2)
        spine.set_visible(True)

def make_chart(out, title, votes, concs,
               order, labels, colors, model_rows, hours):
    n    = len(votes)
    cnt  = Counter(votes)
    conc = np.mean(concs)*100
    unan = sum(x>=0.999 for x in concs)/n*100

    # bars: sort descending by value
    items = sorted([(labels[k], cnt.get(k,0)/n*100, colors[k])
                     for k in order], key=lambda x: x[1])
    lbls = [i[0] for i in items]
    pcts = [i[1] for i in items]
    clrs = [i[2] for i in items]

    n_bars = len(lbls)
    fig_h  = max(7.5, 5.5 + n_bars*0.4)
    fig = plt.figure(figsize=(15, fig_h))
    fig.patch.set_facecolor('white')

    # Layout: 4 rows x 2 cols
    # left col: 3 KPI rows + 1 table row; right col: full bar chart
    gs = GridSpec(4, 2, figure=fig,
                  width_ratios=[1.15, 2.1],
                  height_ratios=[1, 1, 1, 2.2],
                  hspace=0.45, wspace=0.30,
                  left=0.04, right=0.97,
                  top=0.84, bottom=0.09)

    ax_k1  = fig.add_subplot(gs[0, 0])
    ax_k2  = fig.add_subplot(gs[1, 0])
    ax_k3  = fig.add_subplot(gs[2, 0])
    ax_tbl = fig.add_subplot(gs[3, 0])
    ax_bar = fig.add_subplot(gs[:, 1])

    # ── Title ──────────────────────────────────────────────────────────────
    fig.text(0.50, 0.935, title,
             fontsize=16, fontweight='bold', ha='center', va='center',
             color='white',
             bbox=dict(boxstyle='round,pad=0.5', fc=OLIVE, ec='none'))

    # ── KPI cards ──────────────────────────────────────────────────────────
    kpi_ax(ax_k1, f"{n:,}",       "reseñas etiquetadas",    "Seeds & Grasses")
    kpi_ax(ax_k2, f"{conc:.1f}%", "concordancia media",     f"3 modelos · {hours} hs")
    kpi_ax(ax_k3, f"{unan:.1f}%", "acuerdo unánime (3/3)",  f"{int(n*unan/100):,} coincidencias")

    # ── Model table ────────────────────────────────────────────────────────
    ax_tbl.set_facecolor('white')
    ax_tbl.axis('off')
    ax_tbl.set_title("Modelos del ensamble", fontsize=11,
                      fontweight='bold', color=OLIVE, pad=6, loc='left')

    col_labels = ["Modelo", "Empresa", "Params", "Errores", "Tasa"]
    table_data = [[r[0], r[1], r[2], r[3], r[4]] for r in model_rows]

    tbl = ax_tbl.table(
        cellText=table_data,
        colLabels=col_labels,
        loc='center', cellLoc='center',
        bbox=[0, 0.05, 1, 0.82],
    )
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(10)

    for j in range(len(col_labels)):
        tbl[0, j].set_facecolor(OLIVE)
        tbl[0, j].set_text_props(color='white', fontweight='bold')
        tbl[0, j].set_edgecolor('white')
    for i in range(1, len(table_data)+1):
        for j in range(len(col_labels)):
            tbl[i, j].set_facecolor(OLIVE_BG if i%2==1 else 'white')
            tbl[i, j].set_edgecolor('#CCCC88')
            tbl[i, j].set_height(0.22)

    # ── Bar chart ──────────────────────────────────────────────────────────
    ax_bar.set_facecolor('white')
    y_pos = np.arange(n_bars)
    bars  = ax_bar.barh(y_pos, pcts, color=clrs,
                        height=0.55, edgecolor='white', linewidth=1.2)

    for bar, p in zip(bars, pcts):
        ax_bar.text(bar.get_width() + 0.3,
                    bar.get_y() + bar.get_height()/2,
                    f'{p:.1f}%',
                    va='center', ha='left',
                    fontsize=13, fontweight='bold', color='#222222')

    ax_bar.set_yticks(y_pos)
    ax_bar.set_yticklabels(lbls, fontsize=14, fontweight='bold')
    ax_bar.set_xlabel('Porcentaje de reseñas etiquetadas (%)', fontsize=12)
    ax_bar.set_xlim(0, max(pcts)*1.22)
    ax_bar.set_title("Distribución de votos del ensamble",
                     fontsize=13, fontweight='bold', pad=10)
    ax_bar.tick_params(axis='x', labelsize=11)
    ax_bar.tick_params(axis='y', length=0)
    ax_bar.xaxis.grid(True, color='#DDDDDD', linestyle='--', linewidth=0.8)
    ax_bar.set_axisbelow(True)
    ax_bar.spines[['top','right','left']].set_visible(False)
    ax_bar.spines['bottom'].set_color('#BBBBBB')

    plt.savefig(out, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print(f"  -> {out}")


make_chart(
    "/Users/emiliano/Desktop/slide_5clases_v4.png",
    "Resultados del etiquetado ensamble  ·  Experimento A — 5 clases",
    v5, c5,
    order  = ['bueno','muy bueno','neutral','malo','muy malo'],
    labels = {'bueno':'Bueno','muy bueno':'Muy bueno','neutral':'Neutral',
               'malo':'Malo','muy malo':'Muy malo'},
    colors = {'bueno':'#5A8E30','muy bueno':'#2E6020',
               'neutral':'#B8971F','malo':'#E53935','muy malo':'#B71C1C'},
    model_rows = [
        ("gemma2:9b",  "Google",     "9 B",   "—", "—"),
        ("mistral:7b", "Mistral AI", "7 B",   "—", "—"),
        ("llama3.2",   "Meta",       "3.2 B", "—", "—"),
    ],
    hours="~48",
)

make_chart(
    "/Users/emiliano/Desktop/slide_3clases_v4.png",
    "Resultados del etiquetado ensamble  ·  Experimento B — 3 clases",
    v3, c3,
    order  = ['positivo','neutral','negativo'],
    labels = {'positivo':'Positivo','neutral':'Neutral','negativo':'Negativo'},
    colors = {'positivo':'#2E7D32','neutral':'#B8971F','negativo':'#C62828'},
    model_rows = [
        ("qwen2.5:1.5b", "Alibaba",   "1.5 B", "54",  "0.09%"),
        ("gemma2:2b",    "Google",    "2.6 B",  "16",  "0.03%"),
        ("phi4-mini",    "Microsoft", "3.8 B",  "20",  "0.03%"),
    ],
    hours="~26",
)

print("Listo.")
