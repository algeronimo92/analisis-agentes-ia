-- ============================================================
-- Transiciones por TIEMPO (silencio) — corren por cron, no por LLM
--
-- ⚠️ IMPORTANTE (cambio de diseño, ver auditorias/informe-estados.md H5):
-- Estas queries ya NO hacen UPDATE directo a leads.estado. El UPDATE
-- directo se salta la auditoría (lead_activity), las notificaciones
-- WebSocket y las automatizaciones del CRM. El flujo correcto:
--
--   n8n: Schedule Trigger (cada hora)
--     → nodo Postgres con el SELECT de candidatos (abajo)
--     → por cada fila: HTTP Request
--         POST https://<backend>/webhooks/lead-stage
--         { "chat_id": remote_jid, "estado": estado_nuevo,
--           "razonamiento": razon }
--
-- El backend valida el enum, actualiza leads.estado y registra la fila
-- de auditoría en lead_activity. Así TODA transición queda auditada
-- (las del cron incluidas — hoy son transiciones fantasma invisibles).
-- ============================================================

-- 1. Silencio: el vendedor habló último hace >24 h → en_seguimiento
--    (solo estados de conversación activa; los protegidos no se tocan)
SELECT remote_jid,
       'en_seguimiento' AS estado_nuevo,
       'Cron: vendedor habló último hace más de 24 h sin respuesta (silencio, estado previo: ' || estado || ')' AS razon
FROM leads
WHERE ultimo_emisor = 'vendedor'
  AND ultimo_mensaje_at < now() - interval '24 hours'
  AND estado IN ('nuevo', 'en_diagnostico', 'calificado', 'oferta_presentada', 'en_objecion');

-- 2. Cadencia agotada: en_seguimiento sin respuesta hace >45 días → en_nutricion
SELECT remote_jid,
       'en_nutricion' AS estado_nuevo,
       'Cron: cadencia de seguimiento agotada (45 días sin respuesta)' AS razon
FROM leads
WHERE estado = 'en_seguimiento'
  AND ultimo_mensaje_at < now() - interval '45 days';

-- 3. Recontactos vencidos: descalificado temporal cuya fecha llegó → en_nutricion
--    (aparecerán en la vista de nutrición para retomarlos)
SELECT remote_jid,
       'en_nutricion' AS estado_nuevo,
       'Cron: fecha de recontacto vencida (' || fecha_recontacto || ')' AS razon
FROM leads
WHERE estado = 'descalificado'
  AND fecha_recontacto IS NOT NULL
  AND fecha_recontacto <= CURRENT_DATE;

-- Notas:
-- · Excluir leads de prueba si están sembrados:
--     AND remote_jid NOT LIKE '51888000%' AND remote_jid NOT LIKE '51999000%'
-- · División de trabajo: el cron decide TODO lo temporal (silencio, cadencias,
--   recontactos); el agente analista decide TODO lo de contenido. Un LLM nunca
--   calcula tiempo: medimos transiciones a "más de 24 horas" disparadas a los
--   4 segundos (informe-estados.md, H2).
