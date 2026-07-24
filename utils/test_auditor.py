#!/usr/bin/env python3
"""Tester del agente auditor de conversaciones (n8n).

Valida que la auditoría cumpla las expectativas del sistema
(estructura del parser, cumplimiento duro, etiquetas, citas reales del historial,
coherencia auditable/puntajes).

MODOS DE USO
1. Automático (si el workflow tiene un Webhook de prueba):
     N8N_WEBHOOK_URL="https://tu-n8n/webhook/test-auditor" python3 utils/test_auditor.py
   POSTea cada caso y valida la respuesta JSON del agente.

2. Manual (sin webhook):
     python3 utils/test_auditor.py --payload 1
   Imprime el JSON del caso 1 para pegarlo como "pin data" / mock en n8n
   (o para auditarlo a mano con el subagente local de Claude Code).
   Luego guarda la respuesta del agente en un archivo y valida:
     python3 utils/test_auditor.py --check 1 respuesta.json

Los casos viven en utils/tests-auditor.json (edítalos o agrega más ahí).
"""
import json
import os
import sys
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
CASOS = json.loads((RAIZ / "tests-auditor.json").read_text(encoding="utf-8"))

DIMENSIONES = {"diagnostico", "precio", "oferta", "objeciones", "cierre_adelanto", "seguimiento_ritmo", "tono_formato"}
ETIQUETAS = {
    "precio_en_frio", "cita_sin_adelanto", "sin_filtro_contraindicaciones",
    "precio_o_descuento_inventado", "garantia_medica", "urgencia_falsa",
    "oferta_sin_pila_valor", "objecion_mal_tratada", "sobre_venta_tras_si",
    "consultoria_gratis", "respuesta_tardia", "seguimiento_ausente",
    "toque_sin_valor_nuevo", "muro_de_texto", "emoji_fuera_de_paleta",
    "presion_excesiva", "cross_sell_perdido", "no_respeto_baja", "ninguna",
}
GRAVEDADES = {"critica", "media", "menor"}
VEREDICTOS = {"correcta", "incorrecta", "dudosa"}
CAMPOS = (
    "razonamiento", "auditable", "puntaje_global", "dimensiones", "cumplimiento",
    "momento_critico", "aciertos", "errores", "etiquetas", "experto_recomendado",
    "transiciones_auditadas", "alerta_sistema", "resumen_coaching",
)


def _citas_de(respuesta):
    """Todas las citas textuales que el auditor afirma haber copiado del chat."""
    citas = []
    for e in respuesta.get("errores") or []:
        citas.append(e.get("cita", ""))
    for a in respuesta.get("aciertos") or []:
        citas.append(a.get("cita", ""))
    mc = respuesta.get("momento_critico")
    if isinstance(mc, dict):
        citas.append(mc.get("cita", ""))
    return [c for c in citas if c]


