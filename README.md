# Análisis de sentimiento en reseñas de Amazon

Tesis de maestría (MCID, UAT). El objetivo es clasificar el sentimiento de reseñas de productos agrícolas de Amazon en tres clases: positivo, neutro y negativo. El enfoque etiqueta el corpus con un ensamble de tres LLMs y luego entrena clasificadores clásicos supervisados sobre esas etiquetas.

El dataset es de la categoría *Patio, Lawn & Garden* (Amazon, 2023), en inglés. Los CSVs originales superan 1 GB y se excluyen del repo.

## Estructura

```
├── notebooks/
│   ├── clasificacion/     # Clasificadores TF-IDF y Word2Vec
│   ├── etiquetado/        # Análisis de distribución y gold standard
│   └── _referencia/       # Pipelines históricos
├── scripts/               # Pipelines de etiquetado y generación de datos
├── datos/
│   ├── procesados/        # Dataset principal (excluido por tamaño)
│   └── resultados/        # Métricas, etiquetado y unificación
├── ANOTAR/                # Scripts Google Apps Script para anotación humana
├── demo_fic/              # Demo interactiva con Gradio (3 LLMs)
├── materia_topicos/       # Notebooks y datos de Tópicos Selectos
└── estancia/              # Scripts y recursos de estancia de investigación
```

## Stack

- Etiquetado: Claude API (Anthropic), ensamble de 3 modelos
- Clasificadores: scikit-learn (SVM, KNN, MLP, Naive Bayes), Word2Vec con Gensim
- Anotación humana: Google Forms via Apps Script
- Demo: Gradio
- Python 3.11, Jupyter, pandas, NumPy
