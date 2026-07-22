# Negocio · Datos operativos DermicaPro

> Fuente canónica de datos operativos. Los guiones ([[guiones-whatsapp]]) y el agente citan SIEMPRE estos datos — si algo cambia, se actualiza aquí primero.

## Identidad y ubicación
- **Nombre comercial:** DermicaPro
- **Dirección:** Av. Víctor Larco Herrera N.° 877, Urb. Vista Alegre, distrito de Víctor Larco Herrera, Trujillo, La Libertad, Perú.
- **Google Maps:** https://maps.app.goo.gl/W2KsCi6KEDgV76rs9 (mandar siempre el link al confirmar cita — evita el "no encontré el local")

## Horario de atención
- **Lunes a sábado, 9:00 am a 6:00 pm.** Domingos cerrado.
- El agente puede responder chats fuera de horario, pero solo ofrece citas dentro del horario.

## Formas de pago
- **Efectivo**
- **Yape**
- **Plin**
- **Tarjeta** (con **recargo del 5 %** — informarlo SIEMPRE antes de que pague, nunca después)

## Reserva de cita (adelanto)
- Para separar la cita se pide un **adelanto de S/ 50**, que se **descuenta del tratamiento** (no es un costo extra — decirlo así siempre: "se descuenta de tu tratamiento, o sea no pagas de más").
- El adelanto es la herramienta anti-no-show n.º 1: una cita sin adelanto no está separada.
- **Política de inasistencia:** si el lead no asiste, puede **reagendar UNA vez manteniendo su adelanto**. Si tampoco asiste a esa segunda cita, **pierde los S/ 50**. Al reagendar el primer no-show, el agente lo comunica en positivo ("tu adelanto sigue válido para la nueva fecha 😊, solo ten en cuenta que se mantiene para esta única reprogramación").
- **Reagendo proactivo:** si el lead avisa con **al menos 12 horas de anticipación**, NO cuenta como inasistencia — se reagenda con el adelanto intacto y se le agradece el aviso. Si avisa con **menos de 12 h**, se reagenda igual con amabilidad pero cuenta como inasistencia para la política del adelanto (1.ª vez lo conserva, 2.ª lo pierde).
- **[DEFINIR: cancelación definitiva]** — si el lead cancela del todo (no reagenda), ¿el adelanto se devuelve, queda como crédito para más adelante, o se pierde? El agente deriva a administración hasta tener esta regla.
- **Pago de packs:** el pack se paga **completo en la primera sesión** (el adelanto de S/ 50 se descuenta de ese pago). Las sesiones restantes ya quedan pagadas: los reagendos de sesiones intermedias van sin penalidad y no hay cobros sesión por sesión. Si el lead pregunta: "el resto lo pagas el día de tu primera sesión 😊".

## Servicios especiales del catálogo (app)
- **"Control" (S/ 0):** cita de revisión post-procedimiento para verificar que todo esté bien. NO es un servicio que se venda ni cotice — se ofrece como beneficio en cliente_activo/postventa ("tu control de revisión va incluido, sin costo").
- **"Consulta" (S/ 50):** la cita de **valoración con la especialista** — revisa el estado del paciente y le dice qué necesita, sin compromiso de tratarse. Es el MISMO monto del adelanto: cuando alguien agenda un tratamiento, sus S/ 50 de adelanto equivalen a esta consulta y **se descuentan del tratamiento**. Doble uso en ventas: (1) reencuadre del adelanto: "no es un cobro extra — es tu consulta con la especialista y se descuenta"; (2) producto puente para indecisos y ticket alto: "empieza por la valoración de S/ 50 y la especialista te dice exactamente qué necesitas".

## Reglas del agente
- **Precios:** el agente cotiza SOLO con [[precios-servicios]]. No ofrece descuentos ni promociones propias bajo ninguna circunstancia; las promos vigentes son únicamente las que figuran en la lista de precios.
- **Derivar a un humano cuando:** (1) pregunta médica que la ficha no responde, (2) reclamo o cliente molesto, (3) pedido de descuento insistente, (4) caso clínico dudoso (posible contraindicación). Frase de derivación: "Esa consulta te la responde mejor nuestra especialista 😊 le paso tu caso y te escribe hoy mismo."
- **Al derivar, el chat se etiqueta CON ESPECIALISTA y el agente deja de responder en ese chat** hasta que el humano lo devuelva (quita la etiqueta). Regla crítica: el error clásico de los bots es seguir contestando encima de la conversación humana.
- **Nota de implementación (para cuando se construya el agente):** con la **API de WhatsApp Business** solo se puede escribir libremente dentro de las 24 h posteriores al último mensaje del lead; fuera de esa ventana, los toques de cadencia y nutrición requieren **plantillas aprobadas por Meta**. Con la app normal de WhatsApp Business no hay restricción. Definir cuál se usará ANTES de programar las cadencias.
- **[DEFINIR: lead que no puede pagar el adelanto por Yape/Plin/tarjeta]** — ¿puede separar una "cita tentativa" sin adelanto (p. ej. confirmada el mismo día por chat) o el adelanto es innegociable? El agente necesita esta regla para no inventarla.
- **Quién atiende:** los guiones y el agente hablan de **"nuestros especialistas"** (genérico, decisión del negocio) — no se citan nombres ni credenciales individuales.
