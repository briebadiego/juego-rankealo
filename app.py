# -*- coding: utf-8 -*-
"""Rankealo — juego de fiesta para calificar situaciones.

Dos formatos:
  - 📱 Pasa el celu: un teléfono rota entre los jugadores y cada uno vota en secreto.
  - 🃏 Híbrido: la app muestra la situación, se vota con cartas físicas (1-5) y
    luego se ingresan los votos para calcular resultados.

Tres modos de puntaje:
  - 🐑 Oveja Negra: el más alejado de la mediana del grupo suma punto de castigo.
  - 🎯 Protagonista: cada ronda alguien pone su nota real y el resto la adivina.
  - 🎰 Apuesta: además de tu nota, predices el promedio del grupo.
"""

import random
import statistics

import requests
import streamlit as st

from situaciones import CATEGORIAS, total_situaciones

st.set_page_config(page_title="Rankealo", page_icon="🐑", layout="centered")

MODOS_PUNTAJE = {
    "🐑 Oveja Negra": "El que queda más lejos de la mediana del grupo suma un punto de castigo.",
    "🎯 Protagonista": "Cada ronda hay un protagonista que pone su nota real en secreto; el resto intenta adivinarla. El que más se aleja, suma castigo.",
    "🎰 Apuesta": "Pones tu nota Y predices el promedio del grupo. El peor pronóstico suma castigo.",
}

COMENTARIOS = [
    "{p} claramente vive en una realidad paralela. Punto de castigo.",
    "El grupo habló y {p} no estaba escuchando.",
    "{p}, respeta la sabiduría colectiva. O al menos disimula.",
    "Alguien tenía que ser la oveja negra, y hoy le tocó a {p}.",
    "{p} votó con el corazón. El grupo votó con la mediana.",
    "Interesante teoría la de {p}. Lástima que nadie la compartió.",
    "{p} está jugando otro juego, aparentemente.",
    "La media no perdona, {p}.",
]
COMENTARIO_EMPATE = "Consenso absoluto (o empate perfecto): esta ronda nadie pierde. Qué aburridos."

PENITENCIAS = [
    "Publicar una historia diciendo 'perdí en Rankealo por tener opiniones únicas'.",
    "Mandar 'hola, ¿cómo estás?' al último match o contacto que dejaste en visto.",
    "Imitar a alguien de la mesa hasta que adivinen quién es.",
    "Hablar con acento español (de España) durante las próximas 2 rondas.",
    "Mostrar la última foto de tu galería y explicarla.",
    "Dejar que el grupo escriba un estado de WhatsApp por ti (1 hora mínimo).",
    "Cantar el coro de la canción que elija el grupo, de pie.",
    "Contar tu peor cita en 30 segundos.",
    "Servir los bebestibles al resto durante toda la próxima ronda.",
    "Decir un piropo sincero a cada persona de la mesa.",
    "Mostrar tu historial de búsqueda de YouTube más reciente.",
    "Bailar 15 segundos sin música mientras todos miran en silencio.",
]

# Modelos que se pueden elegir en Ajustes. El elegido se prueba primero y el resto
# quedan como respaldo por si la key no tiene ese modelo habilitado en su tier.
MODELOS_DISPONIBLES = [
    "gemini-3.1-flash-lite",   # rápido y barato (recomendado)
    "gemini-3-flash-preview",  # más capaz
    "gemini-3.1-pro-preview",  # el más potente
    "gemini-2.5-flash",        # respaldo de generación anterior
]

TONOS = {
    "Suave": "apto para jugar con la familia, humor blanco",
    "Medio": "humor de carrete entre amigos, se permite algo de picardía",
    "Picante": "humor atrevido y descarado para adultos, sin caer en lo ofensivo",
}


# ---------------------------------------------------------------- utilidades

def _secret_key():
    try:
        return st.secrets.get("GEMINI_API_KEY", "")
    except Exception:
        return ""


def get_api_key():
    """La key escrita en Ajustes tiene prioridad; si no, se usa la de los Secrets."""
    manual = st.session_state.get("api_key_input", "").strip()
    return manual or _secret_key()


def get_modelo():
    """Modelo elegido en Ajustes (o uno escrito a mano), con el flash-lite por defecto."""
    custom = st.session_state.get("modelo_custom", "").strip()
    return custom or st.session_state.get("modelo_ia") or MODELOS_DISPONIBLES[0]


