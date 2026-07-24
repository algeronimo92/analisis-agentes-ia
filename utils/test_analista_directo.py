#!/usr/bin/env python3
"""Tester DIRECTO del analista: llama a OpenAI sin pasar por n8n.

Replica la configuración de producción del nodo de n8n: gpt-4o-mini,
temperature 0, response_format json_object, prompt_cache_key "analista-leads",
historial "más nuevo arriba". El SYSTEM PROMPT se extrae del archivo
prompts/agente-analista-leads.md (única fuente de verdad) y cada caso se
valida con los mismos checks de test_analista.py.

USO
  OPENAI_API_KEY en el entorno o en .env (raíz del proyecto), luego:
    python3 utils/test_analista_directo.py            # los 29 casos
    python3 utils/test_analista_directo.py --caso 20  # un caso puntual
  Variables opcionales: MODELO (default gpt-4o-mini).

Diferencia con test_analista.py: aquel valida el workflow n8n completo
(webhook + BD + agente); este valida SOLO el prompt contra el modelo — ideal
para iterar el prompt rápido y barato antes de re-pegarlo en n8n.
"""
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from test_analista import CASOS, validar  # mismos casos, mismos checks

RAIZ = Path(__file__).resolve().parent.parent
MODELO = os.environ.get("MODELO", "gpt-4o-mini")


def api_key():
    if os.environ.get("OPENAI_API_KEY"):
        return os.environ["OPENAI_API_KEY"]
    env = RAIZ / ".env"
    if env.exists():
        for linea in env.read_text(encoding="utf-8").splitlines():
            if linea.startswith("OPENAI_API_KEY="):
                return linea.split("=", 1)[1].strip()
    sys.exit("Falta OPENAI_API_KEY (en el entorno o en .env). "
             "Para probar el workflow n8n completo usa test_analista.py con N8N_ANALISTA_URL.")


def system_prompt():
    texto = (RAIZ / "prompts" / "agente-analista-leads.md").read_text(encoding="utf-8")
    inicio = texto.index("```", texto.index("## SYSTEM PROMPT")) + 4
    return texto[inicio:texto.index("\n```", inicio)]


def user_prompt(caso):
    lead = dict(caso["lead"])
    historial = list(reversed(caso["historial"]))  # producción: más nuevo arriba
    return (
        "<lead>\nEstado e información del lead (incluye su estado actual):\n"
        + json.dumps(lead, ensure_ascii=False)
        + "\n</lead>\n\n<datos_temporales>\n- Fecha y hora actual: "
        + datetime.now(timezone.utc).astimezone().isoformat()
        + "\n- Último mensaje enviado por: " + (lead.get("ultimo_emisor") or "cliente")
        + "   (cliente | vendedor)\n</datos_temporales>\n\n<historial>\n"
        "Conversación de WhatsApp (más nuevo arriba):\n"
        + json.dumps(historial, ensure_ascii=False)
        + "\n</historial>\n\nAnaliza y devuelve el JSON según tu formato de salida."
    )


def llamar(system, user, clave):
    cuerpo = json.dumps({
        "model": MODELO,
        "temperature": 0,
        "max_tokens": 1500,
        "response_format": {"type": "json_object"},
        "prompt_cache_key": "analista-leads",
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=cuerpo,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {clave}"},
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        data = json.loads(r.read())
    contenido = data["choices"][0]["message"]["content"]
    cacheados = (data.get("usage", {}).get("prompt_tokens_details") or {}).get("cached_tokens", 0)
    return json.loads(contenido), cacheados


def main():
    clave = api_key()
    system = system_prompt()
    casos = CASOS
    if len(sys.argv) > 2 and sys.argv[1] == "--caso":
        casos = [c for c in CASOS if c["id"] == int(sys.argv[2])]
    aprobados = 0
    for caso in casos:
        try:
            respuesta, cacheados = llamar(system, user_prompt(caso), clave)
        except Exception as e:
            print(f"\n[{caso['id']:2}] ❌ FAIL — {caso['nombre']}\n      · error llamando a la API: {e}")
            continue
        fallos = validar(caso, respuesta)
        estado = "✅ PASS" if not fallos else "❌ FAIL"
        print(f"\n[{caso['id']:2}] {estado} — {caso['nombre']}   (cache: {cacheados} tok)")
        for f in fallos:
            print(f"      · {f}")
        if fallos:
            print(f"      → devolvió: {json.dumps(respuesta, ensure_ascii=False)[:220]}")
        aprobados += (not fallos)
    print(f"\n=== {aprobados}/{len(casos)} casos aprobados · modelo {MODELO} ===")


if __name__ == "__main__":
    main()
