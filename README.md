# Base de conocimiento · Los 20 mejores exponentes de ventas y cierre

Base de conocimiento para crear prompts de venta por **WhatsApp** para la clínica estética **DermicaPro** (Trujillo, Perú): manejo de objeciones, elección de formato (texto/audio/flyer/video), funnel de estados para leads y datos del negocio.

## Estructura
- `expertos/` — un archivo por experto: sus ideas, técnicas concretas, aplicación a WhatsApp y un bloque listo para usar en prompts.
- `guias/` — síntesis prácticas que cruzan a varios expertos:
  - [Funnel de estados para leads](guias/funnel-estados-leads.md)
  - [Manual de decisiones del agente](guias/decisiones-agente.md) — cuándo cambiar de estado, cuándo dar el precio, cuándo tratar objeciones
  - [Cuándo enviar texto, audio, flyer o video](guias/formatos-mensaje.md)
  - [Playbook de objeciones](guias/playbook-objeciones.md)
- `negocio/` — datos del negocio (clínica estética **DermicaPro**, Trujillo, Perú — precios en soles):
  - [Lista de precios por servicio y sesiones](negocio/precios-servicios.md) — generada desde el Excel de `utils/`
  - [Fichas de procedimientos](negocio/fichas-procedimientos.md) — en qué consiste cada uno, indicaciones, contraindicaciones y cuidados (borrador a validar por el especialista)
  - [Mapa dolor → solución](negocio/mapa-dolores-soluciones.md) — qué tratamiento aplica a cada problema, escrito como pregunta el lead
  - [Datos operativos](negocio/operacion.md) — horarios, formas de pago, adelanto, reglas del agente
  - [Biblioteca de guiones WhatsApp](negocio/guiones-whatsapp.md) — qué decir en cada momento del funnel, en sintaxis WhatsApp lista para usar
- `prompts/` — prompts de producción de los agentes:
  - [Agente 1: Analista de leads](prompts/agente-analista-leads.md) — clasifica el estado y actualiza la BD (n8n)
  - [Agente 2: Copiloto de ventas](prompts/agente-copiloto-ventas.md) — genera las sugerencias de respuesta que ve el vendedor en el frontend (n8n + RAG)
  - [Agente 3: Auditor de conversaciones](prompts/agente-auditor-conversaciones.md) — QA post-conversación: scorecard, momento crítico y coaching para el vendedor. Se usa desde Claude Code (subagente `.claude/agents/auditor-conversaciones.md`, que lee este archivo como rúbrica); el bloque n8n queda listo por si se automatiza. Es el único que usa `expertos/`
  - [Arquitectura del RAG](prompts/arquitectura-rag.md) — qué se indexa, qué va al prompt y qué a consulta exacta, con argumentos
- `.claude/agents/` — subagentes de Claude Code: [auditor-conversaciones](.claude/agents/auditor-conversaciones.md) (ejecuta el Agente 3 en local), [experto-ia-n8n](.claude/agents/experto-ia-n8n.md) — consultor de prompts, workflows n8n, RAG y elección/costos de modelos de IA — y [experto-funnel-wsp](.claude/agents/experto-funnel-wsp.md) — consultor de diseño de funnels de venta por WhatsApp (audita estados, transiciones y métricas contra la BD real)
- `utils/` — fuentes y herramientas: [migración SQL de estados](utils/migracion-estados-leads.sql), [generador de chunks RAG](utils/generar_chunks_rag.py), sembrador de casos ([seed_tests.py](utils/seed_tests.py)) y los testers: [copiloto](utils/test_copiloto.py) (24 casos), [analista](utils/test_analista.py) (33 casos de transiciones de estado) y [auditor](utils/test_auditor.py) (10 conversaciones completas con su auditoría esperada, 2 con auditoría de transiciones)

## Los 20 expertos: quién es quién y para qué usarlo