def panel_ia():
    """Controles para elegir la API key de Gemini y el modelo. Se usa en el setup y
    en la barra lateral; setup y juego nunca se dibujan a la vez, así que las keys
    de los widgets no chocan."""
    if _secret_key():
        st.caption("🤖 Hay una API key en los Secrets. Puedes sobrescribirla acá abajo.")
    st.text_input(
        "API key de Gemini", type="password", key="api_key_input",
        help="Gratis en aistudio.google.com/apikey. Sin key, el juego usa solo el mazo.",
    )
    st.selectbox("Modelo de IA", MODELOS_DISPONIBLES, key="modelo_ia")
    st.text_input(
        "…o escribe otro modelo", key="modelo_custom",
        placeholder="ej: gemini-3.5-flash",
        help="Si Google lanza un modelo nuevo, escríbelo aquí y tiene prioridad.",
    )


def _extraer_texto(data):
    """Concatena el texto de las 'parts', ignorando las de razonamiento (thought)."""
    try:
        parts = data["candidates"][0]["content"]["parts"]
    except (KeyError, IndexError, TypeError):
        return ""
    trozos = [p["text"] for p in parts if p.get("text") and not p.get("thought")]
    return "\n".join(trozos).strip()


def gemini(prompt):
    """Llama a la API de Gemini probando modelos en orden. Devuelve texto o None.

    Los modelos Gemini 3 razonan por defecto, así que fijamos thinkingLevel bajo y
    un maxOutputTokens amplio para que el razonamiento no consuma toda la respuesta.
    Guarda el último error en session_state para poder mostrarlo en la interfaz.
    """
    st.session_state["_gemini_error"] = None
    key = get_api_key()
    if not key:
        st.session_state["_gemini_error"] = "No hay API key configurada."
        return None

    elegido = get_modelo()
    orden = [elegido] + [m for m in MODELOS_DISPONIBLES if m != elegido]
    ultimo_error = "La IA no respondió."
    for modelo in orden:
        gen_cfg = {"temperature": 1.0, "maxOutputTokens": 2048}
        if modelo.startswith("gemini-3"):
            # thinkingLevel solo existe en la familia 3.x; 2.5 usa otra API de thinking.
            gen_cfg["thinkingConfig"] = {"thinkingLevel": "low"}
        body = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": gen_cfg}
        try:
            r = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent",
                headers={"x-goog-api-key": key}, json=body, timeout=45,
            )
        except Exception as e:
            ultimo_error = f"Error de conexión: {e}"
            continue
        if r.status_code == 200:
            texto = _extraer_texto(r.json())
            if texto:
                return texto
            ultimo_error = f"{modelo}: respuesta vacía (revisa cuota o tokens)."
            continue
        detalle = r.text[:200].replace("\n", " ")
        ultimo_error = f"{modelo} → HTTP {r.status_code}: {detalle}"

    st.session_state["_gemini_error"] = ultimo_error
    return None


def generar_situaciones_ia(cat_key, n=5):
    cat = CATEGORIAS[cat_key]
    ejemplos = "\n".join(random.sample(cat["items"], 3))
    extra = (
        "Si la categoría usa {nombre}, escribe el marcador {nombre} tal cual "
        "(con llaves) donde vaya el nombre de un jugador.\n"
        if cat_key == "grupo" else ""
    )
    tono = TONOS[st.session_state.cfg["tono"]]
    prompt = (
        f"Estás generando cartas para un juego de fiesta chileno donde el grupo "
        f"califica situaciones del 1 al 5.\n"
        f"Categoría: {cat['nombre']} — la pregunta al grupo es '{cat['pregunta']}'.\n"
        f"Ejemplos del estilo:\n{ejemplos}\n\n"
        f"Genera {n} situaciones NUEVAS y distintas a los ejemplos, tono: {tono}. "
        f"En español de Chile, máximo 25 palabras cada una, UNA POR LÍNEA, "
        f"sin numeración, sin viñetas, sin comillas, sin texto adicional.\n{extra}"
    )
    texto = gemini(prompt)
    if not texto:
        return []
    lineas = [l.strip(" -•*\"'") for l in texto.splitlines() if len(l.strip()) > 10]
    return [(cat_key, l) for l in lineas[:n]]


