#!/usr/bin/env python3
"""Tester del nodo Code 'Vaciar a null' (utils/vaciar-a-null.js).

Corre el JS REAL del nodo — el mismo archivo que se pega en n8n — con el
JavaScriptCore que trae macOS, así que no hace falta node ni red ni API key.

Cubre lo que ninguna suite cubría (ver "Lección" en prompts/agente-analista-leads.md):
el CONTRATO de salida. El prompt ya no puede devolver null (el schema de function
calling de Gemini no acepta union types), así que todo campo vacío llega como el
centinela "no_especificado" y ESTE nodo es el único que lo vuelve a null antes
del UPDATE. Si se rompe, se escriben strings basura en la tabla `leads`.

USO
  python3 utils/test_vaciar_null.py          # 24 casos, ~1 s
  python3 utils/test_vaciar_null.py -v       # imprime la salida de cada caso

Para validar el camino completo (modelo real + schema + este nodo):
  utils/test_analista_contrato.py
"""
import json
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
NODO = RAIZ / "utils" / "vaciar-a-null.js"
JSC = Path("/System/Library/Frameworks/JavaScriptCore.framework/Versions/A/Helpers/jsc")

# Salida completa y "limpia" del agente: la base para mutar campo por campo.
BASE = {
    "razonamiento": "Señal de compra sin adelanto: sigue en oferta.",
    "nombre": "Ana",
    "telefono": "no_especificado",
    "estado": "oferta_presentada",
    "tipo_objecion": "no_especificado",
    "servicio_interes": "Hollywood Peel",
    "razon_perdido": "no_especificado",
    "fecha_recontacto": "no_especificado",
    "proxima_cita": "no_especificado",
    "con_especialista": False,
    "notas": "Falta el adelanto de S/ 50. Pedir Yape.",
}


def caso(nombre, cambios, espera=None, error=None, crudo=None):
    """espera: subconjunto de output que debe cumplirse. error: substring del throw."""
    entrada = crudo if crudo is not None else {"output": {**BASE, **cambios}}
    return {"nombre": nombre, "entrada": entrada, "espera": espera or {}, "error": error}


CASOS = [
    # --- el centinela nuevo, que es el motivo de este nodo -------------------
    caso("centinela del prompt en los 7 campos opcionales", {},
         {"telefono": None, "tipo_objecion": None, "razon_perdido": None,
          "fecha_recontacto": None, "proxima_cita": None,
          "nombre": "Ana", "servicio_interes": "Hollywood Peel"}),
    caso("nombre con el centinela", {"nombre": "no_especificado"}, {"nombre": None}),
    caso("servicio con el centinela", {"servicio_interes": "no_especificado"},
         {"servicio_interes": None}),
    caso("variante con mayúsculas y punto", {"nombre": "No Especificado."}, {"nombre": None}),
    caso("variante con espacio en vez de guión bajo", {"nombre": "no especificado"},
         {"nombre": None}),
    caso("variante con tilde (ningún)", {"servicio_interes": "Ningún"},
         {"servicio_interes": None}),
    caso("el null viejo, por si el modelo recae", {"nombre": None}, {"nombre": None}),
    caso("string 'null' literal", {"servicio_interes": "null"}, {"servicio_interes": None}),
    caso("cadena vacía", {"nombre": ""}, {"nombre": None}),
    caso("un nombre real NO se vacía", {"nombre": "María Fernanda"},
         {"nombre": "María Fernanda"}),
    caso("un servicio real conserva sus tildes", {"servicio_interes": "Depilación Láser"},
         {"servicio_interes": "Depilación Láser"}),

    # --- reglas de coherencia -----------------------------------------------
    caso("tipo_objecion válido en en_objecion",
         {"estado": "en_objecion", "tipo_objecion": "concreto"},
         {"estado": "en_objecion", "tipo_objecion": "concreto"}),
    caso("tipo_objecion se descarta fuera de en_objecion",
         {"estado": "agendado", "tipo_objecion": "concreto"}, {"tipo_objecion": None}),
    caso("tipo_objecion inventado se descarta",
         {"estado": "en_objecion", "tipo_objecion": "precio"}, {"tipo_objecion": None}),
    caso("razon_perdido se conserva en descalificado",
         {"estado": "descalificado", "razon_perdido": "lactancia"},
         {"razon_perdido": "lactancia"}),
    caso("razon_perdido se descarta fuera de perdido/descalificado",
         {"estado": "en_diagnostico", "razon_perdido": "precio"}, {"razon_perdido": None}),
    caso("proxima_cita se conserva en agendado",
         {"estado": "agendado", "proxima_cita": "2026-07-25T15:00:00-05:00"},
         {"proxima_cita": "2026-07-25T15:00:00-05:00"}),
    caso("proxima_cita se descarta si no es agendado (cita fabricada)",
         {"proxima_cita": "2026-07-25T15:00:00-05:00"}, {"proxima_cita": None}),
    caso("fecha_recontacto se recorta a YYYY-MM-DD",
         {"fecha_recontacto": "2026-11-01T00:00:00-05:00"}, {"fecha_recontacto": "2026-11-01"}),
    caso("fecha imposible (31 de febrero) no llega a Postgres",
         {"fecha_recontacto": "2026-02-31"}, {"fecha_recontacto": None}),
    caso("fecha en prosa se descarta", {"fecha_recontacto": "en noviembre"},
         {"fecha_recontacto": None}),

    # --- teléfono, boolean, estado ------------------------------------------
    caso("teléfono con formato queda en dígitos", {"telefono": "+51 987 654 321"},
         {"telefono": "51987654321"}),
    caso("teléfono basura corto se descarta", {"telefono": "123"}, {"telefono": None}),
    caso("con_especialista como string 'true'", {"con_especialista": "true"},
         {"con_especialista": True}),
    caso("con_especialista con el centinela cae a false",
         {"con_especialista": "no_especificado"}, {"con_especialista": False}),
    caso("estado con mayúsculas y tilde se normaliza", {"estado": "En Diagnóstico"},
         {"estado": "en_diagnostico"}),
    caso("estado inventado corta la ejecución (nunca un estado por defecto)",
         {"estado": "interesado"}, error="Estado invalido"),
    caso("estado con el centinela también corta", {"estado": "no_especificado"},
         error="Estado invalido"),

    # --- forma del item -----------------------------------------------------
    caso("output como string JSON (parser desactivado)", {},
         {"estado": "oferta_presentada", "telefono": None},
         crudo={"output": json.dumps(BASE, ensure_ascii=False)}),
    caso("output envuelto en ```json", {}, {"estado": "oferta_presentada"},
         crudo={"output": "```json\n" + json.dumps(BASE, ensure_ascii=False) + "\n```"}),
    caso("item sin wrapper output", {}, {"estado": "oferta_presentada", "nombre": "Ana"},
         crudo=dict(BASE)),
]

