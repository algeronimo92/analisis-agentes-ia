#!/usr/bin/env python3
"""Genera utils/rag-chunks.json con los chunks para el índice vectorial del copiloto.

Indexa SOLO los 4 documentos definidos en prompts/arquitectura-rag.md:
  - negocio/mapa-dolores-soluciones.md  (tipo: dolor)    — 1 chunk por dolor (###)
  - negocio/fichas-procedimientos.md    (tipo: ficha)    — 1 chunk por procedimiento (##)
  - guias/playbook-objeciones.md        (tipo: objecion) — 1 chunk por objeción (###) + proceso maestro (##)
  - negocio/guiones-whatsapp.md         (tipo: guion)    — 1 chunk por sección (##)

Limpieza: quita enlaces [[...]] (deja el texto), y las marcas editoriales
**[VALIDAR...]** / **[COMPLETAR...]** / **[CONFIRMAR...]** / **[DEFINIR...]**
(son notas internas, no conocimiento para el agente).
Cada chunk lleva un encabezado de contexto para ser autocontenido.

Uso:  python3 utils/generar_chunks_rag.py   (desde la raíz del proyecto)
Re-indexación: si cambia un archivo, vuelve a correr esto y re-inserta en n8n.
"""
import json
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SALIDA = RAIZ / "utils" / "rag-chunks.json"

FUENTES = [
    {"archivo": "negocio/mapa-dolores-soluciones.md", "tipo": "dolor",    "nivel": "###", "etiqueta": "Dolor del cliente y su solución"},
    {"archivo": "negocio/fichas-procedimientos.md",   "tipo": "ficha",    "nivel": "##",  "etiqueta": "Ficha del procedimiento"},
    {"archivo": "guias/playbook-objeciones.md",       "tipo": "objecion", "nivel": "###", "etiqueta": "Cómo responder la objeción"},
    {"archivo": "negocio/guiones-whatsapp.md",        "tipo": "guion",    "nivel": "##",  "etiqueta": "Guiones de WhatsApp"},
]


def limpiar(texto: str) -> str:
    texto = re.sub(r"\[\[([^\]]+)\]\]", r"\1", texto)                       # [[link]] -> link
    texto = re.sub(r"\*\*\[(VALIDAR|COMPLETAR|CONFIRMAR|DEFINIR)[^\]]*\]\*\*", "", texto)
    texto = re.sub(r"\[(VALIDAR|COMPLETAR|CONFIRMAR|DEFINIR)[^\]]*\]", "", texto)
    texto = re.sub(r"[ \t]+\n", "\n", texto)                                # espacios colgantes
    texto = re.sub(r"\n{3,}", "\n\n", texto)                                # líneas en blanco extra
    return texto.strip()


def seccionar(cuerpo: str, nivel: str):
    """Divide por encabezados del nivel dado. Devuelve [(titulo, contenido)]."""
    patron = re.compile(rf"^{re.escape(nivel)} (?!#)(.+)$", re.MULTILINE)
    partes = patron.split(cuerpo)
    secciones = []
    # partes = [preambulo, titulo1, cuerpo1, titulo2, cuerpo2, ...]
    for i in range(1, len(partes), 2):
        titulo = partes[i].strip().strip('"«»')
        contenido = partes[i + 1]
        # si el nivel es ###, el contenido puede venir con subencabezados ## de categoría: no aplica
        # si el nivel es ##, quitar el bloque final de separadores
        secciones.append((titulo, contenido))
    return secciones


def main():
    chunks = []
    for fuente in FUENTES:
        ruta = RAIZ / fuente["archivo"]
        cuerpo = ruta.read_text(encoding="utf-8")
        # descarta el encabezado del documento (todo antes del primer separador o primera sección)
        for titulo, contenido in seccionar(cuerpo, fuente["nivel"]):
            contenido = limpiar(contenido)
            if not contenido or len(contenido) < 60:
                continue  # secciones vacías o residuales
            # los ## del mapa son categorías (ROSTRO Y PIEL...) sin contenido propio: ya filtradas por longitud
            titulo_limpio = limpiar(titulo)
            texto = f"[DermicaPro · {fuente['etiqueta']}: {titulo_limpio}]\n\n{contenido}"
            chunks.append({
                "texto": texto,
                "metadata": {
                    "tipo": fuente["tipo"],
                    "titulo": titulo_limpio,
                    "fuente": fuente["archivo"],
                },
            })

    # Secciones ## del playbook que el corte por ### descarta (proceso maestro y regla final)
    playbook = (RAIZ / "guias/playbook-objeciones.md").read_text(encoding="utf-8")
    for m in re.finditer(r"^## (?!Las 7 objeciones)(.+)$", playbook, re.MULTILINE):
        titulo = m.group(1).strip()
        inicio = m.end()
        siguiente = re.search(r"^## ", playbook[inicio:], re.MULTILINE)
        fin = inicio + siguiente.start() if siguiente else len(playbook)
        contenido = limpiar(playbook[inicio:fin])
        if contenido and len(contenido) >= 60:
            chunks.append({
                "texto": f"[DermicaPro · Cómo responder objeciones: {titulo}]\n\n{contenido}",
                "metadata": {"tipo": "objecion", "titulo": titulo, "fuente": "guias/playbook-objeciones.md"},
            })

    SALIDA.write_text(json.dumps(chunks, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"OK: {len(chunks)} chunks -> {SALIDA}")
    por_tipo = {}
    for c in chunks:
        por_tipo[c["metadata"]["tipo"]] = por_tipo.get(c["metadata"]["tipo"], 0) + 1
    for tipo, n in sorted(por_tipo.items()):
        print(f"  {tipo}: {n}")
    tam = [len(c["texto"]) for c in chunks]
    print(f"  tamaño de chunk: min {min(tam)} / prom {sum(tam)//len(tam)} / max {max(tam)} caracteres")


if __name__ == "__main__":
    main()