def comentario_ia(resultado, situacion):
    votos_txt = ", ".join(f"{j}: {v['nota']}" for j, v in st.session_state.votos.items())
    perdedores = ", ".join(resultado["perdedores"]) or "nadie"
    prompt = (
        f"Eres el comentarista sarcástico de un juego de fiesta. "
        f"Situación calificada: '{situacion['texto']}'. "
        f"Votos: {votos_txt}. Mediana: {resultado['mediana']}. "
        f"Perdedor(es) de la ronda: {perdedores}. "
        f"Escribe UN comentario chistoso y sarcástico de máximo 2 frases en español "
        f"chileno, dirigido al perdedor (o al grupo si no hubo perdedor). "
        f"Tono: {TONOS[st.session_state.cfg['tono']]}. Solo el comentario, nada más."
    )
    return gemini(prompt)


def armar_mazo(categorias_activas):
    mazo = []
    for c in categorias_activas:
        mazo += [(c, item) for item in CATEGORIAS[c]["items"]]
    random.shuffle(mazo)
    return mazo


def sacar_situacion():
    if not st.session_state.mazo:
        st.session_state.mazo = armar_mazo(st.session_state.cfg["categorias"])
    cat_key, texto = st.session_state.mazo.pop()
    if "{nombre}" in texto:
        texto = texto.replace("{nombre}", random.choice(st.session_state.jugadores))
    cat = CATEGORIAS[cat_key]
    st.session_state.situacion = {
        "cat": cat["nombre"], "texto": texto, "pregunta": cat["pregunta"],
        "label_min": cat["label_min"], "label_max": cat["label_max"],
    }


def prota_actual():
    js = st.session_state.jugadores
    return js[st.session_state.prota_idx % len(js)]


def orden_votacion():
    js = list(st.session_state.jugadores)
    if st.session_state.cfg["modo_puntaje"] == "🎯 Protagonista":
        p = prota_actual()
        return [p] + [j for j in js if j != p]
    return js


def calcular_resultado():
    """Calcula perdedores de la ronda y actualiza el marcador (se llama UNA vez)."""
    votos = st.session_state.votos
    modo = st.session_state.cfg["modo_puntaje"]
    notas = {j: v["nota"] for j, v in votos.items()}
    mediana = statistics.median(notas.values())
    promedio = round(statistics.mean(notas.values()), 2)

    if modo == "🐑 Oveja Negra":
        dist = {j: abs(n - mediana) for j, n in notas.items()}
        objetivo = f"Mediana del grupo: **{mediana}**"
    elif modo == "🎯 Protagonista":
        p = prota_actual()
        target = notas[p]
        dist = {j: abs(n - target) for j, n in notas.items() if j != p}
        objetivo = f"Nota real de {p}: **{target}**"
    else:  # Apuesta
        dist = {j: abs(v["pred"] - promedio) for j, v in votos.items()}
        objetivo = f"Promedio real del grupo: **{promedio}**"

    maxd, mind = max(dist.values()), min(dist.values())
    perdedores = [] if maxd == mind else [j for j, d in dist.items() if d == maxd]
    for p in perdedores:
        st.session_state.scores[p] += 1

    if perdedores:
        comentario = random.choice(COMENTARIOS).format(p=" y ".join(perdedores))
    else:
        comentario = COMENTARIO_EMPATE

    limite = st.session_state.cfg["limite"]
    eliminados = [j for j, s in st.session_state.scores.items() if s >= limite]
    st.session_state.resultado = {
        "mediana": mediana, "promedio": promedio, "dist": dist,
        "perdedores": perdedores, "objetivo": objetivo, "comentario": comentario,
        "eliminados": eliminados, "penitencia": random.choice(PENITENCIAS),
    }


def nueva_ronda():
    st.session_state.ronda += 1
    st.session_state.prota_idx += 1
    st.session_state.votos = {}
    st.session_state.voter_idx = 0
    st.session_state.resultado = None
    sacar_situacion()
    st.session_state.fase = "ronda"


# ------------------------------------------------------------------- interfaz

st.markdown("""
<style>
.carta {
    background: linear-gradient(135deg, #1e3a5f 0%, #2d1e5f 100%);
    color: white; border-radius: 18px; padding: 2.2rem 1.6rem;
    text-align: center; margin: 0.8rem 0 1rem 0;
    box-shadow: 0 6px 20px rgba(0,0,0,0.25);
}
.carta .cat { font-size: 0.9rem; opacity: 0.8; letter-spacing: 1px; margin-bottom: 0.6rem; }
.carta .texto { font-size: 1.45rem; font-weight: 700; line-height: 1.35; }
.carta .pregunta { font-size: 1.0rem; margin-top: 1rem; opacity: 0.9; }
.escala-labels { display: flex; justify-content: space-between; font-size: 0.8rem; opacity: 0.7; margin-bottom: 0.3rem; }
</style>
""", unsafe_allow_html=True)


