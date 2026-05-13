Fase 2: Ingeniería de Requerimientos - MendoBot
ID del Documento: SPEC-REQ-02
Trazabilidad: Deriva de SPEC-ANALYSIS-01
1. Requerimientos Funcionales (RF)
Mínimo 8 requerimientos obligatorios:
RF-01: El sistema debe responder consultas sobre la oferta académica de la institución.
RF-02: El sistema debe proporcionar detalles de los planes de estudio (materias, duración).
RF-03: El sistema debe informar sobre la modalidad de cursado (presencial/virtual).
RF-04: El sistema debe dar información sobre la ubicación y contacto de las sedes (ej. Río Cuarto).
RF-05: El sistema debe permitir la interacción mediante comandos de voz (Web Speech API).
RF-06: El sistema debe contar con un avatar 3D que se anime al responder.
RF-07: El sistema debe permitir rotar la vista del bot para pantallas verticales.
RF-08: El sistema debe mantener una terminal abierta para estar disponible como servicio local.
2. Requerimientos No Funcionales (RNF)
Mínimo 6 requerimientos obligatorios:
RNF-01 (Rendimiento): El tiempo de respuesta debe ser menor a 3 segundos para el 95% de las consultas.
RNF-02 (Usabilidad): La interfaz conversacional debe ser clara, accesible y legible.
RNF-03 (Disponibilidad): El sistema debe garantizar un uptime del 98% en horario de consulta.
RNF-04 (Seguridad): Protección de datos personales de los usuarios según normativas vigentes.
RNF-05 (Mantenibilidad): El código debe ser modular y estar documentado internamente.
RNF-06 (Portabilidad): El sistema debe ser compatible con entornos de ejecución estándar (Python/Node.js).
3. Criterios de Aceptación Globales
El bot debe responder correctamente al menos al 80% del set de preguntas de prueba.
Cada historia de usuario debe tener al menos dos criterios validables en formato Given/When/Then.
