# Guía · Funnel de WhatsApp: estructura de estados para leads

Síntesis de [[19-aaron-ross]] (estados y métricas), [[15-russell-brunson]] (escalera de valor), [[18-chet-holmes]] (pirámide del comprador), [[10-david-sandler]] (calificación) y [[09-neil-rackham]] (avances). Adaptado al flujo real de una clínica estética por WhatsApp (DermicaPro: [[operacion]]).

Regla de Aaron Ross: cada estado necesita **criterio de entrada, criterio de salida y métrica**. Regla de Rackham: un lead solo cambia de estado con un **avance** (compromiso concreto), no con un "quedó buena onda".

> Las **señales concretas** que disparan cada transición (y cuándo dar el precio, el caso más frecuente) están en [[decisiones-agente]] — este archivo define los estados; aquel, las decisiones. Los mensajes exactos, en [[guiones-whatsapp]].
> Implementación práctica: cada estado = una **etiqueta de WhatsApp Business** (un color por estado). Existe además una etiqueta especial FUERA del funnel: **CON ESPECIALISTA** — chat derivado a un humano; mientras esté activa, el agente NO responde en ese chat ([[operacion]]).

## Flujo principal

```
NUEVO → EN DIAGNÓSTICO → CALIFICADO → OFERTA → AGENDADO → GANADO/CLIENTE ACTIVO → POSTVENTA
  │           │              (fast-track: comprador listo salta directo a AGENDADO)
  │           └→ EN NUTRICIÓN / DESCALIFICADO
  ├→ silencio en cualquier punto → EN SEGUIMIENTO → EN NUTRICIÓN → (reactiva) → EN DIAGNÓSTICO
  └→ OFERTA → EN OBJECIÓN → AGENDADO / EN SEGUIMIENTO / PERDIDO
                AGENDADO → no-show (1.ª vez: reagenda con adelanto · 2.ª vez: pierde S/ 50) → EN SEGUIMIENTO
```

## QUIÉN ACTIVA CADA ESTADO (la tabla maestra)

Un estado no se activa por "cómo va la conversación": se activa por la **evidencia de un actor concreto**. La regla madre: **el cliente no puede autopresentarse la oferta, ni autoconfirmarse la cita, ni autoatenderse** — los estados que describen acciones del vendedor o del negocio exigen evidencia DE ESE lado visible en el chat. Y el **RELOJ** (silencio, fechas de recontacto) es un actor más: sus transiciones son deterministas y corren por cron — **nunca las decide el LLM**, que no sabe calcular tiempo.

| Estado | Lo activa | Evidencia mínima exigida |
|---|---|---|
| NUEVO | CLIENTE | escribe por primera vez (primera vez REAL: un cliente pasado nunca vuelve aquí) |
| EN DIAGNÓSTICO | CLIENTE | responde y cuenta qué busca o su problema |
| CALIFICADO | CLIENTE | las 3 luces verdes visibles: dolor verbalizado + filtro de contraindicaciones pasado + decide y no descartó el rango |
| OFERTA PRESENTADA | **VENDEDOR** | un mensaje DEL VENDEDOR con propuesta concreta (pack/precio final + invitación a agendar). Que el cliente pida precio, pida una promo o diga "quiero X" **JAMÁS** la activa; el precio de lista suelto tampoco es una oferta |
| EN OBJECIÓN | CLIENTE | un freno DESPUÉS de una oferta visible en el chat (antes de oferta no hay objeción: es brush-off → nutrición) |
| AGENDADO | CLIENTE (+ vendedor) | evidencia del adelanto de S/ 50 (captura de Yape/Plin, o el vendedor confirmando "cita separada"). El deseo de cita ("resérvame el sábado") NO es cita |
| CLIENTE ACTIVO | CLIENTE | evidencia de que asistió (mensaje post-sesión, cuidados, "¿cómo te fue?") |
| POSTVENTA | CLIENTE | evidencia de tratamiento o pack terminado |
| EN SEGUIMIENTO | **RELOJ** (o CLIENTE) | vendedor habló último + 24 h reales de silencio (lo determina el cron, no el LLM) — o el cliente pidió tiempo con fecha ("escríbeme el viernes") |
| EN NUTRICIÓN | CLIENTE o RELOJ | brush-off ("para más adelante", "solo preguntaba") o cadencia de seguimiento agotada (cron) |
| PERDIDO | CLIENTE o RELOJ | rechazo explícito tras la oferta / compró en otro lado / cadencia agotada con "no" claro |
| DESCALIFICADO | CLIENTE | contraindicación o sin fit verbalizados en el chat |
| BAJA | CLIENTE | pidió no recibir más mensajes. **TERMINAL** — única salida: el PROPIO cliente pide explícitamente retomar la comunicación (opt-in de nuevo), o lo revierte un humano. El agente jamás la revierte por interpretación |