def carta_situacion(mostrar_pregunta=True):
    s = st.session_state.situacion
    pregunta = f"<div class='pregunta'>{s['pregunta']}</div>" if mostrar_pregunta else ""
    st.markdown(
        f"<div class='carta'><div class='cat'>{s['cat']} · Ronda {st.session_state.ronda}</div>"
        f"<div class='texto'>{s['texto']}</div>{pregunta}</div>",
        unsafe_allow_html=True,
    )


def labels_escala():
    s = st.session_state.situacion
    st.markdown(
        f"<div class='escala-labels'><span>1 = {s['label_min']}</span>"
        f"<span>{st.session_state.cfg['escala']} = {s['label_max']}</span></div>",
        unsafe_allow_html=True,
    )


def botones_nota(key_prefix, on_click):
    """Fila(s) de botones 1..escala. Llama on_click(n) al elegir."""
    escala = st.session_state.cfg["escala"]
    labels_escala()
    filas = [range(1, escala + 1)] if escala <= 5 else [range(1, 6), range(6, escala + 1)]
    for fila in filas:
        cols = st.columns(len(list(fila)))
        for col, n in zip(cols, fila):
            if col.button(str(n), key=f"{key_prefix}_{n}", use_container_width=True):
                on_click(n)
                st.rerun()


def sidebar_juego():
    with st.sidebar:
        st.subheader("🏆 Marcador de castigo")
        limite = st.session_state.cfg["limite"]
        for j, s in sorted(st.session_state.scores.items(), key=lambda x: -x[1]):
            st.markdown(f"**{j}**: {'🔴' * s}{'⚪' * (limite - s)} ({s}/{limite})")
        st.caption(f"Modo: {st.session_state.cfg['modo_puntaje']} · "
                   f"{st.session_state.cfg['modo_juego']}")
        st.divider()
        with st.expander("⚙️ Ajustes de IA"):
            panel_ia()
            estado = "conectada ✅" if get_api_key() else "sin key (solo mazo)"
            st.caption(f"IA: {estado} · modelo: {get_modelo()}")
        if st.button("🔄 Nueva partida", use_container_width=True):
            st.session_state.fase = "setup"
            st.rerun()


# ------------------------------------------------------------------ pantallas

def pantalla_setup():
    st.title("🐑 Rankealo")
    st.caption(f"El juego de calificar situaciones y no salirse del rebaño · "
               f"{total_situaciones()} situaciones en el mazo + IA")

    with st.form("setup"):
        nombres = st.text_area(
            "Jugadores (uno por línea)", height=120,
            placeholder="Diego\nClaudia\nPancho\n...",
        )
        modo_juego = st.radio(
            "Formato", ["📱 Pasa el celu", "🃏 Híbrido con cartas físicas"],
            captions=[
                "Un teléfono rota y cada uno vota en secreto.",
                "La app muestra la situación, votan con cartas 1-5 y luego ingresan los votos.",
            ],
        )
        modo_puntaje = st.radio(
            "Modo de puntaje", list(MODOS_PUNTAJE.keys()),
            captions=list(MODOS_PUNTAJE.values()),
        )
        categorias = st.multiselect(
            "Categorías",
            options=list(CATEGORIAS.keys()),
            default=list(CATEGORIAS.keys()),
            format_func=lambda c: CATEGORIAS[c]["nombre"],
        )
        c1, c2 = st.columns(2)
        escala = c1.selectbox("Escala de notas", [5, 10])
        limite = c2.selectbox("Puntos de castigo para perder", [3, 5, 7], index=1)
        tono = st.select_slider("Tono de la IA", options=list(TONOS.keys()), value="Medio")

        with st.expander("⚙️ Ajustes de IA (opcional)", expanded=not get_api_key()):
            panel_ia()

        if st.form_submit_button("🎮 ¡Jugar!", use_container_width=True, type="primary"):
            jugadores = [n.strip() for n in nombres.splitlines() if n.strip()]
            if len(jugadores) < 2:
                st.error("Necesitas al menos 2 jugadores (ideal 3+).")
            elif len(set(jugadores)) != len(jugadores):
                st.error("Hay nombres repetidos.")
            elif not categorias:
                st.error("Elige al menos una categoría.")
            else:
                st.session_state.cfg = {
                    "modo_juego": modo_juego, "modo_puntaje": modo_puntaje,
                    "categorias": categorias, "escala": escala,
                    "limite": limite, "tono": tono,
                }
                st.session_state.jugadores = jugadores
                st.session_state.scores = {j: 0 for j in jugadores}
                st.session_state.mazo = armar_mazo(categorias)
                st.session_state.ronda = 0
                st.session_state.prota_idx = -1
                nueva_ronda()
                st.rerun()

    if len(st.session_state.get("jugadores", [])) == 0:
        st.info("💡 Con 2 jugadores casi siempre empatan: el juego brilla con 3 o más.")


