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

## Los estados

### 1. NUEVO
- **Entra:** el lead escribe o responde por primera vez (registrar ORIGEN: anuncio / referido / orgánico — convierten distinto). Solo primera vez real: un cliente activo o pasado que pregunta por otro servicio NO vuelve aquí — es cross-sell desde su estado actual, con su historial ([[decisiones-agente]] §3).
- **Objetivo:** responder en <5 minutos y abrir conversación humana (Carnegie). Si pide precio: valor + diferenciación + puente a pre-evaluación — el precio NO se da en frío; se presenta en la oferta ([[decisiones-agente]] §1).
- **Sale a:** EN DIAGNÓSTICO (conversa) · **AGENDADO** (comprador listo que pide fecha — fast-track: solo filtro de contraindicaciones + adelanto) · EN SEGUIMIENTO (silencio 24 h).
- **Expertos guía:** [[05-dale-carnegie]], [[14-alex-hormozi]] (guion A-C-A si el contacto es en frío).

### 2. EN DIAGNÓSTICO
- **Objetivo:** entender problema y consecuencias con preguntas — una por mensaje. El **precio-ancla se responde siempre que lo pidan**; lo que NO se adelanta sin diagnóstico es la oferta personalizada ni la agenda.
- **Sale a:** CALIFICADO (3 luces verdes: dolor + sin contraindicaciones + decide/puede) · EN NUTRICIÓN ("no ahora") · DESCALIFICADO (sin fit; razón registrada) · EN SEGUIMIENTO (silencio 48 h).
- **Expertos guía:** [[09-neil-rackham]] (SPIN), [[11-jeremy-miner]] (NEPQ), [[10-david-sandler]] (embudo de dolor).

### 3. CALIFICADO
- **Objetivo:** pre-suadir (Cialdini: testimonio/antes-después del MISMO servicio) y pactar contrato previo (Sandler). Máximo 24 h en este estado.
- **Sale a:** OFERTA PRESENTADA.
- **Expertos guía:** [[10-david-sandler]], [[06-robert-cialdini]], [[17-dan-kennedy]].

### 4. OFERTA PRESENTADA
- **Objetivo:** oferta conectada al diagnóstico, con el pack como opción principal, garantía/beneficios y deadline real; cierre alternativo (Ziglar) + pedir el **adelanto de S/ 50** para separar.
- **Sale a:** AGENDADO (adelanto recibido) · EN OBJECIÓN · EN SEGUIMIENTO (silencio 48 h). **Ojo:** un "sí" sin adelanto NO es AGENDADO — sigue aquí y se recuerda el adelanto con tacto.
- **Expertos guía:** [[14-alex-hormozi]], [[01-zig-ziglar]], [[17-dan-kennedy]].

### 5. EN OBJECIÓN
- **Objetivo:** validar → etiquetar → aislar → re-presentar valor → re-cerrar (máx. 2-3 loops).
- **Sale a:** AGENDADO (resuelta + adelanto) · EN SEGUIMIENTO (pide tiempo: con fecha pactada) · PERDIDO (registrar la objeción final: es tu mejor data).
- **Expertos guía:** [[07-chris-voss]], [[08-jordan-belfort]], [[12-jeb-blount]] — ver [[playbook-objeciones]].

### 6. AGENDADO (cita separada con adelanto)
- **Entra:** adelanto de S/ 50 recibido (sin adelanto no hay cita separada — [[operacion]]).
- **Objetivo:** blindar la asistencia: confirmación con dirección y link de Maps + cuidados previos de la ficha + recordatorio 24 h antes + recordatorio 2-3 h antes ([[guiones-whatsapp]] §8).
- **Sale a:** GANADO (asistió) · **NO-SHOW**: 1.ª vez → reagendar manteniendo el adelanto (una sola vez); 2.ª inasistencia → pierde los S/ 50 → EN SEGUIMIENTO. Si avisa con **≥12 h de anticipación**, es **reagendo proactivo**: no cuenta como no-show, adelanto intacto, sigue en AGENDADO (con menos de 12 h, cuenta como inasistencia — [[operacion]]).
- **Métrica clave:** tasa de no-show (si supera ~10-15 %, revisar recordatorios y adelanto).

