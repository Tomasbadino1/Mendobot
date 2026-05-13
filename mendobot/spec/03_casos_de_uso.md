Fase 3: Casos de Uso - MendoBot
ID del Documento: SPEC-CU-03
Trazabilidad: Basado en RF-01, RF-02, RF-05, RF-06, RF-07 y RF-08 de SPEC-REQ-02.

Matriz de Trazabilidad Bidireccional (RF <-> CU)
RF-01 <-> CU-01 (consulta de oferta/carrera)
RF-02 <-> CU-02 (consulta de plan de estudios)
RF-05 <-> CU-01.A1 (consulta por voz)
RF-06 <-> CU-01 (animacion de avatar al responder)
RF-07 <-> CU-03 (rotacion para pantalla vertical)
RF-08 <-> CU-02.E1 (disponibilidad de servicio local)

CU-01: Consultar Información de Carrera
Actor Principal: Aspirante.
Precondiciones: El sistema está activo y mostrando la interfaz del bot.
Flujo Principal:
El usuario ingresa una pregunta sobre una carrera específica (ej. "Háblame de Desarrollo de Software").
El sistema procesa la consulta semánticamente.
El sistema identifica la carrera en la base de conocimiento.
El bot responde con la descripción de la carrera y el avatar 3D se anima.
Flujos Alternativos:
A1 (Voz): El usuario usa el micrófono para hacer la consulta (RF-05).
Flujo de Excepción:
E1: Si la carrera no existe, el bot solicita reformular la pregunta con un mensaje claro.
Resultado Esperado: El usuario recibe información precisa sobre la carrera consultada.

CU-02: Consultar Plan de Estudios
Actor Principal: Alumno.
Precondiciones: El usuario ha identificado una carrera válida.
Flujo Principal:
El usuario solicita ver las materias o la duración de la carrera.
El sistema recupera el JSON de la base de conocimiento.
El bot detalla la lista de materias y duración total.
Flujo de Excepción:
E1: Si hay un error de conexión, el sistema informa que el servicio local no está disponible (RF-08).
Resultado Esperado: El usuario visualiza o escucha el plan de estudios completo.

CU-03: Rotación de Interfaz para Pantalla Vertical
Actor Principal: Administrador / Usuario general.
Flujo Principal:
El usuario detecta que la pantalla física está en posición vertical.
El usuario presiona el botón de rotación en la interfaz.
El sistema ajusta el layout y el avatar 3D para visualización vertical (RF-07).
Resultado Esperado: La interfaz se adapta correctamente al formato de pantalla sin errores visuales.
