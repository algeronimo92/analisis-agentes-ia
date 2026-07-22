-- ============================================================
-- Migración de estados del funnel · tabla leads (DermicaPro)
-- De: lead_estado v1 (nuevo, calificacion, cotizacion, objecion,
--     cierre, agendado, postventa, sin_respuesta, reactivacion, perdido)
-- A:  funnel de 11 estados + baja/descalificado
--     (ver guias/funnel-estados-leads.md)
-- Todo corre en UNA transacción: si algo falla, nada cambia.
-- ============================================================

BEGIN;

-- ------------------------------------------------------------
-- 1. Crear el enum nuevo
-- ------------------------------------------------------------
CREATE TYPE lead_estado_v2 AS ENUM (
  'nuevo',
  'en_diagnostico',
  'calificado',
  'oferta_presentada',
  'en_objecion',
  'agendado',
  'cliente_activo',
  'postventa',
  'en_seguimiento',
  'en_nutricion',
  'perdido',
  'descalificado',
  'baja'
);

-- ------------------------------------------------------------
-- 2. Migrar la columna con el mapeo viejo → nuevo
-- ------------------------------------------------------------
ALTER TABLE leads ALTER COLUMN estado DROP DEFAULT;

ALTER TABLE leads ALTER COLUMN estado TYPE lead_estado_v2 USING (
  CASE estado::text
    WHEN 'nuevo'         THEN 'nuevo'
    WHEN 'calificacion'  THEN 'en_diagnostico'     -- en proceso de calificar = diagnóstico
    WHEN 'cotizacion'    THEN 'oferta_presentada'  -- ya recibió precios/propuesta
    WHEN 'objecion'      THEN 'en_objecion'
    WHEN 'cierre'        THEN 'oferta_presentada'  -- ⚠️ VER NOTA ABAJO antes de correr
    WHEN 'agendado'      THEN 'agendado'
    WHEN 'postventa'     THEN 'postventa'
    WHEN 'sin_respuesta' THEN 'en_seguimiento'
    WHEN 'reactivacion'  THEN 'en_nutricion'
    WHEN 'perdido'       THEN 'perdido'
  END
)::lead_estado_v2;

-- ⚠️ NOTA sobre 'cierre' (236 leads): este script asume que "cierre"
-- significaba "en proceso de cerrar" → oferta_presentada.
-- Si en tu operación "cierre" significaba "YA COMPRÓ", cambia esa línea por:
--   WHEN 'cierre' THEN 'cliente_activo'

ALTER TABLE leads ALTER COLUMN estado SET DEFAULT 'nuevo';

-- ------------------------------------------------------------
-- 3. Reemplazar el tipo viejo por el nuevo
-- ------------------------------------------------------------
DROP TYPE lead_estado;
ALTER TYPE lead_estado_v2 RENAME TO lead_estado;

-- ------------------------------------------------------------
-- 4. Columnas nuevas que el funnel necesita
--    (origen, notas y metadata ya existen — no se tocan)
-- ------------------------------------------------------------
ALTER TABLE leads
  ADD COLUMN IF NOT EXISTS con_especialista   boolean     NOT NULL DEFAULT false, -- chat derivado a humano: el agente NO responde
  ADD COLUMN IF NOT EXISTS razon_perdido      text,                               -- obligatoria al pasar a perdido/descalificado
  ADD COLUMN IF NOT EXISTS fecha_recontacto   date,                               -- descalificados temporales (embarazo, tatuaje <3 meses) y "escríbeme en agosto"
  ADD COLUMN IF NOT EXISTS contador_noshow    smallint    NOT NULL DEFAULT 0,     -- 1.ª inasistencia conserva adelanto, 2.ª lo pierde
  ADD COLUMN IF NOT EXISTS proxima_cita       timestamptz,                        -- regla de oro: cliente_activo sin proxima_cita = alerta
  ADD COLUMN IF NOT EXISTS toques_seguimiento smallint    NOT NULL DEFAULT 0,     -- cadencia 6-8 toques máx.
  ADD COLUMN IF NOT EXISTS fecha_ultimo_toque timestamptz;                        -- para programar el siguiente toque

-- ------------------------------------------------------------
-- 5. Índices útiles para el agente y los jobs de cadencia
-- ------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_leads_estado           ON leads (estado);
CREATE INDEX IF NOT EXISTS idx_leads_fecha_recontacto ON leads (fecha_recontacto) WHERE fecha_recontacto IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_leads_proxima_cita     ON leads (proxima_cita)     WHERE proxima_cita IS NOT NULL;

-- ------------------------------------------------------------
-- 6. VERIFICACIÓN — revisa este resultado ANTES del COMMIT.
-- Esperado (si 'cierre' → oferta_presentada):
--   nuevo 991 · oferta_presentada 353 · agendado 76 · en_seguimiento 74
--   en_diagnostico 37 · en_objecion 19 · postventa 12 · perdido 7 · en_nutricion 2
-- ------------------------------------------------------------
SELECT estado, COUNT(*) FROM leads GROUP BY estado ORDER BY COUNT(*) DESC;

COMMIT;
-- Si la verificación no cuadra: ROLLBACK; en lugar de COMMIT.


-- ============================================================
-- OPCIONAL (correr después, si quieres higiene de datos):
-- los 991 en 'nuevo' incluyen leads viejos que nunca avanzaron.
-- Mandarlos a nutrición evita que el agente los trate como recién llegados.
-- ============================================================
-- UPDATE leads
-- SET estado = 'en_nutricion'
-- WHERE estado IN ('nuevo', 'en_seguimiento')
--   AND (ultimo_mensaje_at IS NULL OR ultimo_mensaje_at < now() - interval '45 days');
