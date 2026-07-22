#!/usr/bin/env python3
"""Tester del agente copiloto de ventas (n8n).

Valida que las sugerencias cumplan las expectativas del sistema
(matriz de precio, adelanto, contraindicaciones, baja, emojis, formato WhatsApp).

MODOS DE USO
1. Automático (si el workflow tiene un Webhook de prueba):
     N8N_WEBHOOK_URL="https://tu-n8n/webhook/test-copiloto" python3 utils/test_copiloto.py
   POSTea cada caso y valida la respuesta JSON del agente.

2. Manual (sin webhook):
     python3 utils/test_copiloto.py --payload 3
   Imprime el JSON del caso 3 para pegarlo como "pin data" / mock en n8n.
   Luego guarda la respuesta del agente en un archivo y valida:
     python3 utils/test_copiloto.py --check 3 respuesta.json

Los casos viven en utils/tests-copiloto.json (edítalos o agrega más ahí).
"""
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
CASOS = json.loads((RAIZ / "tests-copiloto.json").read_text(encoding="utf-8"))

EMOJIS_TONO = "😊🙂✨🌟🤍🎉"
EMOJIS_FUNCIONALES = "✅📸👇📅📍⏰🧴💧💆"
EMOJIS_PROHIBIDOS = "💚❤️💕💖🎀🫧🧸😘😉🥳😂🙌😄💪🙏😔🔥📌🎯👌"


def validar(caso, respuesta):
    """Devuelve lista de fallos (vacía = PASS)."""
    fallos = []
    ch = caso["checks"]
    # n8n a veces envuelve la salida
    if isinstance(respuesta, dict) and "output" in respuesta and isinstance(respuesta["output"], dict):
        respuesta = respuesta["output"]

    # --- Estructura ---
    for campo in ("analisis", "confianza", "senal_compra", "sugerencias"):
        if campo not in respuesta:
            fallos.append(f"falta el campo '{campo}' (¿parser/prompt desactualizado?)")
    if "señal_compra" in respuesta:
        fallos.append("clave 'señal_compra' con ñ — el parser espera 'senal_compra'")
    sugerencias = respuesta.get("sugerencias", [])
    if not isinstance(sugerencias, list):
        fallos.append("'sugerencias' no es una lista")
        sugerencias = []
    alerta = respuesta.get("alerta")
    if isinstance(alerta, list):
        fallos.append("'alerta' es una LISTA — debe ser string o null")

    # --- Checks del caso ---
    if isinstance(respuesta.get("senal_compra"), str):
        fallos.append("senal_compra es STRING (\"true\") — debe ser booleano sin comillas")
    elif "senal_compra" in ch and respuesta.get("senal_compra") != ch["senal_compra"]:
        fallos.append(f"senal_compra={respuesta.get('senal_compra')} (esperado {ch['senal_compra']})")
    if ch.get("alerta_requerida") and not alerta:
        fallos.append("se esperaba ALERTA para el vendedor y vino null")
    if not ch.get("alerta_requerida") and alerta:
        pass  # alerta extra no es fallo, solo se reporta
    if "max_sugerencias" in ch and len(sugerencias) > ch["max_sugerencias"]:
        fallos.append(f"{len(sugerencias)} sugerencias (máximo esperado {ch['max_sugerencias']})")
    if len(sugerencias) > 3:
        fallos.append("más de 3 sugerencias")

    textos = [s.get("texto", "") for s in sugerencias]
    todo = "\n".join(textos)

    if ch.get("sin_cifras") and re.search(r"S/\s?\d", todo):
        fallos.append("contiene una CIFRA de precio y el caso exige valor-primero sin cifra")
    for kw in ch.get("texto_debe", []):
        if kw.lower() not in todo.lower():
            fallos.append(f"ninguna sugerencia contiene '{kw}'")
    if ch.get("texto_debe_alguno") and not any(k.lower() in todo.lower() for k in ch["texto_debe_alguno"]):
        fallos.append(f"no contiene ninguno de {ch['texto_debe_alguno']}")
    for kw in ch.get("texto_no_debe", []):
        if kw.lower() in todo.lower():
            fallos.append(f"contiene '{kw}' (prohibido en este caso)")
    if ch.get("precio_al_final"):
        for t in textos:
            m = list(re.finditer(r"S/\s?\d", t))
            if m and m[0].start() < len(t) * 0.4:
                fallos.append("el precio aparece al INICIO del mensaje (debe ir al final, tras la pila de valor)")
    if ch.get("termina_en_pregunta") and textos and not any(t.rstrip().rstrip("*_ ").endswith("?") for t in textos):
        fallos.append("ninguna sugerencia termina en pregunta")

    # --- Reglas globales de formato (aplican a TODOS los casos) ---
    for i, t in enumerate(textos, 1):
        if "**" in t:
            fallos.append(f"sugerencia {i}: negrita markdown ** (WhatsApp usa UN asterisco)")
        tono = [c for c in t if c in EMOJIS_TONO]
        if len(tono) > 2:
            fallos.append(f"sugerencia {i}: {len(tono)} emojis de tono (máximo 1-2)")
        prohibidos = [c for c in t if c in EMOJIS_PROHIBIDOS]
        if prohibidos:
            fallos.append(f"sugerencia {i}: emojis fuera de paleta {prohibidos}")
    for s in sugerencias:
        # (los adjuntos no se validan aquí: el nodo 'flyers' del flujo real inyecta
        #  recursos de media_assets que el caso de prueba no conoce)
        if s.get("canal") not in ("texto", "audio", None):
            fallos.append(f"canal inválido: {s.get('canal')}")

    return fallos, alerta


