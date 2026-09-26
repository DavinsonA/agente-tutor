import io
import re

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from flask import Flask, request, send_file
from fpdf import FPDF

app = Flask(__name__)

DIFICULTAD = {
    "facil": ("Fácil", (76, 175, 80)),
    "media": ("Media", (255, 152, 0)),
    "dificil": ("Difícil", (244, 67, 54)),
}


class PDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 14)
        self.cell(0, 10, "Banco de Ejercicios", align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 10, f"Página {self.page_no()}/{{nb}}", align="C")


def latex_png(expr):
    fig = plt.figure()
    fig.text(0, 0, f"${expr}$", fontsize=14)
    buf = io.BytesIO()
    try:
        fig.savefig(buf, format="png", dpi=150, bbox_inches="tight", pad_inches=0.05, facecolor="white")
    except Exception:
        return None
    finally:
        plt.close(fig)
    buf.seek(0)
    return buf


def texto_mixto(pdf, texto):
    for parte in re.split(r"(\$\$[^$]+\$\$|\$[^$]+\$)", texto):
        if not parte.strip():
            continue
        if parte.startswith("$"):
            img = latex_png(parte.strip("$"))
            if img:
                pdf.image(img, h=8)
                pdf.set_x(pdf.l_margin)
                continue
        pdf.set_font("Helvetica", "", 11)
        pdf.multi_cell(0, 6, parte.strip(), new_x="LMARGIN", new_y="NEXT")


def seccion(pdf, titulo, texto):
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 6, titulo, new_x="LMARGIN", new_y="NEXT")
    texto_mixto(pdf, texto)
    pdf.ln(2)


def generar_pdf(datos):
    pdf = PDF()
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 8, f"Nivel: {datos.get('nivel', 'universidad').capitalize()}", new_x="LMARGIN", new_y="NEXT")

    for tema in datos.get("temas", []):
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_fill_color(230, 230, 250)
        pdf.cell(0, 10, f"  {tema.get('nombre', '')}", fill=True, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(3)
        for i, ej in enumerate(tema.get("ejercicios", []), 1):
            etiqueta, color = DIFICULTAD.get(ej.get("nivel_dificultad"), DIFICULTAD["media"])
            if pdf.get_y() > 240:
                pdf.add_page()
            pdf.set_font("Helvetica", "B", 11)
            pdf.set_text_color(*color)
            pdf.cell(0, 7, f"Ejercicio {i} [{etiqueta}]", new_x="LMARGIN", new_y="NEXT")
            pdf.set_text_color(0, 0, 0)
            seccion(pdf, "Enunciado:", ej.get("enunciado", ""))
            seccion(pdf, "Solución:", ej.get("solucion", ""))
            if ej.get("notas_pedagogicas"):
                seccion(pdf, "Notas pedagógicas:", ej["notas_pedagogicas"])
            pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
            pdf.ln(5)

    return io.BytesIO(pdf.output())


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/render")
def render():
    datos = request.get_json(silent=True)
    if not datos:
        return {"error": "No se recibieron datos"}, 400
    return send_file(generar_pdf(datos), mimetype="application/pdf", download_name="ejercicios.pdf")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)