| # | Experto | Su fuerte | Úsalo cuando necesites… |
|---|---|---|---|
| 01 | [Zig Ziglar](expertos/01-zig-ziglar.md) | Cierres, precio vs. costo | Cerrar y responder "está caro" |
| 02 | [Brian Tracy](expertos/02-brian-tracy.md) | Proceso de 7 pasos, psicología | La columna vertebral del proceso de venta |
| 03 | [Tom Hopkins](expertos/03-tom-hopkins.md) | Palabras exactas, micro-compromisos | Pulir el lenguaje de tus plantillas |
| 04 | [Joe Girard](expertos/04-joe-girard.md) | Postventa, referidos (Ley de 250) | Clientes repetidos y referidos |
| 05 | [Dale Carnegie](expertos/05-dale-carnegie.md) | Rapport, relaciones | Los primeros 3 mensajes con un lead |
| 06 | [Robert Cialdini](expertos/06-robert-cialdini.md) | 7 principios de influencia | Decidir qué gatillo activar y cuándo |
| 07 | [Chris Voss](expertos/07-chris-voss.md) | Negociación FBI, empatía táctica | Objeciones difíciles y leads en visto |
| 08 | [Jordan Belfort](expertos/08-jordan-belfort.md) | Línea Recta, loops, tonalidad | Guiones estructurados y loops de objeción |
| 09 | [Neil Rackham](expertos/09-neil-rackham.md) | SPIN, avances | Preguntas de diagnóstico; definir "avance" por estado |
| 10 | [David Sandler](expertos/10-david-sandler.md) | Calificación, contrato previo | Filtrar curiosos y matar el "lo voy a pensar" |
| 11 | [Jeremy Miner](expertos/11-jeremy-miner.md) | NEPQ, venta sin presión | El tono ideal para chat: experto desapegado |
| 12 | [Jeb Blount](expertos/12-jeb-blount.md) | Cadencias, tipos de objeción | Secuencias de seguimiento; clasificar objeciones |
| 13 | [Grant Cardone](expertos/13-grant-cardone.md) | Seguimiento masivo, acuerdo | Persistir sin quemarte (toques 5-12) |
| 14 | [Alex Hormozi](expertos/14-alex-hormozi.md) | Ofertas Grand Slam, leads | Diseñar QUÉ ofreces antes que el guion |
| 15 | [Russell Brunson](expertos/15-russell-brunson.md) | Funnels, escalera de valor | La arquitectura completa del funnel |
| 16 | [Sabri Suby](expertos/16-sabri-suby.md) | Tráfico frío, videos de valor | Nutrir al 97 % que no compra hoy |
| 17 | [Dan Kennedy](expertos/17-dan-kennedy.md) | Respuesta directa, deadlines | Flyers/mensajes que exigen acción con fecha |
| 18 | [Chet Holmes](expertos/18-chet-holmes.md) | Pirámide del comprador, educación | Clasificar leads fríos y educarlos |
| 19 | [Aaron Ross](expertos/19-aaron-ross.md) | Pipeline, estados, métricas | Definir formalmente los estados y medirlos |
| 20 | [Gary Vaynerchuk](expertos/20-gary-vaynerchuk.md) | Contenido nativo, ritmo 3:1 | Decidir formato (texto/audio/flyer/video) |

## Mapa rápido por necesidad

- **Manejo de objeciones:** Voss (07) + Belfort (08) + Blount (12) + Ziglar (01) → [playbook](guias/playbook-objeciones.md)
- **Qué formato enviar:** Gary Vee (20) + Suby (16) + Belfort (08, tonalidad→audio) → [guía de formatos](guias/formatos-mensaje.md)
- **Funnel / estados de leads:** Ross (19) + Brunson (15) + Holmes (18) + Sandler (10) → [guía de funnel](guias/funnel-estados-leads.md)
- **Primer contacto:** Carnegie (05) + Hormozi (14, guion A-C-A)
- **Diagnóstico y calificación:** Rackham (09) + Miner (11) + Sandler (10)
- **Diseño de la oferta:** Hormozi (14) + Kennedy (17) + Cialdini (06)
- **Seguimiento:** Cardone (13) + Blount (12) + Kennedy (17)
- **Postventa y referidos:** Girard (04)

## Cómo usar esta base para crear prompts
1. **Prompt de rol único:** copia el bloque "Cómo invocarlo en un prompt" del experto que aplica a la situación.
2. **Prompt de agente vendedor completo:** system prompt = [funnel](guias/funnel-estados-leads.md) + [manual de decisiones](guias/decisiones-agente.md) + [datos operativos](negocio/operacion.md) + estilo de [formatos](guias/formatos-mensaje.md) + 8-10 guiones canónicos como few-shots; RAG recuperable = [fichas](negocio/fichas-procedimientos.md), [objeciones](guias/playbook-objeciones.md) y el resto de [guiones](negocio/guiones-whatsapp.md); [precios](negocio/precios-servicios.md) como datos exactos (no fragmentos semánticos). Los `expertos/` quedan FUERA del RAG del agente (son biblioteca de consulta) — la receta completa está en la sección 6 del [manual de decisiones](guias/decisiones-agente.md).
3. **Prompt de análisis:** pega una conversación real y pide evaluarla contra un experto específico ("¿qué haría Voss aquí?") o contra la guía de objeciones.

## Menciones honoríficas (no incluidos en el top 20)
Matthew Dixon (*The Challenger Sale*, más B2B enterprise), Daniel Pink (*To Sell Is Human*), Og Mandino (*El vendedor más grande del mundo*, mentalidad), Frank Bettger (clásico de actitud), Oren Klaff (*Pitch Anything*, presentaciones de alto ticket).
# analisis-agentes-ia
