import json, pandas as pd
from pathlib import Path

with open('/Users/emiliano/Desktop/Proyecto de Tesis/datos/resultados/etiquetado/semillas_etiquetadas_3clases.json') as f:
    data = json.load(f)

df = pd.DataFrame(data)
df['n_palabras'] = df['text'].str.split().str.len()
df['n_chars']    = df['text'].str.len()

# Proporciones ajustadas: suman 333 por clase
# neutral tiene conc=0.33; positivo/negativo no
props = {
    'neutral':  [(1.0, 133), (0.6667, 166), (0.3333, 34)],
    'positivo': [(1.0, 133), (0.6667, 200)],
    'negativo': [(1.0, 133), (0.6667, 200)],
}

partes = []
for clase, allocs in props.items():
    df_clase = df[df['voto_ensamble'] == clase]
    total = 0
    for conc, n in allocs:
        sub = df_clase[df_clase['concordancia'] == conc]
        muestra = sub.sample(n, random_state=42)
        partes.append(muestra)
        total += n
        label = {1.0: 'fácil', 0.6667: 'intermedio', 0.3333: 'difícil'}[conc]
        print(f'[{clase}] conc={conc} ({label}): pool={len(sub):,}  muestra={n}')
    print(f'[{clase}] subtotal={total}\n')

gold = pd.concat(partes).sample(frac=1, random_state=42).reset_index(drop=True)

print(f'Total gold standard: {len(gold)} reseñas')
print()
print('Clase × concordancia:')
print(pd.crosstab(gold['voto_ensamble'], gold['concordancia']))

def get_labels(row):
    ets = row.get('etiquetas', {})
    if isinstance(ets, dict):
        return ets.get('qwen2.5:1.5b',''), ets.get('gemma2:2b',''), ets.get('phi4-mini','')
    return '', '', ''

labels_llm = [get_labels(r) for r in gold.to_dict('records')]
q, g, p = zip(*labels_llm)

csv_final = pd.DataFrame({
    'id':              gold.index,
    'idx_original':    gold['idx'].values,
    'rating':          gold['rating_orig'].values,
    'text':            gold['text'].values,
    'n_palabras':      gold['n_palabras'].values,
    'n_chars':         gold['n_chars'].values,
    'qwen2.5_1.5b':    q,
    'gemma2_2b':       g,
    'phi4_mini':       p,
    'voto_ensamble':   gold['voto_ensamble'].values,
    'concordancia':    gold['concordancia'].values,
    'etiqueta_humano': '',
    'notas_humano':    '',
})

out = Path('/Users/emiliano/Desktop/Proyecto de Tesis/datos/resultados/etiquetado/muestra_999_estratificada.csv')
csv_final.to_csv(out, index=False, encoding='utf-8-sig')
print(f'\nGuardado: {out}')
print(f'Tamaño: {out.stat().st_size // 1024} KB')