SHIM = """
const __items = %s;
const $input = { all: function () { return __items; } };
try {
  const __r = (function () { %s })();
  print(JSON.stringify({ ok: __r }));
} catch (e) {
  print(JSON.stringify({ error: String(e && e.message ? e.message : e) }));
}
"""


def correr(items):
    """Corre el nodo real con estos items y devuelve (salida, error)."""
    codigo = SHIM % (json.dumps(items, ensure_ascii=False), NODO.read_text(encoding="utf-8"))
    r = subprocess.run([str(JSC), "-e", codigo], capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        return None, f"jsc falló: {(r.stderr or r.stdout).strip()[:300]}"
    d = json.loads(r.stdout.strip().splitlines()[-1])
    return d.get("ok"), d.get("error")


def main():
    verboso = "-v" in sys.argv
    if not JSC.exists():
        sys.exit(f"No encuentro jsc en {JSC} (este tester usa el JS real del nodo).")
    if not NODO.exists():
        sys.exit(f"No encuentro {NODO}")

    # Un solo proceso jsc con TODOS los items: además prueba el batch (n8n puede
    # mandar varios mensajes juntos) y hace la corrida instantánea.
    lote = [{"json": c["entrada"]} for c in CASOS if not c["error"]]
    salida_lote, err_lote = correr(lote)
    if err_lote:
        print(f"❌ el lote completo tiró error: {err_lote}")
        return 1
    if len(salida_lote) != len(lote):
        print(f"❌ el nodo devolvió {len(salida_lote)} items para {len(lote)} de entrada")
        return 1

    fallos, i = [], 0
    for c in CASOS:
        if c["error"]:
            _, err = correr([{"json": c["entrada"]}])
            ok = err is not None and c["error"] in err
            detalle = f"esperaba throw con {c['error']!r}, obtuve {err!r}"
        else:
            got = salida_lote[i]["json"]["output"]
            i += 1
            malos = {k: (v, got.get(k)) for k, v in c["espera"].items() if got.get(k) != v}
            ok = not malos
            detalle = "; ".join(f"{k}: esperaba {e!r}, obtuve {g!r}" for k, (e, g) in malos.items())
            if verboso:
                print(f"    {json.dumps(got, ensure_ascii=False)}")
        print(f"{'✅' if ok else '❌'} {c['nombre']}" + ("" if ok else f"\n     → {detalle}"))
        if not ok:
            fallos.append(c["nombre"])

    print(f"\n=== nodo 'Vaciar a null': {len(CASOS) - len(fallos)}/{len(CASOS)} ===")
    for f in fallos:
        print(f"  · {f}")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