**Reglas de estabilidad (anti-aleteo):**
- La señal de compra (pregunta precio, horarios, "me interesa") **NUNCA crea un estado**: solo marca urgencia para el vendedor. El estado avanza cuando el ACTOR correspondiente aporta su evidencia.
- Sin evidencia nueva → el estado SE MANTIENE. Un estado que va y vuelve en minutos (A→B→A) es un clasificador roto, no un lead indeciso.
- No hay retrocesos de etapa avanzada a temprana por preguntas de detalle (una duda en OFERTA sigue siendo OFERTA; un freno real es EN OBJECIÓN).

## Los estados

### 1. NUEVO
- **Lo activa:** CLIENTE — escribe o responde por primera vez.
- **Entra:** primer contacto real (registrar ORIGEN: anuncio / referido / orgánico — convierten distinto). Un cliente activo o pasado que pregunta por otro servicio NO vuelve aquí — es cross-sell desde su estado actual, con su historial ([[decisiones-agente]] §3).
- **Objetivo:** responder en <5 minutos y abrir conversación humana (Carnegie). Si pide precio: valor + diferenciación + puente a pre-evaluación — el precio NO se da en frío; se presenta en la oferta ([[decisiones-agente]] §1).
- **Sale a:** EN DIAGNÓSTICO (conversa) · **AGENDADO** (comprador listo que pide fecha — fast-track: solo filtro de contraindicaciones + adelanto CONFIRMADO) · EN SEGUIMIENTO (silencio 24 h — cron).
- **Expertos guía:** [[05-dale-carnegie]], [[14-alex-hormozi]] (guion A-C-A si el contacto es en frío).

### 2. EN DIAGNÓSTICO
- **Lo activa:** CLIENTE — responde contando qué busca o su problema. Pedir una promo o un precio en el primer mensaje entra AQUÍ (jamás a OFERTA: aún no hay propuesta del vendedor).
- **Objetivo:** entender problema y consecuencias con preguntas — una por mensaje. El **precio-ancla se responde siempre que lo pidan**; lo que NO se adelanta sin diagnóstico es la oferta personalizada ni la agenda.
- **Sale a:** CALIFICADO (3 luces verdes) · EN NUTRICIÓN ("no ahora") · DESCALIFICADO (sin fit; razón registrada) · EN SEGUIMIENTO (silencio 48 h — cron).
- **Expertos guía:** [[09-neil-rackham]] (SPIN), [[11-jeremy-miner]] (NEPQ), [[10-david-sandler]] (embudo de dolor).

### 3. CALIFICADO
- **Lo activa:** CLIENTE — completó las 3 luces verdes (dolor + filtro pasado + decide/puede). Ojo: pasar el filtro de contraindicaciones NO es recibir la oferta — el lead queda AQUÍ hasta que el VENDEDOR mande la propuesta.
- **Objetivo:** pre-suadir (Cialdini: testimonio/antes-después del MISMO servicio) y pactar contrato previo (Sandler). Máximo 24 h en este estado.
- **Sale a:** OFERTA PRESENTADA (cuando el VENDEDOR envía la propuesta).
- **Expertos guía:** [[10-david-sandler]], [[06-robert-cialdini]], [[17-dan-kennedy]].

