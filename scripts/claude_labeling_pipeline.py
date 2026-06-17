"""
Claude Sonnet 4.6 — Pipeline de etiquetado para tesis
======================================================
3 usos:
  1. sample    → extrae gold_standard (333×3) + casos_dificiles (100)
  2. label     → etiqueta con Claude API en lotes
  3. errors    → extrae 100 desacuerdos Claude vs ensemble

Uso:
  python claude_labeling_pipeline.py sample
  python claude_labeling_pipeline.py label   --input gold_standard.jsonl   --output gold_standard_claude.jsonl
  python claude_labeling_pipeline.py label   --input casos_dificiles.jsonl --output casos_dificiles_claude.jsonl
  python claude_labeling_pipeline.py errors  --labeled gold_standard_claude.jsonl casos_dificiles_claude.jsonl
"""

import json
import random
import argparse
import time
from pathlib import Path
from collections import defaultdict

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE    = Path("/Users/emiliano/Desktop/Proyecto de Tesis")
SOURCE  = BASE / "datos/resultados/etiquetado/pipeline_llm/semillas_etiquetadas_3clases.json"
OUT_DIR = BASE / "datos/resultados/etiquetado/pruebas_claude"
OUT_DIR.mkdir(parents=True, exist_ok=True)

GOLD_OUT    = OUT_DIR / "gold_standard_sample.jsonl"
DIFICIL_OUT = OUT_DIR / "casos_dificiles_sample.jsonl"
ERRORS_OUT  = OUT_DIR / "analisis_errores.jsonl"

RANDOM_SEED   = 42
GOLD_PER_CLASS = 333
DIFICIL_N      = 100
ERRORS_N       = 100

# Clases válidas (tal como aparecen en los datos)
VALID_CLASSES = {"positivo", "negativo", "neutral"}

# ── STEP 1: SAMPLE ────────────────────────────────────────────────────────────

def sample():
    """Extrae gold_standard y casos_dificiles desde el checkpoint completo."""
    random.seed(RANDOM_SEED)

    high_conc   = defaultdict(list)   # concordancia == 1.0, indexado por clase
    low_conc    = []                   # concordancia < 1.0

    print(f"Leyendo {SOURCE} ...")
    with open(SOURCE) as f:
        for line in f:
            r = json.loads(line)
            clase = r.get("voto_ensamble")
            conc  = r.get("concordancia", 0)
            if clase not in VALID_CLASSES:
                continue
            if conc == 1.0:
                high_conc[clase].append(r)
            else:
                low_conc.append(r)

    # ── Gold standard: 333 por clase, alta concordancia ──
    print("\nGold standard (concordancia = 1.0):")
    gold = []
    for clase in sorted(VALID_CLASSES):
        pool = high_conc[clase]
        n    = min(GOLD_PER_CLASS, len(pool))
        sampled = random.sample(pool, n)
        print(f"  {clase}: {len(pool)} disponibles → {n} seleccionados")
        gold.extend(sampled)

    random.shuffle(gold)
    with open(GOLD_OUT, "w") as f:
        for r in gold:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"\nGuardado: {GOLD_OUT} ({len(gold)} registros)")

    # ── Casos difíciles: 100 con baja concordancia ──
    print(f"\nCasos difíciles (concordancia < 1.0): {len(low_conc)} disponibles")
    dificiles = random.sample(low_conc, min(DIFICIL_N, len(low_conc)))

    # Mostrar distribución de patrones de desacuerdo
    from collections import Counter
    patrones = Counter()
    for r in dificiles:
        votos = sorted(set(v["etiqueta"] for v in r["etiquetas"].values() if "etiqueta" in v))
        patrones["↔".join(votos)] += 1
    print("  Patrones de desacuerdo en la muestra:")
    for pat, cnt in patrones.most_common():
        print(f"    {pat}: {cnt}")

    with open(DIFICIL_OUT, "w") as f:
        for r in dificiles:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"Guardado: {DIFICIL_OUT} ({len(dificiles)} registros)")


