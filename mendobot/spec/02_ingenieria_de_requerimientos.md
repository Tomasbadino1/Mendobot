# Fase 2: Ingeniería de Requerimientos — MendoBot

**ID del Documento:** SPEC-REQ-02  
**Trazabilidad:** Deriva de SPEC-ANALYSIS-01  
**Fuentes de datos de referencia:** `data/Folleto_informativo.md`, `data/info_administrativa.md`, `data/knowledge_base.json`

---

## 1. Requerimientos Funcionales (RF)

Mínimo 8 requerimientos obligatorios.

### RF-01: Oferta académica

**Enunciado:** El sistema debe responder consultas sobre la oferta académica de la institución.

**Criterios de Aceptación**

- **CA-01.1**

  - **Dado** que el usuario consulta sobre la propuesta o la oferta de la carrera.

  - **Cuando** pregunta de qué se trata la Tecnicatura en Desarrollo de Software o cuál es la propuesta académica.

  - **Entonces** el sistema responde con información sobre la formación en desarrollo de software, los objetivos formativos (producir software, mantener programas, evaluar lenguajes y arquitecturas) y la integración en equipos de desarrollo

- **CA-01.2**

  - **Dado** que el usuario solicita el título que otorga la institución.

  - **Cuando** pregunta qué título recibe el egresado.

  - **Entonces** el sistema indica que el título otorgado es **Tecnicatura Universitaria en Desarrollo de Software**.

- **CA-01.3**

  - **Dado** que el usuario consulta la salida laboral o el perfil profesional.

  - **Cuando** pregunta en qué puede trabajar un egresado.

  - **Entonces** el sistema menciona roles como desarrollador backend/frontend, programador Full Stack, Tester QA, analista junior, soporte técnico o desarrollo mobile.

- **CA-01.4**

  - **Dado** que el usuario consulta si la carrera aborda inteligencia artificial.

  - **Cuando** pregunta si se aprende o integra IA en la formación.

  - **Entonces** el sistema responde de forma afirmativa que la carrera está orientada a integrar herramientas de IA en soluciones reales y optimizar software de alto nivel.

---

### RF-02: Plan de estudios

**Enunciado:** El sistema debe proporcionar detalles de los planes de estudio (materias, duración).

**Criterios de Aceptación**

- **CA-02.1**

  - **Dado** que la base de conocimiento contiene el plan por años (primer, segundo y tercer año).

  - **Cuando** el usuario solicita el **plan de estudios completo**.

  - **Entonces** el sistema lista todas las materias de los tres años agrupadas por año, sin una respuesta genérica que solo remita a “pedir el plan”.

- **CA-02.2**

  - **Dado** que el plan del primer año incluye Matemática Discreta y Diseño Lógico, Álgebra y Geometría Analítica, Inglés Técnico, Informática y Análisis de Sistemas I.

  - **Cuando** el usuario pregunta las materias del **primer año**.

  - **Entonces** el sistema devuelve exclusivamente las materias correspondientes a ese año.

- **CA-02.3**

  - **Dado** que el plan del segundo año incluye, entre otras, Computación I y Diseño de Base de Datos I.

  - **Cuando** el usuario pregunta las materias del **segundo año** o si se estudia programación/computación en segundo.

  - **Entonces** el sistema devuelve las materias del segundo año (incluyendo Computación I cuando corresponda semánticamente).

- **CA-02.4**

  - **Dado** que la carrera tiene una duración oficial de 3 años según el folleto y la información administrativa.

  - **Cuando** el usuario pregunta cuánto dura la carrera.

  - **Entonces** el sistema responde que la duración es de **3 años**.

---

### RF-03: Modalidad de cursado

**Enunciado:** El sistema debe informar sobre la modalidad de cursado (presencial/virtual).

**Criterios de Aceptación**

- **CA-03.1**

  - **Dado** que la modalidad oficial de la carrera es **presencial**.

  - **Cuando** el usuario pregunta si la carrera es presencial o virtual.

  - **Entonces** el sistema indica que la modalidad es **presencial** y aclara que no está pensada como cursado 100 % virtual u online.

