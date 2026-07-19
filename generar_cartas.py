# -*- coding: utf-8 -*-
"""Genera un PDF imprimible con las cartas de votación 1-5 de Rankealo.

6 jugadores × cartas del 1 al 5 = 30 cartas, en 2 hojas tamaño carta (15 por hoja).
Diseño de baja tinta: fondo blanco, números en contorno hueco y líneas de corte
en gris claro. Cada columna de una hoja es un set completo 1-5 listo para repartir.
"""

from fpdf import FPDF

try:
    from fpdf.enums import TextMode
    HAY_CONTORNO = True
except Exception:
    HAY_CONTORNO = False

# Tamaño carta (US Letter / "carta") en mm.
ANCHO, ALTO = 215.9, 279.4
MARGEN = 12.0
COLS, FILAS = 3, 5            # 15 cartas por hoja = 3 sets de 1-5
JUGADORES = 6                 # 6 sets en total → 2 hojas
GRIS = (160, 160, 160)

celda_w = (ANCHO - 2 * MARGEN) / COLS
celda_h = (ALTO - 2 * MARGEN) / FILAS

pdf = FPDF(orientation="P", unit="mm", format=(ANCHO, ALTO))
pdf.set_auto_page_break(False)
pdf.set_title("Rankealo - cartas 1 a 5")


def lineas_de_corte():
    """Rejilla de guías de corte en gris claro (líneas rectas de lado a lado)."""
    pdf.set_draw_color(*GRIS)
    pdf.set_line_width(0.2)
    x0, y0 = MARGEN, MARGEN
    x1, y1 = ANCHO - MARGEN, ALTO - MARGEN
    for c in range(COLS + 1):
        x = x0 + c * celda_w
        pdf.line(x, y0, x, y1)
    for f in range(FILAS + 1):
        y = y0 + f * celda_h
        pdf.line(x0, y, x1, y)


def dibujar_carta(cx, cy, numero):
    """Dibuja una carta (número grande hueco + pie 'RANKEALO') en la celda dada."""
    # Número grande, centrado y un poco sobre el medio para dejar sitio al pie.
    pdf.set_font("Helvetica", "B", 120)
    pdf.set_text_color(0, 0, 0)
    y_num = cy + (celda_h - 34) / 2 - 3
    if HAY_CONTORNO:
        with pdf.local_context(text_mode=TextMode.STROKE, line_width=0.5):
            pdf.set_draw_color(0, 0, 0)
            pdf.set_xy(cx, y_num)
            pdf.cell(celda_w, 34, str(numero), align="C")
    else:
        pdf.set_xy(cx, y_num)
        pdf.cell(celda_w, 34, str(numero), align="C")

    # Pie discreto para identidad, en gris claro.
    pdf.set_font("Helvetica", "B", 7)
    pdf.set_text_color(*GRIS)
    pdf.set_xy(cx, cy + celda_h - 9)
    pdf.cell(celda_w, 5, "R A N K E A L O", align="C")


# Cada columna (de arriba a abajo) es un set 1-5; cada hoja tiene 3 columnas = 3 sets.
sets_por_hoja = COLS
hojas = (JUGADORES + sets_por_hoja - 1) // sets_por_hoja
for _ in range(hojas):
    pdf.add_page()
    lineas_de_corte()
    for fila in range(FILAS):          # fila = número (1..5)
        for col in range(COLS):        # col = un jugador
            cx = MARGEN + col * celda_w
            cy = MARGEN + fila * celda_h
            dibujar_carta(cx, cy, fila + 1)

salida = "Cartas_Rankealo_1a5_6jugadores.pdf"
pdf.output(salida)
print("PDF generado:", salida, "| contorno hueco:", HAY_CONTORNO,
      "| hojas:", hojas, "| cartas:", hojas * COLS * FILAS)
