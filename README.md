# 🐑 Rankealo

Juego de fiesta: el grupo califica situaciones del 1 al 5 (o al 10) y pierde quien
se sale del rebaño. Incluye ~500 situaciones en 5 categorías y generación de
situaciones nuevas con IA (Gemini).

## Formatos de juego

- **📱 Pasa el celu**: un solo teléfono rota entre los jugadores; cada uno vota en
  secreto y lo pasa al siguiente. La app calcula todo y lleva el marcador.
- **🃏 Híbrido con cartas**: la app (en una pantalla visible para todos) muestra la
  situación; cada jugador vota con cartas físicas numeradas 1–5 (o papelitos, o
  dedos) y las revelan a la cuenta de 3. Luego se ingresan los votos en la app
  para calcular al perdedor y llevar el marcador.

## Modos de puntaje

- **🐑 Oveja Negra**: el más alejado de la mediana del grupo suma punto de castigo.
- **🎯 Protagonista**: cada ronda un jugador pone su nota real en secreto y el
  resto intenta adivinarla.
- **🎰 Apuesta**: además de tu nota, predices el promedio del grupo; pierde el peor
  pronóstico.

En todos los modos, al llegar al límite de puntos de castigo (configurable),
pierdes el juego y pagas penitencia.

## Correr localmente

```bash
pip install -r requirements.txt
streamlit run app.py
```

## IA (opcional)

Con una API key de [Google AI Studio](https://aistudio.google.com/apikey) el juego
puede generar situaciones nuevas por categoría y comentarios sarcásticos tras cada
ronda. Sin key, funciona igual con el banco de ~500 situaciones.

Desde **⚙️ Ajustes de IA** (en la pantalla de inicio y en la barra lateral durante
el juego) puedes pegar/cambiar la API key y elegir el modelo de Gemini
(`gemini-3.1-flash-lite` por defecto, o escribir uno nuevo a mano). La key escrita
ahí tiene prioridad sobre la de los Secrets.

- **Local**: crea `.streamlit/secrets.toml` con
  ```toml
  GEMINI_API_KEY = "tu-api-key"
  ```
  (este archivo está en `.gitignore`, nunca lo subas al repo), o simplemente pega
  la key en **⚙️ Ajustes de IA**.

## Deploy gratis en Streamlit Community Cloud

1. Sube este repo a GitHub.
2. Entra a [share.streamlit.io](https://share.streamlit.io) con tu cuenta de GitHub.
3. **New app** → elige el repo, branch `main`, archivo `app.py` → **Deploy**.
4. (Opcional, para la IA) En la app: **Settings → Secrets** y pega:
   ```toml
   GEMINI_API_KEY = "tu-api-key"
   ```
5. Comparte la URL con tus amigos. 🎉

> Nota: en el plan gratuito la app "se duerme" tras unos días sin uso; el primer
> visitante la despierta en ~1 minuto.
