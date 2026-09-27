import io
import re
import subprocess
import tempfile
from pathlib import Path

from flask import Flask, request, send_file

app = Flask(__name__)

PREAMBULO = r"""\documentclass[11pt]{article}
\usepackage[margin=2cm]{geometry}
\usepackage{amsmath,amssymb}
\usepackage{xcolor}
\usepackage{fancyhdr}
\pagestyle{fancy}\fancyhf{}\cfoot{\thepage}\renewcommand{\headrulewidth}{0pt}
\setlength{\parindent}{0pt}\setlength{\parskip}{4pt}
\definecolor{facil}{RGB}{76,175,80}\definecolor{media}{RGB}{255,152,0}\definecolor{dificil}{RGB}{244,67,54}
\begin{document}
"""
ETIQUETAS = {"facil": "Fácil", "media": "Media", "dificil": "Difícil"}
MATEMATICA = re.compile(r"(\$\$.+?\$\$|\$.+?\$|\\\(.+?\\\)|\\\[.+?\\\])", re.S)
ESCAPES = {"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "#": r"\#", "_": r"\_",
           "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}", "$": r"\$"}


def escapar(texto):
    return "".join(ESCAPES.get(c, c) for c in texto)


def balanceada(formula):
    sin_escapes = formula.replace(r"\{", "").replace(r"\}", "")
    return (sin_escapes.count("{") == sin_escapes.count("}")
            and formula.count(r"\begin{") == formula.count(r"\end{"))


def mixto(texto, con_matematica=True):
    partes = []
    for parte in MATEMATICA.split(texto or ""):
        if MATEMATICA.fullmatch(parte):
            valida = con_matematica and balanceada(parte)
            partes.append(parte if valida else r"\texttt{" + escapar(parte) + "}")
        else:
            partes.append(escapar(parte).replace("\n", "\n\n"))
    return "".join(partes)


def documento(datos, con_matematica=True):
    t = lambda x: mixto(x, con_matematica)
    cuerpo = [r"\begin{center}{\Large\bfseries Banco de Ejercicios}\end{center}",
              f"Nivel: {escapar(datos.get('nivel', 'universidad').capitalize())}"]
    for tema in datos.get("temas", []):
        cuerpo.append(r"\section*{" + escapar(tema.get("nombre", "")) + "}")
        for i, ej in enumerate(tema.get("ejercicios", []), 1):
            nivel = ej.get("nivel_dificultad") if ej.get("nivel_dificultad") in ETIQUETAS else "media"
            cuerpo += [
                r"\subsection*{\textcolor{" + nivel + "}{Ejercicio " + str(i) + " [" + ETIQUETAS[nivel] + "]}}",
                r"\textbf{Enunciado:} " + t(ej.get("enunciado")),
                r"\textbf{Solución:} " + t(ej.get("solucion")),
            ]
            if ej.get("notas_pedagogicas"):
                cuerpo.append(r"\textbf{Notas pedagógicas:} \textit{" + t(ej["notas_pedagogicas"]) + "}")
            cuerpo.append(r"\noindent\rule{\linewidth}{0.4pt}")
    return PREAMBULO + "\n\n".join(cuerpo) + "\n\\end{document}\n"


def compilar(tex):
    with tempfile.TemporaryDirectory() as tmp:
        fuente = Path(tmp) / "ejercicios.tex"
        fuente.write_text(tex, encoding="utf-8")
        r = subprocess.run(["tectonic", str(fuente)], capture_output=True, text=True, timeout=300)
        pdf = fuente.with_suffix(".pdf")
        if r.returncode != 0:
            print(r.stderr[-500:], flush=True)
        return pdf.read_bytes() if r.returncode == 0 and pdf.exists() else None


def precalentar():
    formulas = (r"$\mathbf{x} \in \mathbb{R}^n$, $\bar{X}$, $\hat{\theta}$, $\sqrt{n}$, $\sum_{i=1}^n x_i$, "
                r"$$\int_0^\infty e^{-x}dx \quad \begin{aligned} a &= b \\ c &\leq d \end{aligned}$$")
    ejemplo = {"temas": [{"nombre": "x", "ejercicios": [
        {"nivel_dificultad": n, "enunciado": formulas, "solucion": formulas, "notas_pedagogicas": formulas}
        for n in ETIQUETAS]}]}
    for con_matematica in (True, False):
        assert compilar(documento(ejemplo, con_matematica))


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/render")
def render():
    datos = request.get_json(silent=True)
    if not datos:
        return {"error": "No se recibieron datos"}, 400
    pdf = compilar(documento(datos)) or compilar(documento(datos, con_matematica=False))
    if not pdf:
        return {"error": "No se pudo compilar el LaTeX"}, 500
    return send_file(io.BytesIO(pdf), mimetype="application/pdf", download_name="ejercicios.pdf")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)
