import argparse
import hashlib
import json
import os
import re
from pathlib import Path

from rag import chroma
from rag.chunker import fragmentar
from rag.fuentes import idioma, leer, tipo_material, tutorias

TUTORIAS_DIR = os.getenv("TUTORIAS_DIR", "../../Consultorias/_archivo/tutorias")
LOTE = 32


def huella(texto):
    return hashlib.md5(re.sub(r"\W+", "", texto.lower()).encode()).hexdigest()


def construir_chunks(raiz):
    vistas, chunks, omitidos = set(), [], []
    for meta, archivos in tutorias(raiz):
        for ruta in archivos:
            paginas, con_texto = [], 0
            for n, parrafos in leer(ruta):
                texto = " ".join(parrafos)
                if len(texto) < 30:
                    continue
                con_texto += 1
                huellas = [(huella(p), len(p)) for p in parrafos if len(p) >= 40]
                repetido = sum(l for h, l in huellas if h in vistas)
                vistas.update(h for h, _ in huellas)
                if repetido < 0.7 * len(texto):
                    paginas.append((n, parrafos))
            if not paginas:
                motivo = "duplicado" if con_texto else "sin texto (OCR)"
                omitidos.append(f"{motivo}: {meta['tutoria']}/{ruta.name}")
                continue
            for i, c in enumerate(fragmentar(paginas)):
                rel = f"{meta['tutoria']}/{ruta.name}"
                chunks.append({
                    "id": hashlib.md5(f"{rel}#{i}".encode()).hexdigest(),
                    "texto": c["texto"],
                    "meta": {
                        **meta,
                        "archivo": ruta.name,
                        "pagina": c["pagina_inicio"],
                        "pagina_fin": c["pagina_fin"],
                        "seccion": c["seccion"],
                        "tipo": tipo_material(ruta.name),
                        "idioma": idioma(c["texto"]),
                        "indice_fragmento": i,
                    },
                })
    return chunks, omitidos


def para_embeber(c):
    m = c["meta"]
    return f"search_document: {m['curso']} | {m['archivo']} | {m['seccion']}\n{c['texto']}"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dir", default=TUTORIAS_DIR)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--reset", action="store_true")
    p.add_argument("--salida", default="data/chunks.jsonl")
    args = p.parse_args()

    chunks, omitidos = construir_chunks(args.dir)

    Path(args.salida).parent.mkdir(parents=True, exist_ok=True)
    with open(args.salida, "w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")

    largos = sorted(len(c["texto"]) for c in chunks)
    print(f"chunks: {len(chunks)} | mediana {largos[len(largos) // 2]} chars | max {largos[-1]}")
    print(f"archivos omitidos: {len(omitidos)}")
    for o in sorted(omitidos):
        print("  -", o)

    if args.dry_run:
        return

    if args.reset:
        chroma.borrar()
    id_col = chroma.coleccion()
    for i in range(0, len(chunks), LOTE):
        lote = chunks[i:i + LOTE]
        chroma.upsert(
            id_col,
            [c["id"] for c in lote],
            chroma.embeber([para_embeber(c) for c in lote]),
            [c["texto"] for c in lote],
            [c["meta"] for c in lote],
        )
        print(f"  {i + len(lote)}/{len(chunks)}", end="\r")
    print(f"\ncoleccion '{chroma.COLECCION}': {chroma.contar(id_col)} fragmentos")


if __name__ == "__main__":
    main()
