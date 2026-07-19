# -*- coding: utf-8 -*-
"""Genera el PDF de cartas de votación 1-5 de Rankealo con siluetas de animales.

Todo en UNA cara tamaño carta, sin márgenes (rejilla a sangre): 5 columnas
(números 1-5) × 6 filas (jugadores) = 30 cartas. Cada fila es un set completo.
Diseño de baja tinta: fondo blanco, número grande en contorno y animal en línea.
"""

import os
import tempfile

from fpdf import FPDF
from fpdf.enums import TextMode

ANCHO, ALTO = 215.9, 279.4          # tamaño carta en mm
COLS, FILAS = 5, 6                   # 5 números × 6 jugadores = 30 cartas
GRIS = (150, 150, 150)

cw = ANCHO / COLS
ch = ALTO / FILAS

# --- Siluetas de animales (line-art) en un viewBox 100x100 ---------------------
_STROKE = ('fill="none" stroke="#000" stroke-width="4.5" '
           'stroke-linejoin="round" stroke-linecap="round"')

RATA = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><g {_STROKE}>
<ellipse cx="54" cy="61" rx="27" ry="15"/>
<circle cx="27" cy="58" r="12"/>
<circle cx="22" cy="46" r="6"/>
<path d="M16 61 l-9 2 l7 -6"/>
<path d="M79 61 C99 56 89 83 97 88"/>
<path d="M44 75 v9 M62 75 v9"/>
</g></svg>'''

CHANCHO = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><g {_STROKE}>
<ellipse cx="55" cy="60" rx="31" ry="22"/>
<circle cx="31" cy="55" r="14"/>
<ellipse cx="16" cy="58" rx="8" ry="9"/>
<path d="M24 43 l-3 -13 l12 6 Z"/>
<path d="M38 43 l3 -13 l-12 6 Z"/>
<path d="M85 52 c8 -4 8 9 15 4"/>
<path d="M46 79 v9 M66 79 v9"/>
</g></svg>'''

GATO = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><g {_STROKE}>
<path d="M34 52 Q29 92 50 92 Q71 92 66 52"/>
<circle cx="50" cy="37" r="17"/>
<path d="M36 26 l-5 -17 l17 11 Z"/>
<path d="M64 26 l5 -17 l-17 11 Z"/>
<path d="M35 38 l-13 -3 M35 42 l-13 4"/>
<path d="M65 38 l13 -3 M65 42 l13 4"/>
<path d="M66 84 Q95 82 85 53"/>
</g></svg>'''

PERRO = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><g {_STROKE}>
<path d="M35 56 Q30 91 50 91 Q70 91 65 56"/>
<circle cx="50" cy="39" r="15"/>
<ellipse cx="50" cy="49" rx="9" ry="6.5"/>
<ellipse cx="32" cy="43" rx="6.5" ry="13"/>
<ellipse cx="68" cy="43" rx="6.5" ry="13"/>
<path d="M66 62 Q87 47 80 70"/>
</g></svg>'''

LEON = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><g {_STROKE}>
<path d="M44 22 L50 9 L56 22 M71 27 L82 18 L79 31 M78 44 L92 50 L78 56
M71 73 L82 82 L67 78 M56 78 L50 91 L44 78 M29 73 L18 82 L33 78
M22 56 L8 50 L22 44 M29 27 L18 18 L21 31"/>
<circle cx="50" cy="50" r="27"/>
<circle cx="38" cy="35" r="5.5"/>
<circle cx="62" cy="35" r="5.5"/>
<path d="M50 52 l-6 8 h12 Z"/>
<path d="M50 60 v6"/>
</g></svg>'''

# número -> (svg, animal, frase con guiño adulto)
CARTAS = {
    1: (RATA,    "una rata inmunda"),
    2: (CHANCHO, "un asco, pero pasa"),
    3: (GATO,    "ni fu ni fa"),
    4: (PERRO,   "me lo llevo"),
    5: (LEON,    "un lujo, el rey"),
}

# Escribe cada SVG a un archivo temporal (fpdf2 embebe SVG vectorial por ruta).
_tmp = tempfile.mkdtemp(prefix="rankealo_")
SVG_PATH = {}
for n, (svg, _frase) in CARTAS.items():
    p = os.path.join(_tmp, f"animal_{n}.svg")
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(svg)
    SVG_PATH[n] = p


def dibujar_carta(x, y, numero):
    frase = CARTAS[numero][1]
    # Número grande en contorno (bajo consumo de tinta), parte superior.
    pdf.set_font("Helvetica", "B", 58)
    with pdf.local_context(text_mode=TextMode.STROKE, line_width=0.5):
        pdf.set_draw_color(0, 0, 0)
        pdf.set_xy(x, y + ch * 0.05)
        pdf.cell(cw, ch * 0.42, str(numero), align="C")
    # Animal en línea, parte media.
    lado = 17.0
    pdf.image(SVG_PATH[numero], x=x + (cw - lado) / 2, y=y + ch * 0.46, w=lado, h=lado)
    # Frase con guiño, al pie.
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(90, 90, 90)
    pdf.set_xy(x, y + ch - 7)
    pdf.cell(cw, 4, frase, align="C")
    pdf.set_text_color(0, 0, 0)


pdf = FPDF(orientation="P", unit="mm", format=(ANCHO, ALTO))
pdf.set_auto_page_break(False)
pdf.set_margins(0, 0, 0)
pdf.set_title("Rankealo - cartas animales 1 a 5")
pdf.add_page()

# Guías de corte: rejilla interior en gris claro (sin borde exterior = a sangre).
pdf.set_draw_color(*GRIS)
pdf.set_line_width(0.2)
for c in range(1, COLS):
    pdf.line(c * cw, 0, c * cw, ALTO)
for f in range(1, FILAS):
    pdf.line(0, f * ch, ANCHO, f * ch)

for fila in range(FILAS):            # fila = jugador
    for col in range(COLS):          # col = número 1..5
        dibujar_carta(col * cw, fila * ch, col + 1)

salida = "Cartas_Rankealo_animales_1a5_6jug.pdf"
pdf.output(salida)
print("PDF generado:", salida, "| 1 hoja |", COLS * FILAS, "cartas")
