# agente-tutor (v1): contexto completo

Documento para ponerse al día con el proyecto sin leer el código. v1 es el proyecto original, hecho a mano
en n8n. `../Agente Tutor v2` es una versión que otro LLM reescribió en Python (FastAPI). De ella se tomaron
lecciones para v1 sin cambiar su esencia: la orquestación sigue en n8n y Python solo vive en `rag/` y en
`latex-renderer`.

## Qué es

**Gaussito**, bot de Telegram para un tutor privado de matemáticas y estadística. Lo usa una sola persona,
en español, con pedidos rápidos y sueltos (sin memoria de conversación).

| Tarea | Salida |
|---|---|
| `plan_de_clases` | Plan de sesiones en Telegram, con las fuentes usadas |
| `banco_de_ejercicios` | Resumen en Telegram, con fuentes, y PDF compilado con LaTeX |
| `planificar_clase` | Evento en Google Calendar con enlace de Meet |
| `aclarar` | Pregunta breve de vuelta |

## Arquitectura (workflow `n8n/agente-tutor.json`)

```
Polling Timer (5 s) → getUpdates (limit=1) → Procesar Updates → Confirmar Offset → Extraer Info Mensaje
  → ¿adjunto? → getFile → Descargar → Extraer Texto PDF (primeros 4000 chars) → Procesar Archivo
  → Normalizar Datos
  → 🧭 Orquestador → Llamar Orquestador → Leer Orquestador            {tarea, consulta, mensaje}
  → ¿Necesita RAG? ─ sí → Embedding (bge-m3 de `consulta`) → Listar Colecciones → Preparar Query RAG
  │                        → Consultar ChromaDB (top-5, filtro por tipo) → Formatear Contexto RAG ─┐
  │                 └ no ───────────────────────────────────────────────────────────────────────────┤
  → Especialista ─┬ 📘 Planeador ─┐                                                                  ◄┘
                  ├ 📝 Ejercicios ┼→ Llamar Ollama → Parsear Respuesta LLM → Router de Tareas
                  ├ 📅 Agendador ─┘
                  └ aclarar → Formato Aclarar
  Router de Tareas → Formato Plan | Formato Ejercicios (+ Generar PDF → Enviar PDF)
                   | Validar Datos Clase → Google Calendar | Formato Error
  → Unir Respuestas → Dividir Mensaje Largo (4000) → Enviar Respuesta (Markdown)
```

- **Orquestador**: qwen3 con temperatura 0 y esquema `{tarea, consulta, mensaje}`. `consulta` es una
  búsqueda corta con solo los temas pedidos ("distribución normal"); buscar con ella, y no con el mensaje
  entero, es lo que más mejora el RAG.
- **Búsqueda**: solo para plan y ejercicios. Ejercicios filtra `tipo ∈ {ejercicios, evaluacion}`.
- **Especialistas**: nodos Code, cada uno con su prompt y su JSON Schema (sacados de v2 sin lo de idioma
  ni memoria). Los tres comparten `Llamar Ollama` (`/api/chat`, `think: false`, `num_ctx` 8192, hasta 4096
  tokens de salida, temperatura 0.2; el Agendador usa 0).
- **Agendador**: recibe en el prompt los próximos 14 días con su día de la semana (America/Bogota).
- **Parsear Respuesta LLM**: toma `tarea` y fuentes del Orquestador; mantiene el reparador de JSON truncado
  de siempre; corrige el LaTeX que el LLM rompe al escapar (`\frac` llega como salto de página + "rac"); si
  hay `dia_semana`, calcula la fecha: siempre la próxima ocurrencia, nunca hoy (para hoy se dice "hoy").
- **Validar Datos Clase**: exige estudiante, fecha y hora; si falta la modalidad asume virtual y la
  confirmación dice "virtual (asumida)".
- Las fuentes se muestran como `` `archivo p.N` `` para que los `_` no rompan el Markdown de Telegram.

## Servicios (`docker-compose.yml`, proyecto `tutor`)

| Servicio | Puerto | Detalle |
|---|---|---|
| n8n | 5678 | lee `.env`, TZ America/Bogota, `N8N_BLOCK_ENV_ACCESS_IN_NODE=false`, datos en `n8n-data/` |
| chromadb | 8000 | colección `tutorias` (bge-m3, 1024 dims, coseno), en `chroma-data/` |
| latex-renderer | 5001 | Flask + Tectonic (traído de v2). `POST /render {nivel, temas[]}` → PDF; si la matemática no compila, reintenta con ella como texto. Dificultad desconocida → "Media" |
| Ollama | 11434 (host) | `qwen3:14b`, `bge-m3` |

`.env`: `TELEGRAM_BOT_TOKEN`, `GOOGLE_CALENDAR_ID`, `COLECCION=tutorias`, `LLM_MODEL=qwen3:14b`.
La credencial de Google Calendar se conecta a mano en n8n. v1 y v2 usan los mismos puertos: solo uno a la vez.

## Base vectorial y RAG (`rag/`)

`chroma-data/` es una **copia de la base de v2**: 621 fragmentos de 75 archivos en 10 tutorías, incluidos
escaneados y fotos transcritos con qwen3-vl. La base anterior (nomic-embed-text) está en `data/chroma-data-nomic/`.

Los scripts de `rag/` (lectura de PDF/DOCX/PPTX, cortes, deduplicación) siguen siendo los de v1, ahora con
`bge-m3` y sin prefijos. Reingestar con ellos (`--reset`) funciona, pero pierde lo transcrito por visión y la
detección de `tipo` por contenido que tiene la base de v2.

Evaluación (`uv run python -m rag.evaluar`, 25 preguntas de `rag/preguntas.yaml`, búsqueda vectorial top-5):

| Base | hit@5 | MRR@5 |
|---|---|---|
| nomic (v1 original) | 0.56 | 0.50 |
| bge-m3 (copiada de v2) | 0.80 | 0.66 |

Fallan todavía: ANOVA, chi-cuadrado, teorema de Bayes, distribución gamma y mínimo y máximo de una muestra.

## Tiempos medidos (RTX 5070, simulando el workflow nodo por nodo)

- Ejercicios (3, uno por dificultad): ~25-30 s en total, PDF incluido.
- Plan de 2 sesiones: ~32 s.
- Agendar o aclarar: 1-3 s.

## Limitaciones conocidas

- Con temas amplios ("probabilidad básica, 1 por nivel") el modelo divide en subtemas y genera más
  ejercicios de los esperados. Para evitarlo, pide un total ("3 ejercicios en total").
- Sin memoria: si al agendar falta el nombre, la fecha o la hora, hay que reenviar el pedido completo.
- Del adjunto solo se lee el texto de PDFs (no escaneados) y hasta 4000 caracteres.
- Búsqueda solo vectorial. La híbrida con reranker de v2 (Fase 3 del plan) queda pendiente de lo que diga
  la evaluación.

## Comandos

```
docker compose up -d --build
uv sync
uv run python -m rag.evaluar
uv run python -m rag.consultar "pregunta" -k 5 --tipo ejercicios
TUTORIAS_DIR=/ruta uv run python -m rag.ingestar [--dry-run] [--reset]
```

Tras cambiar el workflow hay que reimportar `n8n/agente-tutor.json` en http://localhost:5678.