def validar(caso, respuesta):
    """Devuelve lista de fallos (vacía = PASS)."""
    fallos = []
    ch = caso["checks"]
    # n8n a veces envuelve la salida
    if isinstance(respuesta, dict) and "output" in respuesta and isinstance(respuesta["output"], dict):
        respuesta = respuesta["output"]

    # --- Estructura ---
    for campo in CAMPOS:
        if campo not in respuesta:
            fallos.append(f"falta el campo '{campo}' (¿parser/prompt desactualizado?)")
    if fallos:
        return fallos

    auditable = respuesta.get("auditable")
    if isinstance(auditable, str):
        fallos.append("auditable es STRING — debe ser booleano sin comillas")
        auditable = auditable == "true"

    puntaje = respuesta.get("puntaje_global")
    dims = respuesta.get("dimensiones") or []
    cumplimiento = respuesta.get("cumplimiento") or {}
    etiquetas = respuesta.get("etiquetas") or []
    errores = respuesta.get("errores") or []
    aciertos = respuesta.get("aciertos") or []

    # --- Coherencia auditable=false ---
    if auditable is False:
        if puntaje is not None:
            fallos.append("auditable=false pero puntaje_global no es null")
        if dims:
            fallos.append("auditable=false pero hay dimensiones puntuadas")
        if respuesta.get("resumen_coaching"):
            fallos.append("auditable=false pero hay resumen_coaching")
    else:
        if not isinstance(puntaje, int) or not 1 <= puntaje <= 10:
            fallos.append(f"puntaje_global={puntaje!r} — debe ser entero 1-10")
        if not dims:
            fallos.append("auditable=true sin dimensiones")
        if not respuesta.get("resumen_coaching"):
            fallos.append("auditable=true sin resumen_coaching")

    # --- Dimensiones ---
    vistas = set()
    for d in dims:
        nombre = d.get("dimension")
        if nombre not in DIMENSIONES:
            fallos.append(f"dimensión desconocida: {nombre!r}")
            continue
        if nombre in vistas:
            fallos.append(f"dimensión repetida: {nombre}")
        vistas.add(nombre)
        p = d.get("puntaje")
        if p is not None and (not isinstance(p, int) or not 1 <= p <= 10):
            fallos.append(f"dimensión {nombre}: puntaje {p!r} fuera de 1-10")

    # --- Cumplimiento ---
    aprobado = cumplimiento.get("aprobado")
    violaciones = cumplimiento.get("violaciones") or []
    if aprobado is False and not violaciones:
        fallos.append("cumplimiento reprobado sin violaciones listadas")
    if aprobado is False and isinstance(puntaje, int) and puntaje > 4:
        fallos.append(f"cumplimiento reprobado pero puntaje_global={puntaje} (la regla lo limita a 4)")

    # --- Errores / aciertos / etiquetas ---
    if len(errores) > 5:
        fallos.append(f"{len(errores)} errores (máximo 5)")
    if len(aciertos) > 3:
        fallos.append(f"{len(aciertos)} aciertos (máximo 3)")
    for e in errores:
        if e.get("gravedad") not in GRAVEDADES:
            fallos.append(f"gravedad inválida: {e.get('gravedad')!r}")
    for et in etiquetas:
        if et not in ETIQUETAS:
            fallos.append(f"etiqueta fuera del enum: {et!r}")
    if (errores or not violaciones == []) and etiquetas == ["ninguna"] and errores:
        fallos.append("hay errores reportados pero etiquetas=['ninguna']")

    # --- Anti-alucinación: toda cita debe estar en el historial ---
    # (se exceptúan los marcadores de silencio tipo "(sin mensajes...)")
    todo_el_chat = "\n".join(m["texto"] for m in caso["historial"]).lower()
    for cita in _citas_de(respuesta):
        if cita.strip().startswith("("):
            continue
        recorte = cita.strip().strip('"').strip("…").strip("...")[:40].lower()
        if recorte and recorte not in todo_el_chat:
            fallos.append(f"cita no encontrada en el historial: '{cita[:50]}'")

    # --- Auditoría de transiciones ---
    trans_caso = caso.get("transiciones", [])
    trans_resp = respuesta.get("transiciones_auditadas") or []
    if len(trans_resp) != len(trans_caso):
        fallos.append(f"{len(trans_resp)} transiciones auditadas (el caso trae {len(trans_caso)})")
    for i, t in enumerate(trans_resp):
        if t.get("veredicto") not in VEREDICTOS:
            fallos.append(f"transición {i+1}: veredicto inválido {t.get('veredicto')!r}")
        if i < len(trans_caso) and (t.get("de") != trans_caso[i]["de"] or t.get("a") != trans_caso[i]["a"]):
            fallos.append(f"transición {i+1}: {t.get('de')}→{t.get('a')} no corresponde a la recibida ({trans_caso[i]['de']}→{trans_caso[i]['a']}) — deben venir en el mismo orden")
    if ch.get("transicion_incorrecta_requerida") and not any(t.get("veredicto") == "incorrecta" for t in trans_resp):
        fallos.append("se esperaba al menos una transición con veredicto 'incorrecta'")
    if ch.get("transiciones_sin_incorrectas") and any(t.get("veredicto") == "incorrecta" for t in trans_resp):
        fallos.append("hay transiciones marcadas 'incorrecta' y el caso las esperaba todas válidas")

    # --- Checks del caso ---
    if "auditable" in ch and auditable != ch["auditable"]:
        fallos.append(f"auditable={auditable} (esperado {ch['auditable']})")
    if "aprobado" in ch and aprobado != ch["aprobado"]:
        fallos.append(f"cumplimiento.aprobado={aprobado} (esperado {ch['aprobado']})")
    if "puntaje_min" in ch and isinstance(puntaje, int) and puntaje < ch["puntaje_min"]:
        fallos.append(f"puntaje_global={puntaje} (mínimo esperado {ch['puntaje_min']})")
    if "puntaje_max" in ch and isinstance(puntaje, int) and puntaje > ch["puntaje_max"]:
        fallos.append(f"puntaje_global={puntaje} (máximo esperado {ch['puntaje_max']})")
    for et in ch.get("etiquetas_debe", []):
        if et not in etiquetas:
            fallos.append(f"falta la etiqueta esperada '{et}'")
    for et in ch.get("etiquetas_no_debe", []):
        if et in etiquetas:
            fallos.append(f"etiqueta '{et}' presente (no debía estarlo)")
    if ch.get("error_critico_requerido") and not any(e.get("gravedad") == "critica" for e in errores):
        fallos.append("se esperaba al menos un error de gravedad 'critica'")
    if ch.get("momento_critico_requerido") and not respuesta.get("momento_critico"):
        fallos.append("se esperaba momento_critico y vino null")
    if ch.get("alerta_sistema_requerida") and not respuesta.get("alerta_sistema"):
        fallos.append("se esperaba alerta_sistema (BD desincronizada) y vino null")
    if "aciertos_min" in ch and len(aciertos) < ch["aciertos_min"]:
        fallos.append(f"{len(aciertos)} aciertos (mínimo esperado {ch['aciertos_min']})")
    if ch.get("experto_alguno"):
        exp = (respuesta.get("experto_recomendado") or {}).get("archivo", "")
        if exp not in ch["experto_alguno"]:
            fallos.append(f"experto_recomendado={exp!r} (se esperaba uno de {ch['experto_alguno']})")
    for nombre, tope in (ch.get("dimension_max") or {}).items():
        d = next((x for x in dims if x.get("dimension") == nombre), None)
        if d is None:
            fallos.append(f"no se puntuó la dimensión '{nombre}' (el caso la exige)")
        elif isinstance(d.get("puntaje"), int) and d["puntaje"] > tope:
            fallos.append(f"dimensión {nombre}={d['puntaje']} (máximo esperado {tope})")
    for nombre, piso in (ch.get("dimension_min") or {}).items():
        d = next((x for x in dims if x.get("dimension") == nombre), None)
        if d is None:
            fallos.append(f"no se puntuó la dimensión '{nombre}' (el caso la exige)")
        elif isinstance(d.get("puntaje"), int) and d["puntaje"] < piso:
            fallos.append(f"dimensión {nombre}={d['puntaje']} (mínimo esperado {piso})")

    return fallos


