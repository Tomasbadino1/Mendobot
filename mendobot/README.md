# MendoBot

Estructura inicial del proyecto basada en Spec-Driven Development (SDD).

## Estructura

- `spec/`: documentos de especificación (fases 1 a 3).
- `src/engine.py`: lógica de procesamiento de consultas (CU-01).
- `src/data_manager.py`: carga de base de conocimiento en JSON.
- `data/knowledge_base.json`: carreras, FAQ y datos institucionales.
- `main.py`: punto de entrada local (RF-08).

## Ejecución

```bash
python main.py
```

## Estado actual

- Implementado flujo base de `CU-01`: consulta de información de carrera.
- Incluye manejo de excepción cuando la carrera no se encuentra.