# ── STEP 2: LABEL ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """Eres un experto en análisis de sentimiento de reseñas de productos Amazon en inglés.
Clasifica cada reseña en exactamente una de estas tres clases:
- positivo: experiencia favorable, satisfacción, recomendación
- negativo: experiencia desfavorable, queja, decepción, fallo del producto
- neutral: experiencia mixta, ambigua, sin información suficiente, o solo descriptiva sin valoración clara

Responde SOLO con JSON válido, sin texto adicional. Formato exacto:
{"etiqueta": "<positivo|negativo|neutral>", "justificacion": "<1 oración concisa en español>"}"""

def build_batch_prompt(records):
    """Construye prompt para un lote de registros."""
    lines = []
    for i, r in enumerate(records):
        text = r["text"].replace("\n", " ").strip()[:500]
        rating = r.get("rating_orig", "?")
        lines.append(f"[{i}] Rating: {rating}/5 | Reseña: {text}")
    batch_text = "\n".join(lines)

    return f"""Clasifica las siguientes {len(records)} reseñas.
Responde con un array JSON con exactamente {len(records)} objetos, uno por reseña, en el mismo orden.
Formato: [{{"etiqueta": "...", "justificacion": "..."}}, ...]

Reseñas:
{batch_text}"""

def label(input_path: str, output_path: str, batch_size: int = 20):
    """Etiqueta un JSONL con Claude API en lotes."""
    try:
        import anthropic
    except ImportError:
        print("ERROR: instala anthropic → pip install anthropic")
        return

    client = anthropic.Anthropic()  # usa ANTHROPIC_API_KEY del env

    records = []
    with open(input_path) as f:
        for line in f:
            records.append(json.loads(line))

    print(f"Etiquetando {len(records)} registros en lotes de {batch_size}...")
    print(f"Modelo: claude-sonnet-4-6")

    results = []
    errors  = []
    total_input_tokens  = 0
    total_output_tokens = 0

    for batch_start in range(0, len(records), batch_size):
        batch = records[batch_start : batch_start + batch_size]
        batch_prompt = build_batch_prompt(batch)

        attempt = 0
        success = False
        while attempt < 3 and not success:
            try:
                resp = client.messages.create(
                    model="claude-sonnet-4-6",
                    max_tokens=2048,
                    system=SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": batch_prompt}],
                )
                total_input_tokens  += resp.usage.input_tokens
                total_output_tokens += resp.usage.output_tokens

                raw = resp.content[0].text.strip()
                # Limpiar posibles bloques de código markdown
                if raw.startswith("```"):
                    raw = raw.split("```")[1]
                    if raw.startswith("json"):
                        raw = raw[4:]
                labels = json.loads(raw)

                if not isinstance(labels, list) or len(labels) != len(batch):
                    raise ValueError(f"Esperaba {len(batch)} etiquetas, recibí {len(labels)}")

                for record, label_data in zip(batch, labels):
                    out = {
                        "idx":         record["idx"],
                        "parent_asin": record["parent_asin"],
                        "asin":        record["asin"],
                        "user_id":     record["user_id"],
                        "rating_orig": record.get("rating_orig"),
                        "text":        record["text"],
                        "voto_ensamble_original": record.get("voto_ensamble"),
                        "concordancia_original":  record.get("concordancia"),
                        "etiqueta_claude": label_data.get("etiqueta"),
                        "justificacion_claude": label_data.get("justificacion"),
                    }
                    results.append(out)

                success = True
                print(f"  Lote {batch_start//batch_size + 1}/{(len(records)-1)//batch_size + 1} ✓ "
                      f"({batch_start + len(batch)}/{len(records)})")

            except Exception as e:
                attempt += 1
                print(f"  Lote {batch_start//batch_size + 1} — error (intento {attempt}/3): {e}")
                if attempt < 3:
                    time.sleep(5 * attempt)
                else:
                    print(f"  ⚠ Lote fallido, guardando con error")
                    for record in batch:
                        out = {
                            "idx":         record["idx"],
                            "error":       str(e),
                            "voto_ensamble_original": record.get("voto_ensamble"),
                        }
                        results.append(out)
                        errors.append(record["idx"])

        # Pausa entre lotes para no saturar rate limit
        time.sleep(1)

    # Guardar resultados
    with open(output_path, "w") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"\n✅ Guardado: {output_path}")
    print(f"   Registros: {len(results)} | Errores: {len(errors)}")
    print(f"   Tokens — input: {total_input_tokens:,} | output: {total_output_tokens:,}")
    est_cost = total_input_tokens/1e6 * 3 + total_output_tokens/1e6 * 15
    print(f"   Costo estimado: ${est_cost:.4f} USD")
    if errors:
        print(f"   IDX con error: {errors}")


# ── STEP 3: ERRORS ────────────────────────────────────────────────────────────

def extract_errors(labeled_paths: list, n: int = ERRORS_N):
    """Extrae registros donde Claude difiere del voto_ensamble original."""
    all_records = []
    for path in labeled_paths:
        with open(path) as f:
            for line in f:
                r = json.loads(line)
                if "etiqueta_claude" not in r or "error" in r:
                    continue
                all_records.append(r)

    disagreements = [
        r for r in all_records
        if r["etiqueta_claude"] != r["voto_ensamble_original"]
        and r["etiqueta_claude"] in VALID_CLASSES
    ]

    print(f"Total etiquetados: {len(all_records)}")
    print(f"Desacuerdos Claude vs ensemble: {len(disagreements)} ({len(disagreements)/len(all_records)*100:.1f}%)")

    if not disagreements:
        print("Sin desacuerdos — no hay errores que extraer.")
        return

    # Mostrar matriz de confusión simplificada
    from collections import Counter
    matrix = Counter(
        (r["voto_ensamble_original"], r["etiqueta_claude"])
        for r in disagreements
    )
    print("\nMatriz de desacuerdos (ensemble → Claude):")
    for (ens, claude), cnt in sorted(matrix.items(), key=lambda x: -x[1]):
        print(f"  {ens} → {claude}: {cnt}")

    # Muestra estratificada por tipo de desacuerdo
    random.seed(RANDOM_SEED)
    by_type = defaultdict(list)
    for r in disagreements:
        key = (r["voto_ensamble_original"], r["etiqueta_claude"])
        by_type[key].append(r)

    sampled = []
    n_types  = len(by_type)
    per_type = max(1, n // n_types)

    for key, recs in by_type.items():
        take = min(per_type, len(recs))
        sampled.extend(random.sample(recs, take))

    # Si faltan hasta n, rellenar aleatoriamente del total
    if len(sampled) < n:
        remaining = [r for r in disagreements if r not in sampled]
        sampled.extend(random.sample(remaining, min(n - len(sampled), len(remaining))))

    sampled = sampled[:n]
    random.shuffle(sampled)

    with open(ERRORS_OUT, "w") as f:
        for r in sampled:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"\n✅ Guardado: {ERRORS_OUT} ({len(sampled)} registros)")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Claude labeling pipeline")
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("sample", help="Extrae gold_standard y casos_dificiles")

    p_label = sub.add_parser("label", help="Etiqueta con Claude API")
    p_label.add_argument("--input",  required=True)
    p_label.add_argument("--output", required=True)
    p_label.add_argument("--batch",  type=int, default=20)

    p_err = sub.add_parser("errors", help="Extrae desacuerdos Claude vs ensemble")
    p_err.add_argument("--labeled", nargs="+", required=True,
                       help="Archivos JSONL ya etiquetados por Claude")

    args = parser.parse_args()

    if args.cmd == "sample":
        sample()
    elif args.cmd == "label":
        label(args.input, args.output, args.batch)
    elif args.cmd == "errors":
        extract_errors(args.labeled)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