def pantalla_ronda():
    """Muestra la situación antes de votar (ambos formatos)."""
    carta_situacion()
    modo = st.session_state.cfg["modo_puntaje"]
    if modo == "🎯 Protagonista":
        st.info(f"🎯 Protagonista de la ronda: **{prota_actual()}** — el resto intenta "
                f"adivinar SU nota.")

    hibrido = "Híbrido" in st.session_state.cfg["modo_juego"]
    if hibrido:
        st.markdown("**🃏 Todos elijan su carta en secreto y revélenlas a la cuenta de 3.**")
        if modo == "🎰 Apuesta":
            st.caption("En Apuesta: cada uno muestra DOS cartas — su nota y su predicción del promedio.")
        boton = "📝 Ya votamos, ingresar cartas"
    else:
        boton = "🗳️ Comenzar votación secreta"

    if st.button(boton, type="primary", use_container_width=True):
        st.session_state.fase = "ingreso" if hibrido else "handoff"
        st.rerun()

    c1, c2 = st.columns(2)
    if c1.button("🔁 Otra situación", use_container_width=True):
        sacar_situacion()
        st.rerun()
    if get_api_key():
        if c2.button("🤖 Generar una con IA", use_container_width=True):
            with st.spinner("Pidiéndole ideas a la IA..."):
                cat = random.choice(st.session_state.cfg["categorias"])
                nuevas = generar_situaciones_ia(cat)
            if nuevas:
                st.session_state.mazo.extend(nuevas[1:])
                st.session_state.mazo.append(nuevas[0])
                sacar_situacion()
                st.rerun()
            else:
                err = st.session_state.get("_gemini_error") or "sin detalle"
                st.warning(f"La IA no respondió ({err}). Sigo con el mazo normal.")
    else:
        c2.caption("🤖 Agrega tu API key en ⚙️ Ajustes de IA (barra lateral) para generar con IA.")


def pantalla_handoff():
    """Pantalla intermedia: pásale el teléfono al siguiente jugador."""
    orden = orden_votacion()
    jugador = orden[st.session_state.voter_idx]
    st.markdown(f"<div class='carta'><div class='texto'>📲 Pásale el teléfono a<br>"
                f"{jugador}</div></div>", unsafe_allow_html=True)
    if st.button(f"✋ Soy {jugador}, estoy listo/a", type="primary", use_container_width=True):
        st.session_state.fase = "voto"
        st.rerun()


def pantalla_voto():
    orden = orden_votacion()
    jugador = orden[st.session_state.voter_idx]
    modo = st.session_state.cfg["modo_puntaje"]
    carta_situacion()

    def registrar(voto):
        st.session_state.votos[jugador] = voto
        st.session_state.voter_idx += 1
        if st.session_state.voter_idx >= len(orden):
            calcular_resultado()
            st.session_state.fase = "resultados"
        else:
            st.session_state.fase = "handoff"

    if modo == "🎯 Protagonista":
        if jugador == prota_actual():
            st.warning(f"🎯 **{jugador}**, eres el protagonista: pon tu nota REAL, en secreto.")
        else:
            st.info(f"**{jugador}**, adivina la nota que puso **{prota_actual()}**.")
    else:
        st.info(f"**{jugador}**, vota en secreto:")

    if modo == "🎰 Apuesta" and jugador != "":
        escala = st.session_state.cfg["escala"]
        opciones = list(range(1, escala + 1))
        nota = st.radio("Tu nota:", opciones, horizontal=True, index=None,
                        key=f"nota_{st.session_state.ronda}_{jugador}")
        pred = st.radio("Tu predicción del promedio del grupo:", opciones, horizontal=True,
                        index=None, key=f"pred_{st.session_state.ronda}_{jugador}")
        if st.button("✅ Confirmar y pasar el teléfono", type="primary",
                     use_container_width=True):
            if nota is None or pred is None:
                st.error("Te falta elegir la nota o la predicción.")
            else:
                registrar({"nota": nota, "pred": pred})
                st.rerun()
    else:
        botones_nota(f"v_{st.session_state.ronda}_{jugador}",
                     lambda n: registrar({"nota": n, "pred": None}))