- **CA-03.2**

  - **Dado** que el horario de cursada es de lunes a viernes de **18:00 a 22:00 hs**.

  - **Cuando** el usuario pregunta en qué horario se cursan las materias o si debe asistir todos los días.

  - **Entonces** el sistema informa el rango horario y que la formación presencial implica asistencia en la franja indicada de lunes a viernes.

- **CA-03.3**

  - **Dado** que el cursillo preuniversitario tiene modalidad **presencial obligatoria**.

  - **Cuando** el usuario consulta la modalidad del cursillo de ingreso.

  - **Entonces** el sistema responde que el cursillo es presencial y de carácter obligatorio.

---

### RF-04: Sedes y ubicación

**Enunciado:** El sistema debe dar información sobre la ubicación y contacto de las sedes (ej. Río Cuarto).

**Criterios de Aceptación**

- **CA-04.1**

  - **Dado** que la carrera se dicta en la **Sede Río Cuarto** según la base de conocimiento institucional.

  - **Cuando** el usuario pregunta dónde se dicta la carrera, en qué sede queda o cuál es el lugar de cursada.

  - **Entonces** el sistema indica que la Tecnicatura se dicta en la **Sede Río Cuarto**.

- **CA-04.2**

  - **Dado** que la institución es la **Universidad de Mendoza**.

  - **Cuando** el usuario consulta la sede o ubicación de la universidad.

  - **Entonces** el sistema contextualiza la respuesta en la Universidad de Mendoza y la sede de dictado (Río Cuarto).

- **CA-04.3**

  - **Dado** que el usuario necesita datos de contacto o dirección exacta no almacenados en el JSON.

  - **Cuando** solicita domicilio, teléfono o contacto detallado de la sede.

  - **Entonces** el sistema provee la información de sede disponible y orienta a consultar los canales oficiales de la institución para datos de contacto actualizados.

---

### RF-05: Interacción por voz

**Enunciado:** El sistema debe permitir la interacción mediante comandos de voz (Web Speech API).

**Criterios de Aceptación**

- **CA-05.1**

  - **Dado** que el usuario accede a la interfaz con soporte de voz habilitado.

  - **Cuando** activa el micrófono y formula una consulta hablada sobre la carrera.

  - **Entonces** el sistema transcribe la consulta y procesa la respuesta con la misma lógica que una consulta escrita.

- **CA-05.2**

  - **Dado** que la consulta por voz fue comprendida correctamente.

  - **Cuando** el motor genera una respuesta válida.

  - **Entonces** el sistema presenta la respuesta al usuario (texto y/o síntesis de voz, según la implementación de la interfaz).

- **CA-05.3**

  - **Dado** que el navegador no soporta o el usuario deniega permisos de micrófono.

  - **Cuando** intenta usar el comando de voz.

  - **Entonces** el sistema informa que la entrada por voz no está disponible y permite continuar por texto sin bloquear el servicio.

---

### RF-06: Avatar 3D

**Enunciado:** El sistema debe contar con un avatar 3D que se anime al responder.

**Criterios de Aceptación**

- **CA-06.1**

  - **Dado** que la interfaz del bot está visible con el avatar 3D cargado.

  - **Cuando** el sistema entrega una respuesta exitosa a una consulta del usuario.

  - **Entonces** el avatar ejecuta una animación de respuesta acorde al evento configurado.

- **CA-06.2**

  - **Dado** que la consulta no produce una respuesta válida (excepción CU-01 E1).

  - **Cuando** el sistema no encuentra información en la base de conocimiento.

  - **Entonces** el avatar no simula una respuesta exitosa o utiliza una animación diferenciada de error, según el diseño de la interfaz.

- **CA-06.3**

  - **Dado** que el usuario realiza una nueva consulta mientras el avatar está animándose.

  - **Cuando** llega un nuevo mensaje del motor.

  - **Entonces** la interfaz completa la transición sin bloquear la interacción textual del usuario.

