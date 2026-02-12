import google.generativeai as genai


def configure_gemini(api_key):
    try:
        if not api_key:
            return False
        genai.configure(api_key=api_key)
        return True
    except Exception:
        return False


def generate_podcast_script(text_content, api_key):
    """Usa Gemini Pro para convertir texto tecnico en un dialogo."""
    if not configure_gemini(api_key):
        return None

    model = genai.GenerativeModel("gemini-3-flash-preview")

    prompt = f"""
    Eres un guionista de podcasts experto y creativo.

    TU TAREA:
    Convierte el siguiente texto (extraido de un documento PDF) en un guion de podcast atractivo entre dos personas: Alex (Curioso) y Sam (Experto).

    REGLAS:
    1. Idioma: Espanol.
    2. Tono: Conversacional, educativo, dinamico y minimalista.
    3. Estructura:
       - Breve intro.
       - Discusion de los 3 puntos mas importantes del texto.
       - Conclusion rapida.
    4. Formato de salida: Solo el texto del dialogo. No uses acotaciones de sonido como [Musica] o [Aplausos].

    TEXTO ORIGINAL:
    {text_content[:30000]}  # Limitamos caracteres por seguridad
    """

    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error en Gemini: {e}"
