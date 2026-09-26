import re

MAX_CHARS = 1500
MIN_CHARS = 200
OVERLAP = 200

ENCABEZADO = re.compile(
    r"^(ejercicio|exercise|problema|problem|ejemplo|example|definici[oó]n|definition|"
    r"teorema|theorem|proposici[oó]n|proposition|lema|lemma|corolario|corollary|"
    r"soluci[oó]n|solution|cap[ií]tulo|chapter|secci[oó]n|section|punto|pregunta|question)\b"
    r"|^\d{1,2}(\.\d{1,2})*[.)]?\s+[A-ZÁÉÍÓÚ¿]",
    re.I,
)


def secciones(paginas):
    actual = None
    for pagina, parrafos in paginas:
        for p in parrafos:
            if actual is None or ENCABEZADO.match(p):
                if actual:
                    yield actual
                actual = {"titulo": p[:80], "partes": []}
            actual["partes"].append((pagina, p))
    if actual:
        yield actual


def partir(texto):
    if len(texto) <= MAX_CHARS:
        return [texto]
    oraciones = re.split(r"(?<=[.;:?!])\s+", texto)
    trozos, buffer = [], ""
    for o in oraciones:
        while len(o) > MAX_CHARS:
            trozos.append(o[:MAX_CHARS])
            o = o[MAX_CHARS - OVERLAP:]
        if buffer and len(buffer) + len(o) + 1 > MAX_CHARS:
            trozos.append(buffer)
            buffer = buffer[-OVERLAP:].split(" ", 1)[-1]
        buffer = f"{buffer} {o}".strip()
    if buffer:
        trozos.append(buffer)
    return trozos


def fragmentar(paginas):
    chunks, actual = [], None

    def cerrar():
        if not actual:
            return
        if len(actual["texto"]) >= MIN_CHARS or not chunks:
            chunks.append(actual)
        else:
            chunks[-1]["texto"] += "\n" + actual["texto"]
            chunks[-1]["pagina_fin"] = actual["pagina_fin"]

    for s in secciones(paginas):
        texto = "\n".join(p for _, p in s["partes"])
        paginas_s = [n for n, _ in s["partes"]]
        for trozo in partir(texto):
            nuevo = {
                "texto": trozo,
                "seccion": s["titulo"],
                "pagina_inicio": paginas_s[0],
                "pagina_fin": paginas_s[-1],
            }
            if actual and len(actual["texto"]) + len(trozo) + 1 <= MAX_CHARS:
                actual["texto"] += "\n" + trozo
                actual["pagina_fin"] = nuevo["pagina_fin"]
            else:
                cerrar()
                actual = nuevo
    cerrar()
    return chunks
