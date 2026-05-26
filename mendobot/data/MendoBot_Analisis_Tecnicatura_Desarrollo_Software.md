# Análisis Académico y Técnico - Tecnicatura Universitaria en Desarrollo de Software

Este documento consolida la información académica, administrativa y técnica extraída del material proporcionado sobre la carrera Tecnicatura Universitaria en Desarrollo de Software y su integración potencial dentro del sistema de inteligencia artificial institucional MendoBot.

## 1. Información General de la Carrera

- Nombre: Tecnicatura Universitaria en Desarrollo de Software
- Duración: 3 años
- Modalidad: Presencial
- Horario: Lunes a viernes de 18:00 a 22:00 hs
- Estado de inscripción: Abierta

## 2. Objetivos Formativos

- Producir software utilizando lenguajes y herramientas de alto nivel
- Modificar y mantener programas informáticos
- Evaluar y seleccionar lenguajes de programación
- Seleccionar arquitecturas de software
- Integrar equipos de desarrollo de software

## 3. Cursillo Preuniversitario

- Inicio: Febrero 2026
- Cierre: Marzo 2026
- Examen final: Nivelatorio
- Modalidad: Presencial obligatoria

## 4. Información Económica

- Pago obligatorio del cursillo preuniversitario
- 12 cuotas mensuales consecutivas desde marzo a febrero
- Matrícula anual equivalente al valor de una cuota
- Pago de matrícula: 50% en junio y 50% en noviembre

## 5. Documentación Requerida

- Fotocopia del DNI
- Partida de nacimiento actualizada
- Fotocopia legalizada del certificado analítico
- Constancia provisoria o constancia de alumno regular

## 6. Perfil Profesional Inferido

- Desarrollador backend
- Desarrollador frontend
- Programador full stack
- Tester QA
- Analista junior
- Soporte técnico
- Desarrollo mobile

## 7. Competencias Técnicas Inferidas

- Programación orientada a objetos
- Algoritmos y estructuras de datos
- Bases de datos
- Ingeniería de software
- Testing
- Arquitectura de software

## 8. Integración con MendoBot

- Indexación semántica mediante ChromaDB
- Procesamiento RAG
- Extracción automática de PDFs
- Embeddings semánticos
- Consultas académicas automatizadas

## 9. Pipeline RAG de MendoBot

Usuario → Pregunta → Embedding → Búsqueda Vectorial → Recuperación de Contexto → Prompt Contextual → LLM Local → Respuesta Final

## 10. Stack Tecnológico de MendoBot

- Backend: FastAPI
- LLM Local: Ollama
- Embeddings: sentence-transformers
- Vector Database: ChromaDB
- Speech To Text: Whisper
- Text To Speech: Piper
- Frontend: React
- Avatar: Three.js
- Persistencia: PostgreSQL

## 11. Endpoints API previstos

- /api/chat
- /api/voice
- /api/search
- /api/upload
- /api/history
- /api/metrics
- /api/health

## 12. Conclusión

La información académica suministrada puede ser integrada directamente dentro del sistema MendoBot mediante embeddings semánticos y procesamiento RAG, permitiendo construir un asistente conversacional institucional inteligente, offline y completamente basado en tecnologías open-source.
