"""
Merge respuestas exportadas de Google Forms → para_anotar_humano.csv

Uso:
  python merge_forms_responses.py <export.csv> [--parte N]

  --parte N  : número de parte (1-10). Si no se da, lo infiere del nombre del archivo.
               Parte 1 → filas 0-99, Parte 2 → filas 100-199, etc.

El export de Google Forms no incluye el idx en las columnas — solo pares posicionales:
  col 0: Marca temporal
  col 1+2N: Polaridad reseña N+1
  col 2+2N: Justificación reseña N+1  (N = 0-indexed)

Se mapea por posición: par N del export → fila (parte-1)*100 + N del CSV → idx.
"""

import csv
import sys
import re
import argparse
from pathlib import Path

CSV_PATH = Path(__file__).parent / "para_anotar_humano.csv"
RESEÑAS_POR_PARTE = 100

def inferir_parte(filename: str) -> int:
    m = re.search(r'[Pp]arte\s*(\d+)', filename)
    if m:
        return int(m.group(1))
    raise ValueError(f"No se pudo inferir el número de parte de '{filename}'. Usa --parte N.")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("export", help="CSV exportado de Google Forms")
    parser.add_argument("--parte", type=int, default=None)
    args = parser.parse_args()

    export_path = Path(args.export)
    parte = args.parte or inferir_parte(export_path.name)
    fila_inicio = (parte - 1) * RESEÑAS_POR_PARTE

    # Cargar export
    with open(export_path, encoding="utf-8-sig") as f:
        export_rows = list(csv.reader(f))

    if len(export_rows) < 2:
        print("El archivo export está vacío (solo encabezado).")
        sys.exit(1)

    encabezado_export = export_rows[0]
    respuestas = export_rows[1:]  # puede haber más de una fila si varias personas respondieron
    n_reseñas = (len(encabezado_export) - 1) // 2
    print(f"Export: {len(respuestas)} respuesta(s), {n_reseñas} reseñas por respuesta")
    print(f"Parte {parte} → filas CSV {fila_inicio}–{fila_inicio + n_reseñas - 1}")

    if len(respuestas) > 1:
        print("AVISO: hay más de una fila de respuestas. Se usará la ÚLTIMA (más reciente).")
    respuesta = respuestas[-1]

    # Cargar CSV principal
    with open(CSV_PATH, encoding="utf-8-sig", newline="") as f:
        csv_rows = list(csv.DictReader(f))

    total_filas = len(csv_rows)
    actualizados = 0
    conflictos = []

    for n in range(n_reseñas):
        fila_csv = fila_inicio + n
        if fila_csv >= total_filas:
            print(f"  AVISO: posición {n} sale del rango del CSV (fila {fila_csv} >= {total_filas})")
            break

        col_polaridad = 1 + n * 2
        col_justif   = 2 + n * 2

        polaridad   = respuesta[col_polaridad].strip() if col_polaridad < len(respuesta) else ""
        justif      = respuesta[col_justif].strip()    if col_justif    < len(respuesta) else ""

        row = csv_rows[fila_csv]
        idx_csv = row["idx"]

        if not polaridad:
            continue  # pregunta sin responder

        etiqueta_actual = row.get("etiqueta_humano", "").strip()
        if etiqueta_actual and etiqueta_actual != polaridad:
            conflictos.append(f"  fila {fila_csv} idx={idx_csv}: '{etiqueta_actual}' → '{polaridad}' (sobreescribiendo)")

        row["etiqueta_humano"] = polaridad
        row["notas_humano"]    = justif
        actualizados += 1

    # Escribir CSV actualizado
    fieldnames = ["idx", "text", "etiqueta_humano", "notas_humano"]
    with open(CSV_PATH, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(csv_rows)

    print(f"\nActualizados: {actualizados} filas")
    if conflictos:
        print(f"Conflictos sobreescritos ({len(conflictos)}):")
        for c in conflictos:
            print(c)
    print("Listo.")

if __name__ == "__main__":
    main()