def payload_de(caso):
    lead = dict(caso["lead"])
    lead["ultimo_mensaje_at"] = "2026-07-21T10:00:00-05:00"
    lead["recursos"] = caso.get("recursos", [])
    lead["data"] = caso["historial"]
    return lead


def reportar(caso, fallos, alerta):
    estado = "✅ PASS" if not fallos else "❌ FAIL"
    print(f"\n[{caso['id']:2}] {estado} — {caso['nombre']}")
    for f in fallos:
        print(f"      · {f}")
    if alerta and not fallos:
        print(f"      (alerta emitida: {str(alerta)[:80]})")


def main():
    args = sys.argv[1:]
    if args and args[0] == "--payload":
        caso = next(c for c in CASOS if c["id"] == int(args[1]))
        print(json.dumps(payload_de(caso), ensure_ascii=False, indent=2))
        return
    if args and args[0] == "--check":
        caso = next(c for c in CASOS if c["id"] == int(args[1]))
        respuesta = json.loads(Path(args[2]).read_text(encoding="utf-8"))
        fallos, alerta = validar(caso, respuesta)
        reportar(caso, fallos, alerta)
        return

    url = os.environ.get("N8N_WEBHOOK_URL")
    if not url:
        print(__doc__)
        print("Casos disponibles:")
        for c in CASOS:
            print(f"  {c['id']:2}. {c['nombre']}")
        return

    # El flujo real lee de la BD: sembrar antes con seed_tests.py.
    # Se invoca por GET con ?chat_id=<jid> (así lo espera el nodo 'get lead').
    import urllib.parse
    aprobados = 0
    for caso in CASOS:
        jid = caso["lead"]["remote_jid"].split("@")[0] + "@s.whatsapp.net"
        try:
            with urllib.request.urlopen(url + "?chat_id=" + urllib.parse.quote(jid), timeout=180) as r:
                respuesta = json.loads(r.read())
        except Exception as e:
            reportar(caso, [f"error llamando al webhook: {e}"], None)
            continue
        if isinstance(respuesta, list) and respuesta:
            respuesta = respuesta[0]
        fallos, alerta = validar(caso, respuesta)
        reportar(caso, fallos, alerta)
        aprobados += (not fallos)
    print(f"\n=== {aprobados}/{len(CASOS)} casos aprobados ===")


if __name__ == "__main__":
    main()
