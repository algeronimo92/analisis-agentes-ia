#!/usr/bin/env python3
"""Exporta una conversación real de la BD en el formato que espera el auditor.

USO
  python3 utils/exportar_conversacion.py --listar [estado]
      Lista leads con su conteo de mensajes (opcionalmente filtrado por estado).
  python3 utils/exportar_conversacion.py 51982066896
      Imprime el payload de auditoría (lead + historial) de ese chat.
      Acepta el número solo o el remote_jid completo (...@s.whatsapp.net).
  python3 utils/exportar_conversacion.py 51982066896 --guardar
      Además lo guarda en auditorias/payload-<numero>.json

Requiere DATABASE_URL en .env (raíz del proyecto) y el paquete pg8000.
"""
import json
import re
import sys
from pathlib import Path

import pg8000.native

RAIZ = Path(__file__).resolve().parent.parent


def conectar():
    env = (RAIZ / ".env").read_text(encoding="utf-8")
    url = next(l.split("=", 1)[1].strip() for l in env.splitlines() if l.startswith("DATABASE_URL"))
    m = re.match(r"postgres(?:ql)?://([^:]+):([^@]+)@([^:/]+):(\d+)/(.+)", url)
    user, pwd, host, port, db = m.groups()
    return pg8000.native.Connection(user, host=host, port=int(port), database=db, password=pwd, timeout=20)


def listar(con, estado=None):
    filtro = "WHERE l.estado = :estado" if estado else ""
    filas = con.run(f"""
        SELECT l.remote_jid, l.estado, l.servicio_interes, l.ultimo_mensaje_at::date, count(w.id) AS n
        FROM leads l LEFT JOIN wsp_messages w ON w.chat_id = l.remote_jid
        {filtro}
        GROUP BY 1,2,3,4
        HAVING count(w.id) >= 4
        ORDER BY l.ultimo_mensaje_at DESC NULLS LAST
        LIMIT 40""", estado=estado)
    print(f"{'chat':<32} {'estado':<18} {'servicio':<22} {'último':<12} msgs")
    for jid, est, serv, fecha, n in filas:
        print(f"{jid.split('@')[0]:<32} {est or '':<18} {(serv or '')[:22]:<22} {str(fecha or ''):<12} {n}")


def exportar(con, chat):
    jid = chat if "@" in chat else chat + "@s.whatsapp.net"
    lead = con.run("""
        SELECT remote_jid, nombre, estado, tipo_objecion, servicio_interes, razon_perdido,
               notas, con_especialista, contador_noshow, proxima_cita, ultimo_emisor, ultimo_mensaje_at
        FROM leads WHERE remote_jid = :jid""", jid=jid)
    if not lead:
        sys.exit(f"No existe el lead {jid}")
    cols = ("remote_jid", "nombre", "estado", "tipo_objecion", "servicio_interes", "razon_perdido",
            "notas", "con_especialista", "contador_noshow", "proxima_cita", "ultimo_emisor", "ultimo_mensaje_at")
    payload = {c: (v.isoformat() if hasattr(v, "isoformat") else v) for c, v in zip(cols, lead[0])}
    mensajes = con.run("""
        SELECT sender, sent_at, content, media_url
        FROM wsp_messages WHERE chat_id = :jid
        ORDER BY sent_at ASC""", jid=jid)
    payload["data"] = [
        {
            "rol": s,
            "fecha": f.isoformat() if f else None,
            "texto": (c or "") + (" [adjunto]" if u and not c else ""),
        }
        for s, f, c, u in mensajes
    ]
    transiciones = con.run("""
        SELECT old_value->>'stage', new_value->>'stage', actor_type,
               metadata->>'reason', metadata->'trigger_message'->>'content', created_at
        FROM lead_activity
        WHERE lead_id = :jid AND event_type = 'stage_changed'
        ORDER BY created_at ASC""", jid=jid)
    payload["transiciones"] = [
        {
            "de": de,
            "a": a,
            "actor": actor,
            "razonamiento": razon,
            "mensaje_disparador": disparador,
            "fecha": f.isoformat() if f else None,
        }
        for de, a, actor, razon, disparador, f in transiciones
    ]
    return payload


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return
    con = conectar()
    try:
        if args[0] == "--listar":
            listar(con, args[1] if len(args) > 1 else None)
            return
        payload = exportar(con, args[0])
        texto = json.dumps(payload, ensure_ascii=False, indent=1)
        print(texto)
        if "--guardar" in args:
            destino = RAIZ / "auditorias"
            destino.mkdir(exist_ok=True)
            ruta = destino / f"payload-{args[0].split('@')[0]}.json"
            ruta.write_text(texto, encoding="utf-8")
            print(f"\n[guardado en {ruta.relative_to(RAIZ)}]", file=sys.stderr)
    finally:
        con.close()


if __name__ == "__main__":
    main()
