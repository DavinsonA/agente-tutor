import argparse
from pathlib import Path

import yaml

from rag import chroma


def evaluar(k):
    preguntas = yaml.safe_load((Path(__file__).parent / "preguntas.yaml").read_text(encoding="utf-8"))
    id_col = chroma.coleccion()
    aciertos, rr = 0, 0.0
    for p in preguntas:
        emb = chroma.embeber([p["pregunta"]])[0]
        archivos = [m["archivo"] for m in chroma.buscar(id_col, emb, k)["metadatas"][0]]
        esperado = [str(e).lower() for e in p["esperado"]]
        rango = next((i for i, a in enumerate(archivos, 1) if any(e in a.lower() for e in esperado)), None)
        aciertos += rango is not None
        rr += 1 / rango if rango else 0
        print(f"{'ok ' if rango else '-- '} {rango or '-'}  {p['pregunta'][:60]}")
    n = len(preguntas)
    print(f"\nhit@{k}: {aciertos / n:.2f}  MRR@{k}: {rr / n:.2f}  ({n} preguntas)")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("-k", type=int, default=5)
    evaluar(p.parse_args().k)