def payload_de(caso):
    lead = dict(caso["lead"])
    lead["data"] = caso["historial"]
    lead["transiciones"] = caso.get("transiciones", [])
    return lead


def reportar(caso, fallos):
    estado = "✅ PASS" if not fallos else "❌ FAIL"
    print(f"\n[{caso['id']:2}] {estado} — {caso['nombre']}")
    for f in fallos:
        print(f"      · {f}")


def main():
    args = sys.argv[1:]
    if args and args[0] == "--payload":
        caso = next(c for c in CASOS if c["id"] == int(args[1]))
        print(json.dumps(payload_de(caso), ensure_ascii=False, indent=2))
        return
    if args and args[0] == "--check":
        caso = next(c for c in CASOS if c["id"] == int(args[1]))
        respuesta = json.loads(Path(args[2]).read_text(encoding="utf-8"))
        reportar(caso, validar(caso, respuesta))
        return

    url = os.environ.get("N8N_WEBHOOK_URL")
    if not url:
        print(__doc__)
        print("Casos disponibles:")
        for c in CASOS:
            print(f"  {c['id']:2}. {c['nombre']}")
        return

    aprobados = 0
    for caso in CASOS:
        cuerpo = json.dumps(payload_de(caso), ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(url, data=cuerpo, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                respuesta = json.loads(r.read())
        except Exception as e:
            reportar(caso, [f"error llamando al webhook: {e}"])
            continue
        if isinstance(respuesta, list) and respuesta:
            respuesta = respuesta[0]
        fallos = validar(caso, respuesta)
        reportar(caso, fallos)
        aprobados += (not fallos)
    print(f"\n=== {aprobados}/{len(CASOS)} casos aprobados ===")


if __name__ == "__main__":
    main()
