#!/usr/bin/env python3
"""Tester del Agente 1: Analista de leads (clasificador de estados).

Valida las TRANSICIONES del funnel (y cuándo NO transicionar), la taxonomía de
objeciones y la extracción de campos (nombre, teléfono, fechas, derivación).

USO
1. Sembrar los casos en la BD real:
     PG_HOST=... PG_PASS=... python3 utils/seed_tests.py utils/tests-analista.json
2. Correr contra el webhook de prueba del analista (mismo patrón que el copiloto:
   Webhook GET → get lead → get messages → AI Agent analista → Respond to Webhook):
     N8N_ANALISTA_URL="https://.../webhook/xxx" python3 utils/test_analista.py
3. Limpiar al terminar:
     PG_HOST=... PG_PASS=... python3 utils/seed_tests.py utils/tests-analista.json --clean

Casos en utils/tests-analista.json (prefijo de jid 51888000, no choca con el copiloto).
"""
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
CASOS = json.loads((RAIZ / "tests-analista.json").read_text(encoding="utf-8"))

ESTADOS_VALIDOS = {"nuevo", "en_diagnostico", "calificado", "oferta_presentada", "en_objecion",
                   "agendado", "cliente_activo", "postventa", "en_seguimiento", "en_nutricion",
                   "perdido", "descalificado", "baja"}


def validar(caso, r):
    fallos = []
    if isinstance(r, dict) and "output" in r and isinstance(r["output"], dict):
        r = r["output"]
    ch = caso["checks"]
    estado = r.get("estado")

    # --- estructura y tipos ---
    if "razonamiento" not in r and not r.get("_desde_bd"):
        fallos.append("falta 'razonamiento' (debe generarse PRIMERO)")
    if estado not in ESTADOS_VALIDOS:
        fallos.append(f"estado inválido o con tilde/mayúsculas: {estado!r}")
    if estado != "en_objecion" and r.get("tipo_objecion") is not None:
        fallos.append(f"tipo_objecion={r.get('tipo_objecion')!r} debe ser null fuera de en_objecion")
    if estado in ("perdido", "descalificado") and not r.get("razon_perdido"):
        fallos.append(f"estado {estado} sin razon_perdido (es obligatoria)")
    for campo_fecha in ("fecha_recontacto", "proxima_cita"):
        v = r.get(campo_fecha)
        if v and not re.match(r"^\d{4}-\d{2}-\d{2}", str(v)):
            fallos.append(f"{campo_fecha}={v!r} no está en formato ISO")

    # --- checks del caso ---
    if "estado_esperado" in ch and estado != ch["estado_esperado"]:
        fallos.append(f"estado={estado!r} (esperado {ch['estado_esperado']!r})")
    for prohibido in ch.get("estado_prohibido", []):
        if estado == prohibido:
            fallos.append(f"estado={estado!r} está PROHIBIDO en este caso")
    if "tipo_objecion_esperado" in ch and r.get("tipo_objecion") != ch["tipo_objecion_esperado"]:
        fallos.append(f"tipo_objecion={r.get('tipo_objecion')!r} (esperado {ch['tipo_objecion_esperado']!r})")
    if ch.get("proxima_cita_requerida") and not r.get("proxima_cita"):
        fallos.append("proxima_cita vino null (había cita con día+hora y adelanto confirmado)")
    if ch.get("razon_requerida") and not r.get("razon_perdido"):
        fallos.append("razon_perdido vino null y era obligatoria")
    if "fecha_recontacto_contiene" in ch and ch["fecha_recontacto_contiene"] not in str(r.get("fecha_recontacto", "")):
        fallos.append(f"fecha_recontacto={r.get('fecha_recontacto')!r} (esperaba que contenga {ch['fecha_recontacto_contiene']!r})")
    if "nombre_esperado" in ch and ch["nombre_esperado"].lower() not in str(r.get("nombre", "")).lower():
        fallos.append(f"nombre={r.get('nombre')!r} (esperado {ch['nombre_esperado']!r})")
    if "telefono_contiene" in ch and ch["telefono_contiene"] not in str(r.get("telefono", "")):
        fallos.append(f"telefono={r.get('telefono')!r} (esperaba que contenga {ch['telefono_contiene']!r})")
    if "servicio_contiene" in ch and ch["servicio_contiene"].lower() not in str(r.get("servicio_interes", "")).lower():
        fallos.append(f"servicio_interes={r.get('servicio_interes')!r} (esperaba {ch['servicio_contiene']!r})")
    if ch.get("con_especialista_esperado") and not r.get("con_especialista"):
        fallos.append("con_especialista=false (se esperaba true: derivación a especialista)")
    if not r.get("notas") and estado != "baja":  # en baja no hay nada que resumir
        fallos.append("notas vacías (siempre debe resumir qué quiere y la próxima acción)")

    return fallos


