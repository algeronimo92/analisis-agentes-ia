#!/usr/bin/env python3
"""Tester DIRECTO del analista: llama al modelo sin pasar por n8n.

Replica la configuración de producción del nodo de n8n: gemini-2.5-flash-lite,
temperature 0, salida JSON, safety settings en BLOCK_NONE (las 4 categorías),
max output 4000, historial "más nuevo arriba". El SYSTEM PROMPT se extrae del
archivo prompts/agente-analista-leads.md (única fuente de verdad) y cada caso
se valida con los mismos checks de test_analista.py.

USO
  GEMINI_API_KEY en el entorno o en .env (raíz del proyecto), luego:
    python3 utils/test_analista_directo.py            # los 33 casos
    python3 utils/test_analista_directo.py --caso 34  # un caso puntual
    python3 utils/test_analista_directo.py --caso 34 --repetir 5   # flakiness
  Variables opcionales: MODELO (default gemini-2.5-flash-lite; si empieza por
  "gpt"/"o" usa la API de OpenAI con OPENAI_API_KEY).

Diferencia con test_analista.py: aquel valida el workflow n8n completo
(webhook + BD + agente); este valida SOLO el prompt contra el modelo — ideal
para iterar el prompt rápido y barato antes de re-pegarlo en n8n.
"""
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from test_analista import CASOS, validar  # mismos casos, mismos checks

RAIZ = Path(__file__).resolve().parent.parent
MODELO = os.environ.get("MODELO", "gemini-2.5-flash-lite")
ES_GEMINI = MODELO.startswith("gemini") or MODELO.startswith("models/gemini")


def api_key():
    nombres = ("GEMINI_API_KEY", "GOOGLE_API_KEY") if ES_GEMINI else ("OPENAI_API_KEY",)
    for nombre in nombres:
        if os.environ.get(nombre):
            return os.environ[nombre]
    env = RAIZ / ".env"
    if env.exists():
        for linea in env.read_text(encoding="utf-8").splitlines():
            for nombre in nombres:
                if linea.startswith(nombre + "="):
                    return linea.split("=", 1)[1].strip()
    sys.exit(f"Falta {nombres[0]} (en el entorno o en .env). "
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


def _post(url, cuerpo, headers):
    req = urllib.request.Request(url, data=json.dumps(cuerpo).encode("utf-8"), headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:  # el cuerpo del error trae el motivo real
        raise RuntimeError(f"HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:400]}") from None


def _json_del_texto(texto):
    """El modelo debe devolver JSON pelado; si envuelve en ```json, se rescata."""
    t = texto.strip()
    if t.startswith("```"):
        t = t.split("```")[1]
        t = t[4:] if t.startswith("json") else t
    return json.loads(t.strip())


def llamar_openai(system, user, clave):
    data = _post(
        "https://api.openai.com/v1/chat/completions",
        {"model": MODELO, "temperature": 0, "max_tokens": 1500,
         "response_format": {"type": "json_object"},
         "prompt_cache_key": "analista-leads",
         "messages": [{"role": "system", "content": system},
                      {"role": "user", "content": user}]},
        {"Content-Type": "application/json", "Authorization": f"Bearer {clave}"},
    )
    contenido = data["choices"][0]["message"]["content"]
    cacheados = (data.get("usage", {}).get("prompt_tokens_details") or {}).get("cached_tokens", 0)
    return _json_del_texto(contenido), cacheados


def llamar_gemini(system, user, clave):
    """Misma config que el nodo Google Gemini Chat Model de n8n (ver el .md):
    temperature 0, 4000 tokens de salida y las CUATRO safety settings en BLOCK_NONE
    (sin eso, los mensajes sobre lactancia/depilación íntima se bloquean y no llega JSON)."""
    modelo = MODELO if MODELO.startswith("models/") else f"models/{MODELO}"
    data = _post(
        f"https://generativelanguage.googleapis.com/v1beta/{modelo}:generateContent",
        {"systemInstruction": {"parts": [{"text": system}]},
         "contents": [{"role": "user", "parts": [{"text": user}]}],
         "generationConfig": {"temperature": 0, "maxOutputTokens": 4000,
                              "responseMimeType": "application/json"},
         "safetySettings": [{"category": c, "threshold": "BLOCK_NONE"} for c in
                            ("HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH",
                             "HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_DANGEROUS_CONTENT")]},
        {"Content-Type": "application/json", "x-goog-api-key": clave},
    )
    candidatos = data.get("candidates") or []
    partes = (candidatos[0].get("content", {}).get("parts") if candidatos else None) or []
    if not partes:
        motivo = candidatos[0].get("finishReason") if candidatos else data.get("promptFeedback")
        raise RuntimeError(f"sin texto en la respuesta (finishReason={motivo}) — "
                           "clasificación perdida, es el modo de fallo silencioso de producción")
    cacheados = data.get("usageMetadata", {}).get("cachedContentTokenCount", 0)
    return _json_del_texto(partes[0]["text"]), cacheados


def llamar(system, user, clave):
    return (llamar_gemini if ES_GEMINI else llamar_openai)(system, user, clave)


def main():
    clave = api_key()
    system = system_prompt()
    casos = CASOS
    if "--caso" in sys.argv:
        ids = {int(x) for x in sys.argv[sys.argv.index("--caso") + 1].split(",")}
        casos = [c for c in CASOS if c["id"] in ids]
        if not casos:
            sys.exit(f"No existe(n) el/los caso(s) {sorted(ids)} en tests-analista.json")
    repetir = int(sys.argv[sys.argv.index("--repetir") + 1]) if "--repetir" in sys.argv else 1

    aprobados = corridas = 0
    for caso in casos:
        for i in range(repetir):
            sufijo = f" ({i + 1}/{repetir})" if repetir > 1 else ""
            corridas += 1
            try:
                respuesta, cacheados = llamar(system, user_prompt(caso), clave)
            except Exception as e:
                print(f"\n[{caso['id']:2}] ❌ FAIL{sufijo} — {caso['nombre']}\n      · error llamando a la API: {e}")
                continue
            fallos = validar(caso, respuesta)
            estado = "✅ PASS" if not fallos else "❌ FAIL"
            print(f"\n[{caso['id']:2}] {estado}{sufijo} — {caso['nombre']}   (cache: {cacheados} tok)")
            for f in fallos:
                print(f"      · {f}")
            if fallos:
                print(f"      → devolvió: {json.dumps(respuesta, ensure_ascii=False)[:220]}")
            aprobados += (not fallos)
    print(f"\n=== {aprobados}/{corridas} clasificaciones aprobadas · modelo {MODELO} ===")


if __name__ == "__main__":
    main()
