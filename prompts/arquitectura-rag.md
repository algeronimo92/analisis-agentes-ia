# Arquitectura · Qué va al RAG y qué no (y por qué)

> Decisión de diseño para el índice vectorial del [[agente-copiloto-ventas]]. Principio rector: **el RAG es para conocimiento que varía según la consulta; el system prompt es para reglas que aplican en TODOS los turnos; los datos exactos van a consulta estructurada.** La recuperación vectorial es probabilística — nunca pongas en ella algo que no puede fallar.

## 1 · System prompt (SIEMPRE presente — nunca al RAG)

| Contenido | Por qué NO al RAG |
|---|---|
| Reglas del funnel y tácticas por estado ([[funnel-estados-leads]], [[decisiones-agente]] — ya destiladas en el prompt) | Son la constitución del agente: aplican en cada turno. Si dependieran de retrieval, un turno con mala recuperación = agente sin reglas. Además, recuperar fragmentos de reglas crearía DOBLE autoridad (prompt vs. chunk) con versiones que pueden divergir. |
| Datos operativos ([[operacion]]: horario, pagos, adelanto, dirección, políticas) | Chicos (~300 tokens), invariables y críticos en casi todo turno. Indexarlos además duplicaría la fuente: si cambian, prompt e índice quedarían desincronizados. Una sola fuente: el prompt. |
| Estilo y formato ([[formatos-mensaje]] destilado: asterisco simple, paleta de emojis, un objetivo por turno) | El estilo aplica al 100 % de los mensajes — jamás debe depender de si se recuperó el chunk correcto. |
| 2-3 ejemplos canónicos (few-shots) | Los ejemplos calibran tono y formato de salida; deben estar siempre, no a veces. |

## 2 · RAG vectorial (recuperable por consulta semántica)

| Documento | Chunking | Por qué SÍ al RAG |
|---|---|---|
| [[mapa-dolores-soluciones]] | 1 chunk por dolor | **La estrella del índice.** Las consultas reales llegan fraseadas como dolores ("tengo manchas", "me da roche mi bigotito") y las entradas están escritas con esos sinónimos → match semántico directo. Imposible meter 31 dolores en el prompt sin ahogar al modelo. |
| [[fichas-procedimientos]] | 1 chunk por procedimiento | 16 fichas con contraindicaciones, cuidados y "¿duele?" = demasiado para el prompt, y en cada turno solo se necesita UNA. La recuperación por servicio es el caso ideal del RAG. |
| [[playbook-objeciones]] | 1 chunk por objeción + 1 del proceso de 5 pasos | Se necesita solo cuando hay objeción, y la objeción del lead ("está caro", "le pregunto a mi esposo") matchea directo con el título de cada jugada. |
| [[guiones-whatsapp]] | 1 chunk por sección/situación | El copiloto redacta solo, pero recuperar el guion de la situación exacta ancla el tono y las jugadas probadas. Larga cola de situaciones (no-show, cross-sell, reactivación) que no cabe en el prompt. ⚠️ Los guiones traen **cifras de ejemplo**: el guardrail del copiloto obliga a copiar solo la ESTRUCTURA — la cifra siempre sale del tool 'precios'. |

## 3 · Consulta EXACTA — ni prompt ni vector (los precios)

**[[precios-servicios]] NO debe ir al índice vectorial.** Argumento: la recuperación semántica confunde vecinos — "axilas" puede traer depilación de axilas (S/ 50) o Hollywood Peel de axilas (S/ 120); "pack de 3" existe en 6 servicios distintos. Un precio equivocado citado con seguridad es el peor error posible del agente (se pierde la venta o la confianza).

**Fuente de verdad: la app de precios que la clínica YA usa (online).** Los precios nunca se mantienen a mano en dos lugares — todo lee de esa app. Dos formas de conectar el tool 'precios' del copiloto:
1. **Tool directo (ELEGIDO):** HTTP Request de n8n a la API pública de la app de la clínica: `GET https://dermicapro.app/api/public/catalog` — sin auth. Estructura: `data[].name` ("Servicio - Zona/Detalle") y `data[].packages[]` con `{label, sessions, price}`. Precio vigente en tiempo real, cero sincronización. Config del tool en [[agente-copiloto-ventas]].
2. **Réplica sincronizada (si no hay API cómoda):** job de n8n que copia los precios de la app a una tabla `servicios_precios` cada X horas; el tool lee la tabla (rápido y resistente a caídas de la app, con el desfase del intervalo).
En ambos casos el tool entrega al copiloto la misma estructura: `servicio, detalle/zona, sesiones, precio, nota`. El archivo [[precios-servicios]] queda como documentación de referencia para humanos (y para validar la app), NO como fuente del agente.

## 4 · FUERA de todo (ni RAG, ni prompt)

| Contenido | Por qué fuera |
|---|---|
| `expertos/` (los 20) | Ya están destilados en las guías. Indexarlos crea **ruido de recuperación**: "cómo cierro esta venta" traería la biografía de Ziglar compitiendo contra el playbook operativo. Y un agente con ese material tiende a citar gurús al cliente ("como dice Cardone…") — rarísimo en una clínica. Son biblioteca para iterar prompts y formar vendedores humanos. |
| [[funnel-estados-leads]] y [[decisiones-agente]] como documentos | Su contenido vive en los prompts de los agentes; indexarlos además = doble autoridad. |
| README, memoria, prompts, migración SQL, Excel | Meta-documentos del proyecto, no conocimiento de venta. |
| Historiales de conversaciones de clientes | Privacidad + ruido. El historial del lead activo llega por el user prompt, no por el índice. |

## 5 · El Agente 1 (analista) NO usa RAG
Clasifica con la conversación + sus reglas; todo lo que necesita cabe en su prompt. Darle RAG solo agregaría latencia, costo y una fuente de inconsistencia a un flujo que corre en cada mensaje.

## 6 · Reglas de indexación
- **Generación de chunks:** `python3 utils/generar_chunks_rag.py` → produce `utils/rag-chunks.json` (68 chunks con metadata, enlaces y marcas editoriales limpiados, encabezado de contexto por chunk). Si cambia uno de los 4 documentos: re-correr el script y re-insertar.
- **Chunk = sección de markdown** (un dolor, una ficha, una objeción, un guion) — nunca cortes por tamaño fijo que partan una ficha a la mitad.
- **Metadata por chunk:** `{tipo: dolor|ficha|objecion|guion, servicio: <nombre|null>}` — permite filtrar (ej. solo fichas) además del match semántico.
- Cada chunk debe ser **autocontenido** (repetir el nombre del servicio dentro del texto — los archivos ya lo hacen).
- Los enlaces `[[...]]` se pueden limpiar al indexar (son navegación, no contenido).
- **Proceso de actualización:** cambia el Excel → regenerar `precios-servicios.md` → actualizar la tabla/tool de precios; cambia una ficha/guion → re-indexar SOLO ese documento. Responsable y frecuencia: definir antes de salir a producción — un RAG desactualizado es peor que no tener RAG.