---

### RF-07: Rotación de interfaz

**Enunciado:** El sistema debe permitir rotar la vista del bot para pantallas verticales.

**Criterios de Aceptación**

- **CA-07.1**

  - **Dado** que la interfaz se muestra en una pantalla en orientación vertical.

  - **Cuando** el usuario presiona el control de rotación del layout.

  - **Entonces** el sistema ajusta la disposición de los elementos y del avatar para visualización vertical.

- **CA-07.2**

  - **Dado** que la interfaz fue rotada a modo vertical.

  - **Cuando** el usuario vuelve a presionar el control de rotación.

  - **Entonces** el sistema restaura el layout a la orientación anterior sin pérdida de contexto de la conversación.

- **CA-07.3**

  - **Dado** que existe contenido de chat activo en pantalla.

  - **Cuando** se ejecuta la rotación.

  - **Entonces** los mensajes y el área de entrada permanecen legibles y usables tras el cambio de orientación.

---

### RF-08: Servicio local en terminal

**Enunciado:** El sistema debe mantener una terminal abierta para estar disponible como servicio local.

**Criterios de Aceptación**

- **CA-08.1**

  - **Dado** que el servicio MendoBot fue iniciado mediante `python main.py` en la consola.

  - **Cuando** el proceso queda en ejecución.

  - **Entonces** el sistema muestra un mensaje de bienvenida y acepta consultas en un bucle interactivo hasta que el usuario indique salir.

- **CA-08.2**

  - **Dado** que el servicio local está activo y la base `knowledge_base.json` es accesible.

  - **Cuando** el usuario ingresa una consulta válida.

  - **Entonces** el sistema responde utilizando `buscar_respuesta()` sin requerir un servidor externo para el MVP por consola.

- **CA-08.3**

  - **Dado** que el archivo de conocimiento no está disponible o está corrupto.

  - **Cuando** el usuario intenta consultar.

  - **Entonces** el sistema informa que el servicio local no puede recuperar la información (flujo de excepción CU-02 E1) en lugar de devolver datos inventados.

- **CA-08.4**

  - **Dado** que el usuario escribe `salir`, `exit` o `quit`.

  - **Cuando** confirma el cierre en la terminal.

  - **Entonces** el sistema finaliza el bucle y termina el servicio de forma ordenada.

---

## 2. Requerimientos No Funcionales (RNF)

Mínimo 6 requerimientos obligatorios:

| ID | Categoría | Enunciado |
|----|-----------|-----------|
| RNF-01 | Rendimiento | El tiempo de respuesta debe ser menor a 3 segundos para el 95 % de las consultas. |
| RNF-02 | Usabilidad | La interfaz conversacional debe ser clara, accesible y legible. |
| RNF-03 | Disponibilidad | El sistema debe garantizar un uptime del 98 % en horario de consulta. |
| RNF-04 | Seguridad | Protección de datos personales de los usuarios según normativas vigentes. |
| RNF-05 | Mantenibilidad | El código debe ser modular y estar documentado internamente. |
| RNF-06 | Portabilidad | El sistema debe ser compatible con entornos de ejecución estándar (Python/Node.js). |

---

## 3. Criterios de Aceptación Globales

- El bot debe responder correctamente al menos al **80 %** del set de preguntas de prueba definido para el MVP.

- Cada requerimiento funcional (RF-01 a RF-08) cuenta con al menos **dos criterios** validables en formato **Dado / Cuando / Entonces**.

- Las respuestas de RF-01 a RF-04 deben basarse exclusivamente en la información oficial cargada en `knowledge_base.json`, alineada con `Folleto_informativo.md` e `info_administrativa.md`.

- Ante consultas fuera del alcance del sistema (otras carreras, trámites administrativos complejos, integración con gestión de notas), el bot debe aplicar la excepción **CU-01 E1** y solicitar reformular la consulta, sin inventar información.
