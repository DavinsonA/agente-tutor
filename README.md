<p align="center">
  <img src="assets/gaussito.jpg" alt="Gaussito" width="280">
</p>

# agente-tutor

**Gaussito**, bot de Telegram para tutorías de matemáticas y estadística: n8n + Ollama + ChromaDB.

```
cp .env.example .env
docker compose up -d --build
ollama pull qwen3:14b
ollama pull bge-m3
uv sync
TUTORIAS_DIR=/ruta/a/tutorias uv run python -m rag.ingestar
uv run python -m rag.evaluar
```

Importar `n8n/agente-tutor.json` en http://localhost:5678 y conectar las credenciales de Telegram y Google Calendar.

Un Orquestador decide la tarea y la pasa a su especialista (plan de clases, ejercicios o agenda); el plan y
los ejercicios llegan como PDF compilado con LaTeX.