def pantalla_ingreso():
    """Formato híbrido: ingresar las cartas que mostró cada jugador."""
    carta_situacion()
    modo = st.session_state.cfg["modo_puntaje"]
    escala = st.session_state.cfg["escala"]
    opciones = list(range(1, escala + 1))
    ronda = st.session_state.ronda

    st.markdown("**📝 Ingresa la carta que mostró cada jugador:**")
    labels_escala()
    votos = {}
    completos = True
    for j in st.session_state.jugadores:
        etiqueta = j
        if modo == "🎯 Protagonista" and j == prota_actual():
            etiqueta = f"🎯 {j} (nota real)"
        nota = st.radio(etiqueta, opciones, horizontal=True, index=None,
                        key=f"h_nota_{ronda}_{j}")
        pred = None
        if modo == "🎰 Apuesta":
            pred = st.radio(f"↳ predicción de {j}", opciones, horizontal=True, index=None,
                            key=f"h_pred_{ronda}_{j}")
        if nota is None or (modo == "🎰 Apuesta" and pred is None):
            completos = False
        votos[j] = {"nota": nota, "pred": pred}

    if st.button("🧮 Calcular resultados", type="primary", use_container_width=True):
        if not completos:
            st.error("Faltan votos por ingresar.")
        else:
            st.session_state.votos = votos
            calcular_resultado()
            st.session_state.fase = "resultados"
            st.rerun()


def pantalla_resultados():
    r = st.session_state.resultado
    carta_situacion(mostrar_pregunta=False)
    st.markdown(f"#### {r['objetivo']}")

    filas = []
    for j, v in st.session_state.votos.items():
        d = r["dist"].get(j)
        icono = "🐑" if j in r["perdedores"] else ("🎯" if d == 0 else "✅") if d is not None else "⭐"
        extra = f" · predijo {v['pred']}" if v["pred"] is not None else ""
        dist_txt = f" (distancia {d:g})" if d is not None else " (protagonista)"
        filas.append(f"{icono} **{j}**: {v['nota']}{extra}{dist_txt}")
    st.markdown("\n\n".join(filas))

    if r["perdedores"]:
        st.error(f"🐑 Punto de castigo para: **{', '.join(r['perdedores'])}**")
    else:
        st.success("🤝 Empate: nadie pierde esta ronda.")
    st.markdown(f"> 💬 *{r['comentario']}*")

    if get_api_key() and st.button("🤖 Pedir comentario a la IA"):
        with st.spinner("La IA está afilando el sarcasmo..."):
            c = comentario_ia(r, st.session_state.situacion)
        if c:
            st.session_state.resultado["comentario"] = c.strip()
            st.rerun()
        else:
            st.caption(f"⚠️ {st.session_state.get('_gemini_error') or 'La IA no respondió.'}")

    if r["eliminados"]:
        st.divider()
        perdedor = " y ".join(r["eliminados"])
        st.markdown(f"<div class='carta'><div class='cat'>FIN DEL JUEGO</div>"
                    f"<div class='texto'>💀 {perdedor} llegó al límite de castigo<br>"
                    f"¡{perdedor} pierde!</div>"
                    f"<div class='pregunta'>Penitencia: {r['penitencia']}</div></div>",
                    unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        if c1.button("⚔️ Revancha (mismo grupo)", type="primary", use_container_width=True):
            st.session_state.scores = {j: 0 for j in st.session_state.jugadores}
            nueva_ronda()
            st.rerun()
        if c2.button("🛠️ Nueva partida", use_container_width=True):
            st.session_state.fase = "setup"
            st.rerun()
    else:
        if st.button("➡️ Siguiente ronda", type="primary", use_container_width=True):
            nueva_ronda()
            st.rerun()


# ---------------------------------------------------------------------- main

if "fase" not in st.session_state:
    st.session_state.fase = "setup"

if st.session_state.fase == "setup":
    pantalla_setup()
else:
    sidebar_juego()
    {
        "ronda": pantalla_ronda,
        "handoff": pantalla_handoff,
        "voto": pantalla_voto,
        "ingreso": pantalla_ingreso,
        "resultados": pantalla_resultados,
    }[st.session_state.fase]()