### 4. OFERTA PRESENTADA
- **Lo activa:** VENDEDOR — envió la propuesta concreta (pack/precio final con invitación a agendar). Es el único estado del funnel activo que exige evidencia del lado del vendedor: **el cliente no puede autopresentarse la oferta**.
- **Objetivo:** oferta conectada al diagnóstico, con el pack como opción principal, garantía/beneficios y deadline real; cierre alternativo (Ziglar) + pedir el **adelanto de S/ 50** para separar.
- **Sale a:** AGENDADO (adelanto recibido) · EN OBJECIÓN · EN SEGUIMIENTO (silencio 48 h — cron). **Ojo:** un "sí" sin adelanto NO es AGENDADO — sigue aquí y se recuerda el adelanto con tacto.
- **Expertos guía:** [[14-alex-hormozi]], [[01-zig-ziglar]], [[17-dan-kennedy]].

### 5. EN OBJECIÓN
- **Lo activa:** CLIENTE — un freno DESPUÉS de la oferta ("está caro", "lo voy a pensar", "le pregunto a mi esposo"). Un "no me interesa" ANTES de cualquier oferta no es objeción: es brush-off → NUTRICIÓN.
- **Objetivo:** validar → etiquetar → aislar → re-presentar valor → re-cerrar (máx. 2-3 loops).
- **Sale a:** AGENDADO (resuelta + adelanto) · EN SEGUIMIENTO (pide tiempo: con fecha pactada) · PERDIDO (registrar la objeción final: es tu mejor data).
- **Expertos guía:** [[07-chris-voss]], [[08-jordan-belfort]], [[12-jeb-blount]] — ver [[playbook-objeciones]].

### 6. AGENDADO (cita separada con adelanto)
- **Lo activa:** CLIENTE (+ confirmación del vendedor) — adelanto de S/ 50 con evidencia en el chat (captura de Yape/Plin o "cita separada" del vendedor). Sin adelanto no hay cita separada ([[operacion]]); frases como "resérvame el sábado" son deseo, no cita.
- **Objetivo:** blindar la asistencia: confirmación con dirección y link de Maps + cuidados previos de la ficha + recordatorio 24 h antes + recordatorio 2-3 h antes ([[guiones-whatsapp]] §8).
- **Sale a:** GANADO (asistió) · **NO-SHOW**: 1.ª vez → reagendar manteniendo el adelanto (una sola vez); 2.ª inasistencia → pierde los S/ 50 → EN SEGUIMIENTO. Si avisa con **≥12 h de anticipación**, es **reagendo proactivo**: no cuenta como no-show, adelanto intacto, sigue en AGENDADO (con menos de 12 h, cuenta como inasistencia — [[operacion]]).
- **Métrica clave:** tasa de no-show (si supera ~10-15 %, revisar recordatorios y adelanto).

### 7. GANADO / CLIENTE ACTIVO
- **Lo activa:** CLIENTE — asistió a su primera sesión (evidencia: mensaje post-sesión, cuidados, "¿cómo te fue?").
- **Objetivo:** si compró pack o tratamiento multi-sesión, es **cliente activo**: siguiente sesión agendada SIEMPRE antes de salir de la clínica, mensaje post-sesión con cuidados (ficha), recordatorio de siguiente sesión, y upsell natural entre sesiones (limpieza → Hollywood Peel; papada → HIFU; depilación de axilas → Hollywood Peel de axilas para aclarado).
- **Sale a:** POSTVENTA (terminó su tratamiento/pack).
- **Regla de oro:** un cliente activo sin próxima cita en agenda es una alerta — nunca debe pasar.
- **Expertos guía:** [[13-grant-cardone]] (la 2.ª venta es más fácil), [[04-joe-girard]].

### 8. POSTVENTA / REFERIDOS
- **Lo activa:** CLIENTE — terminó su tratamiento o pack (postventa es SOLO cuando terminó todo; con sesiones pendientes sigue siendo cliente activo).
- **Objetivo:** confirmar satisfacción a las 24-48 h, contacto de cercanía periódico (no de venta), pedir referido en el pico de satisfacción (gancho: plan pareja de limpieza S/ 160), y **recompra programada**: Botox al mes 4, depilación al terminar pack (faltan sesiones para el resultado completo), mantenimientos anuales (HIFU).
- **Sale a:** AGENDADO (acepta una recompra — fast-track de cliente: sin diagnóstico, solo re-filtro + adelanto) · OFERTA (pregunta por otro servicio — cross-sell) · su referido entra como NUEVO (origen: referido).
- **Expertos guía:** [[04-joe-girard]] (Ley de 250), [[13-grant-cardone]].

