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

CATALOGO_URL = "https://dermicapro.app/api/public/catalog"


def precios_del_catalogo():
    """Precios vigentes del catálogo (la MISMA fuente que usa la tool 'precios').

    Sin esto el tester solo comprueba que aparezca 'S/', no que la cifra sea real:
    un modelo que no llame a la tool e invente 'S/ 350' pasaría los 40 casos. Es el
    fallo más caro del sistema (cotizar mal), así que se valida contra la fuente.
    """
    try:
        with urllib.request.urlopen(CATALOGO_URL, timeout=30) as r:
            data = json.loads(r.read())
    except Exception as e:
        print(f"⚠️  no se pudo leer el catálogo ({e}): las cifras NO se validarán")
        return None
    items = data.get("data", data if isinstance(data, list) else [])
    precios = set()
    for it in items:
        for p in it.get("packages", []):
            if p.get("price") is not None:
                precios.add(int(float(p["price"])))
    # el adelanto/consulta es una constante operativa del prompt, no del catálogo
    precios.add(50)
    return precios or None


PRECIOS_VALIDOS = precios_del_catalogo()


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

    # --- CIFRAS INVENTADAS: toda cifra cotizada debe existir en el catálogo real ---
    # (detecta que el agente NO llamó a la tool 'precios' y alucinó el número).
    # NO se validan las ANCLAS (~S/ 540~): el prompt pide mostrar lo que valdría
    # suelto, que es un cálculo (n sesiones × precio unitario) y no un ítem del
    # catálogo. Por eso se saltan las cifras tachadas y se aceptan los múltiplos.
    if PRECIOS_VALIDOS:
        for i, t in enumerate(textos, 1):
            tachados = {m.group(1) for m in re.finditer(r"~[^~]*S/\s?(\d[\d.,]*)[^~]*~", t)}
            for m in re.finditer(r"S/\s?(\d[\d.,]*)", t):
                crudo = m.group(1)
                if crudo in tachados:
                    continue  # es un ancla tachada, no una cotización
                try:
                    cifra = int(float(crudo.replace(",", "")))
                except ValueError:
                    continue
                if cifra in PRECIOS_VALIDOS:
                    continue
                # ancla sin tachar: n sesiones × un precio del catálogo (n de 2 a 12)
                if any(cifra % p == 0 and 2 <= cifra // p <= 12 for p in PRECIOS_VALIDOS if p):
                    continue
                fallos.append(
                    f"sugerencia {i}: cifra INVENTADA 'S/ {cifra}' — no existe en el catálogo "
                    f"(¿no llamó a la tool 'precios'?)")

    # --- Reglas globales de formato (aplican a TODOS los casos) ---
    for i, t in enumerate(textos, 1):
        if "**" in t:
            fallos.append(f"sugerencia {i}: negrita markdown ** (WhatsApp usa UN asterisco)")
        tono = [c for c in t if c in EMOJIS_TONO]
        if len(tono) > 1:
            fallos.append(f"sugerencia {i}: {len(tono)} emojis de tono (máximo 1)")
        if re.search(r"S/\s?\d[\d.,]*\s?[" + EMOJIS_TONO + EMOJIS_FUNCIONALES + "]", t):
            fallos.append(f"sugerencia {i}: emoji pegado a la cifra del precio (el precio va limpio)")
        prohibidos = [c for c in t if c in EMOJIS_PROHIBIDOS]
        if prohibidos:
            fallos.append(f"sugerencia {i}: emojis fuera de paleta {prohibidos}")
    ids_recursos = {r["id"] for r in caso.get("recursos", [])}
    algun_adjunto = False
    for s in sugerencias:
        if s.get("canal") not in ("texto", "audio", None):
            fallos.append(f"canal inválido: {s.get('canal')}")
        adjuntos = s.get("adjuntos") or []
        algun_adjunto = algun_adjunto or bool(adjuntos)
        # (si el caso no define recursos, los adjuntos no se validan: el nodo 'flyers'
        #  del flujo real inyecta recursos de media_assets que el caso no conoce)
        for a in adjuntos:
            if ids_recursos and a not in ids_recursos:
                fallos.append(f"adjunto '{a}' no existe en recursos_disponibles del caso")
    if ch.get("debe_adjuntar") and not algun_adjunto:
        fallos.append("se esperaba al menos un adjunto de recursos_disponibles y no vino ninguno")

    return fallos, alerta


def payload_de(caso):
    lead = dict(caso["lead"])
    lead["ultimo_mensaje_at"] = "2026-07-21T10:00:00-05:00"
    lead["horas_desde_ultimo_mensaje"] = caso.get("antiguedad_horas", 1)
    lead["indicacion_vendedor"] = caso.get("indicacion_vendedor", "")
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
        # La indicación del vendedor es una entrada del frontend por generación (no vive
        # en la BD): el webhook del flujo la recibe como query param 'instruction'.
        params = {"chat_id": jid}
        if caso.get("indicacion_vendedor"):
            params["instruction"] = caso["indicacion_vendedor"]
        try:
            with urllib.request.urlopen(url + "?" + urllib.parse.urlencode(params), timeout=180) as r:
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
