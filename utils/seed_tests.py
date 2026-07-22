#!/usr/bin/env python3
"""Siembra los 12 casos de utils/tests-copiloto.json en la BD real (leads + wsp_messages)
para probar el copiloto por el camino de producción (el webhook lee de la BD).

Uso:
  PG_HOST=... PG_PORT=... PG_DB=... PG_USER=... PG_PASS=... python3 utils/seed_tests.py          # sembrar
  PG_HOST=... PG_PORT=... PG_DB=... PG_USER=... PG_PASS=... python3 utils/seed_tests.py --clean  # limpiar TODO rastro

Los leads de prueba usan números 51999000001-12 (prefijo '51999000'): imposibles de
confundir con reales, y la limpieza borra por ese prefijo en ambas tablas.
"""
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pg8000.native as pg

RAIZ = Path(__file__).resolve().parent
ARCHIVO = next((a for a in sys.argv[1:] if a.endswith(".json")), str(RAIZ / "tests-copiloto.json"))
CASOS = json.loads(Path(ARCHIVO).read_text(encoding="utf-8"))
PREFIJO = CASOS[0]["lead"]["remote_jid"][:8]  # ej. 51999000 (copiloto) / 51888000 (analista)
TZ = timezone(timedelta(hours=-5))  # Perú


def conectar():
    return pg.Connection(
        os.environ.get("PG_USER", "postgres"),
        host=os.environ["PG_HOST"],
        port=int(os.environ.get("PG_PORT", "5432")),
        database=os.environ.get("PG_DB", "postgres"),
        password=os.environ["PG_PASS"],
    )


def limpiar(c):
    n1 = c.run(f"DELETE FROM wsp_messages WHERE chat_id LIKE '{PREFIJO}%'")
    n2 = c.run(f"DELETE FROM leads WHERE remote_jid LIKE '{PREFIJO}%'")
    print("limpieza: mensajes y leads de prueba eliminados")


def jid_de(caso, sufijo):
    # respeta el formato real de la BD (con o sin @s.whatsapp.net)
    base = caso["lead"]["remote_jid"].split("@")[0]
    return base + sufijo


def sembrar(c):
    # ¿el formato real lleva @s.whatsapp.net?
    ej = c.run("SELECT remote_jid FROM leads WHERE remote_jid NOT LIKE :pref LIMIT 1", pref=PREFIJO + "%")
    sufijo = "@s.whatsapp.net" if (ej and "@" in ej[0][0]) else ""
    # valores válidos del enum tipo_objecion (si existe)
    tipos_validos = {r[0] for r in c.run(
        "SELECT e.enumlabel FROM pg_type t JOIN pg_enum e ON t.oid=e.enumtypid "
        "WHERE t.typname IN (SELECT udt_name FROM information_schema.columns "
        "WHERE table_name='leads' AND column_name='tipo_objecion')")}

    limpiar(c)
    ahora = datetime.now(TZ)
    for caso in CASOS:
        lead = caso["lead"]
        jid = jid_de(caso, sufijo)
        # antigüedad del historial definida por caso (campo "antiguedad_horas"; default 30 min)
        base = ahora - timedelta(hours=caso.get("antiguedad_horas", 0.5))
        tipo_obj = lead.get("tipo_objecion")
        if tipo_obj not in tipos_validos:
            tipo_obj = None
        c.run(
            """INSERT INTO leads (remote_jid, nombre, estado, tipo_objecion, servicio_interes,
                                  origen, ultimo_emisor, ultimo_mensaje_at, notas, metadata,
                                  con_especialista, contador_noshow, proxima_cita)
               VALUES (:jid, :nombre, :estado, :tipo, :serv, 'TEST', :emisor, :fecha, :notas,
                       '{}'::jsonb, :espec, :noshow, :cita)""",
            jid=jid, nombre=lead.get("nombre"), estado=lead["estado"], tipo=tipo_obj,
            serv=lead.get("servicio_interes"), emisor=lead.get("ultimo_emisor", "cliente"),
            fecha=base + timedelta(minutes=len(caso["historial"])),
            notas=lead.get("notas"), espec=lead.get("con_especialista", False),
            noshow=lead.get("contador_noshow", 0), cita=lead.get("proxima_cita"),
        )
        historial = caso["historial"]
        if "--sin-ultimo" in sys.argv:
            historial = historial[:-1]  # el último mensaje lo enviará el tester por el webhook
        for i, msg in enumerate(historial):
            c.run(
                """INSERT INTO wsp_messages (chat_id, content, sent_at, sender, status)
                   VALUES (:chat, :content, :fecha, :sender, 'delivered')""",
                chat=jid, content=msg["texto"], fecha=base + timedelta(minutes=i),
                sender=msg["rol"],
            )
        print(f"[{caso['id']:2}] sembrado {jid} ({lead['estado']}) — {len(caso['historial'])} mensajes")
    print(f"\nOK: {len(CASOS)} casos sembrados. Sufijo jid: '{sufijo or '(sin @)'}'")


if __name__ == "__main__":
    con = conectar()
    if "--clean" in sys.argv:
        limpiar(con)
    else:
        sembrar(con)
    con.close()