### 9. EN SEGUIMIENTO (silencio en cualquier punto del funnel)
- **Lo activa:** RELOJ (cron) — vendedor habló último + 24 h reales sin respuesta. También el CLIENTE cuando pide tiempo con fecha pactada ("escríbeme el viernes"). **Nunca lo decide el LLM calculando tiempo**: el cálculo de silencio es del cron ([[decisiones-agente]] §3; `utils/cron-seguimiento.sql`).
- **Entra:** el lead dejó de responder (en NUEVO, DIAGNÓSTICO, OFERTA, OBJECIÓN o tras no-show), o pidió tiempo con fecha pactada.
- **Objetivo:** cadencia de 6-8 toques en ~30-45 días (día 1, 3, 7, 14, 21, 30 — los mensajes modelo en [[guiones-whatsapp]] §7), variando formato, valor nuevo en cada toque — nunca "¿pudiste verlo?". Último recurso: pregunta de 9 palabras de Voss.
- **La cadencia se adapta a dónde quedó el lead:** silencio pre-oferta → toques de re-enganche suave (sin promos ni deadlines); silencio post-oferta → cadencia completa. Si se usa la API de WhatsApp Business, los toques fuera de la ventana de 24 h requieren plantillas aprobadas ([[operacion]]).
- **Sale a:** retoma donde quedó (DIAGNÓSTICO u OFERTA según lo que faltaba) · EN NUTRICIÓN (30-45 días sin respuesta — cron) · PERDIDO.
- **Expertos guía:** [[13-grant-cardone]], [[12-jeb-blount]], [[17-dan-kennedy]].

### 10. EN NUTRICIÓN (el 97 % que no compra hoy)
- **Lo activa:** CLIENTE (brush-off: "para más adelante", "solo preguntaba") o RELOJ (cadencia de seguimiento agotada, fecha de recontacto vencida — cron).
- **Objetivo:** educación espaciada sin vender: ritmo 3 valor : 1 oferta (Gary Vee), por estados de WhatsApp o listas de difusión SOLO de contactos que ya interactuaron (anti-bloqueo). Reactivar con oferta cada 30-60 días.
- **Sale a:** EN DIAGNÓSTICO (mostró interés — retomar donde quedó, sin reprochar el silencio) · BAJA (pidió no recibir más).
- **Expertos guía:** [[16-sabri-suby]], [[18-chet-holmes]], [[20-gary-vaynerchuk]].

### 11. PERDIDO / DESCALIFICADO / BAJA
- **Los activa:** CLIENTE (rechazo explícito tras la oferta, contraindicación, pedido de baja) o RELOJ (cadencia agotada). Nunca una interpretación sin evidencia.
- **Siempre con razón registrada** (precio, timing, desconfianza, contraindicación, sin fit). Los "timing" y las contraindicaciones temporales (embarazo, tatuaje <3 meses) llevan **fecha de recontacto** y vuelven a NUTRICIÓN o DIAGNÓSTICO en esa fecha.
- **BAJA es terminal y sagrada:** pidió no recibir más mensajes → se respeta de inmediato y no se contacta nunca más. En WhatsApp esto protege el número: leads molestos bloquean y reportan spam, y los reportes acumulados hacen que WhatsApp suspenda la línea. **Única excepción para salir de BAJA:** el propio cliente escribe pidiendo explícitamente retomar la comunicación (opt-in de nuevo — se registra el mensaje como evidencia), o la revierte un humano desde el panel. El agente jamás la revierte por deducción.

## Métricas mínimas (Aaron Ross)
1. Leads nuevos/semana por origen.
2. % de conversión entre cada par de estados (dónde se rompe el funnel).
3. N.º de toques promedio hasta AGENDADO (Cardone: la venta está entre el toque 5 y el 12).
4. **Tasa de no-show** (AGENDADO → GANADO).
5. % de clientes activos con próxima cita en agenda (debe ser 100 %) y % de recompra post-tratamiento.
6. **Salud del clasificador** (nueva, con `lead_activity`): % de transiciones válidas según la tabla maestra; transiciones `nuevo → oferta_presentada` deben ser ~0 y todo `en_seguimiento` por silencio debe venir del cron, no del LLM.
