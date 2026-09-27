import argparse

from rag import chroma


def main():
    p = argparse.ArgumentParser()
    p.add_argument("pregunta", nargs="+")
    p.add_argument("-k", type=int, default=5)
    p.add_argument("--tipo", choices=["teoria", "ejercicios", "evaluacion"])
    args = p.parse_args()

    pregunta = " ".join(args.pregunta)
    emb = chroma.embeber([pregunta])[0]
    filtro = {"tipo": args.tipo} if args.tipo else None
    r = chroma.buscar(chroma.coleccion(), emb, args.k, filtro)

    for doc, meta, dist in zip(r["documents"][0], r["metadatas"][0], r["distances"][0]):
        print(f"\n[{1 - dist:.3f}] {meta['tutoria']} / {meta['archivo']} p.{meta['pagina']} ({meta['tipo']})")
        print("  " + doc[:300].replace("\n", " ") + "...")


if __name__ == "__main__":
    main()