def main():
    url = os.environ.get("N8N_ANALISTA_URL")
    if not url:
        print(__doc__)
        print("Casos disponibles:")
        for c in CASOS:
            print(f"  {c['id']:2}. {c['nombre']}")
        return

    from datetime import datetime, timedelta, timezone
    solo = None
    if "--caso" in sys.argv:
        solo = int(sys.argv[sys.argv.index("--caso") + 1])

    LIMA = timezone(timedelta(hours=-5))
    aprobados = 0
    for caso in CASOS:
        if solo and caso["id"] != solo:
            continue
        jid = caso["lead"]["remote_jid"].split("@")[0] + "@s.whatsapp.net"
        # marca de agua: updated_at ANTES del disparo (para detectar updates silenciosamente perdidos)
        marca_previa = None
        if os.environ.get("PG_HOST"):
            import pg8000.native as pg
            _c = pg.Connection(os.environ.get("PG_USER", "postgres"), host=os.environ["PG_HOST"],
                               port=int(os.environ.get("PG_PORT", "5432")),
                               database=os.environ.get("PG_DB", "postgres"), password=os.environ["PG_PASS"])
            _f = _c.run("SELECT updated_at FROM leads WHERE remote_jid = :jid", jid=jid)
            _c.close()
            marca_previa = _f[0][0] if _f else None
        # el último mensaje del historial es el DISPARADOR: va por el webhook con etiqueta <text>
        ultimo = caso["historial"][-1]
        # el flujo interpreta el timestamp (con Z) como hora de Lima → se envía hora Lima + 'Z'
        momento = datetime.now(LIMA) - timedelta(hours=caso.get("antiguedad_horas", 0))
        ts = momento.replace(tzinfo=None).isoformat(timespec="milliseconds") + "Z"
        msg_id = f"TEST-{caso['id']}-{int(datetime.now().timestamp())}"
        payload = {
            "chat_id": jid,
            "content": f"<text>\n{ultimo['texto']}\n</text>",
            "timestamp": ts,
            "media_url": None,
            "origen": "test",
            "wa_message_id": msg_id,
            "status": "delivered",
            "instance": {"chat_id": jid, "message_id": msg_id},
            "message": {
                "from_me": ultimo["rol"] == "vendedor",
                "timestamp": ts,
                "status": "delivered",
                "content": ultimo["texto"],
            },
        }
        req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                     headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                r = json.loads(resp.read())
        except Exception as e:
            print(f"\n[{caso['id']:2}] ❌ FAIL — {caso['nombre']}\n      · error de webhook: {e}")
            continue
        if isinstance(r, list) and r:
            r = r[0]
        # el webhook devuelve la FILA actualizada del lead (salida del update): no trae 'razonamiento'
        if isinstance(r, dict) and "remote_jid" in r:
            r["_desde_bd"] = True
        # si el webhook no devuelve la clasificación, leerla de la BD (la verdad final)
        plano = r.get("output", r) if isinstance(r, dict) else {}
        if not plano.get("estado") and os.environ.get("PG_HOST"):
            import time
            import pg8000.native as pg
            con = pg.Connection(os.environ.get("PG_USER", "postgres"), host=os.environ["PG_HOST"],
                                port=int(os.environ.get("PG_PORT", "5432")),
                                database=os.environ.get("PG_DB", "postgres"), password=os.environ["PG_PASS"])
            fila = None
            for _ in range(18):  # hasta 90 s: el agente corre asíncrono tras responder el webhook
                time.sleep(5)
                fila = con.run("SELECT estado, tipo_objecion, servicio_interes, nombre, telefono, "
                               "razon_perdido, fecha_recontacto, proxima_cita, con_especialista, notas, "
                               "updated_at FROM leads WHERE remote_jid = :jid", jid=jid)
                if fila and (marca_previa is None or fila[0][10] != marca_previa):
                    break
            con.close()
            if fila:
                f = fila[0]
                if marca_previa is not None and f[10] == marca_previa:
                    print(f"\n[{caso['id']:2}] ❌ FAIL — {caso['nombre']}\n      · el UPDATE nunca corrió (updated_at no cambió): el flujo perdió la clasificación en silencio")
                    continue
                r = {"_desde_bd": True, "estado": str(f[0]) if f[0] else None,
                     "tipo_objecion": f[1], "servicio_interes": f[2], "nombre": f[3],
                     "telefono": f[4], "razon_perdido": f[5],
                     "fecha_recontacto": str(f[6]) if f[6] else None,
                     "proxima_cita": str(f[7]) if f[7] else None,
                     "con_especialista": f[8], "notas": f[9]}
        fallos = validar(caso, r)
        estado = "✅ PASS" if not fallos else "❌ FAIL"
        print(f"\n[{caso['id']:2}] {estado} — {caso['nombre']}")
        for f in fallos:
            print(f"      · {f}")
        aprobados += (not fallos)
    print(f"\n=== {aprobados}/{len(CASOS)} casos aprobados ===")


if __name__ == "__main__":
    main()