### 7. GANADO / CLIENTE ACTIVO
- **Entra:** asistió a su primera sesión.
- **Objetivo:** si compró pack o tratamiento multi-sesión, es **cliente activo**: siguiente sesión agendada SIEMPRE antes de salir de la clínica, mensaje post-sesión con cuidados (ficha), recordatorio de siguiente sesión, y upsell natural entre sesiones (limpieza → Hollywood Peel; papada → HIFU; depilación de axilas → Hollywood Peel de axilas para aclarado).
- **Sale a:** POSTVENTA (terminó su tratamiento/pack).
- **Regla de oro:** un cliente activo sin próxima cita en agenda es una alerta — nunca debe pasar.
- **Expertos guía:** [[13-grant-cardone]] (la 2.ª venta es más fácil), [[04-joe-girard]].

### 8. POSTVENTA / REFERIDOS
- **Objetivo:** confirmar satisfacción a las 24-48 h, contacto de cercanía periódico (no de venta), pedir referido en el pico de satisfacción (gancho: plan pareja de limpieza S/ 160), y **recompra programada**: Botox al mes 4, depilación al terminar pack (faltan sesiones para el resultado completo), mantenimientos anuales (HIFU).
- **Sale a:** AGENDADO (acepta una recompra — fast-track de cliente: sin diagnóstico, solo re-filtro + adelanto) · OFERTA (pregunta por otro servicio — cross-sell) · su referido entra como NUEVO (origen: referido).
- **Expertos guía:** [[04-joe-girard]] (Ley de 250), [[13-grant-cardone]].

### 9. EN SEGUIMIENTO (silencio en cualquier punto del funnel)
- **Entra:** el lead dejó de responder (en NUEVO, DIAGNÓSTICO, OFERTA, OBJECIÓN o tras no-show), o pidió tiempo con fecha pactada.
- **Objetivo:** cadencia de 6-8 toques en ~30-45 días (día 1, 3, 7, 14, 21, 30 — los mensajes modelo en [[guiones-whatsapp]] §7), variando formato, valor nuevo en cada toque — nunca "¿pudiste verlo?". Último recurso: pregunta de 9 palabras de Voss.
- **La cadencia se adapta a dónde quedó el lead:** silencio pre-oferta → toques de re-enganche suave (sin promos ni deadlines); silencio post-oferta → cadencia completa. Si se usa la API de WhatsApp Business, los toques fuera de la ventana de 24 h requieren plantillas aprobadas ([[operacion]]).
- **Sale a:** retoma donde quedó (DIAGNÓSTICO u OFERTA) · EN NUTRICIÓN (30-45 días sin respuesta) · PERDIDO.
- **Expertos guía:** [[13-grant-cardone]], [[12-jeb-blount]], [[17-dan-kennedy]].

### 10. EN NUTRICIÓN (el 97 % que no compra hoy)
- **Objetivo:** educación espaciada sin vender: ritmo 3 valor : 1 oferta (Gary Vee), por estados de WhatsApp o listas de difusión SOLO de contactos que ya interactuaron (anti-bloqueo). Reactivar con oferta cada 30-60 días.
- **Sale a:** EN DIAGNÓSTICO (mostró interés — retomar donde quedó, sin reprochar el silencio) · BAJA (pidió no recibir más).
- **Expertos guía:** [[16-sabri-suby]], [[18-chet-holmes]], [[20-gary-vaynerchuk]].

### 11. PERDIDO / DESCALIFICADO / BAJA
- **Siempre con razón registrada** (precio, timing, desconfianza, contraindicación, sin fit). Los "timing" y las contraindicaciones temporales (embarazo, tatuaje <3 meses) llevan **fecha de recontacto** y vuelven a NUTRICIÓN o DIAGNÓSTICO en esa fecha.
- **BAJA es terminal y sagrada:** pidió no recibir más mensajes → se respeta de inmediato y no se contacta nunca más. En WhatsApp esto protege el número: leads molestos bloquean y reportan spam, y los reportes acumulados hacen que WhatsApp suspenda la línea.

## Métricas mínimas (Aaron Ross)
1. Leads nuevos/semana por origen.
2. % de conversión entre cada par de estados (dónde se rompe el funnel).
3. N.º de toques promedio hasta AGENDADO (Cardone: la venta está entre el toque 5 y el 12).
4. **Tasa de no-show** (AGENDADO → GANADO).
5. % de clientes activos con próxima cita en agenda (debe ser 100 %) y % de recompra post-tratamiento.
