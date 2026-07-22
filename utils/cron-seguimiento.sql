-- ============================================================
-- Transiciones por TIEMPO (silencio) — corren por cron, no por LLM
-- En n8n: workflow con Schedule Trigger (cada hora) → nodo Postgres
-- ejecutando estas queries. Determinista: no gasta tokens ni falla.
-- ============================================================

-- 1. Silencio: el vendedor habló último hace >24 h → en_seguimiento
--    (solo estados de conversación activa; los protegidos no se tocan)
UPDATE leads
SET estado = 'en_seguimiento'
WHERE ultimo_emisor = 'vendedor'
  AND ultimo_mensaje_at < now() - interval '24 hours'
  AND estado IN ('nuevo', 'en_diagnostico', 'calificado', 'oferta_presentada', 'en_objecion')
RETURNING remote_jid, estado;

-- 2. Cadencia agotada: en_seguimiento sin respuesta hace >45 días → en_nutricion
UPDATE leads
SET estado = 'en_nutricion'
WHERE estado = 'en_seguimiento'
  AND ultimo_mensaje_at < now() - interval '45 days'
RETURNING remote_jid, estado;

-- 3. Recontactos vencidos: descalificado temporal cuya fecha llegó → en_nutricion
--    (aparecerán en la vista de nutrición para retomarlos)
UPDATE leads
SET estado = 'en_nutricion'
WHERE estado = 'descalificado'
  AND fecha_recontacto IS NOT NULL
  AND fecha_recontacto <= CURRENT_DATE
RETURNING remote_jid, estado;

-- Nota: excluir leads de prueba si están sembrados:
--   AND remote_jid NOT LIKE '51888000%' AND remote_jid NOT LIKE '51999000%'
