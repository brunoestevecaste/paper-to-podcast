import google.generativeai as genai
import streamlit as st
import os

# Configuración inicial
def configure_gemini():
    try:
        api_key = st.secrets["GOOGLE_API_KEY"]
        genai.configure(api_key=api_key)
        return True
    except Exception as e:
        st.error("Falta la API Key en .streamlit/secrets.toml")
        return False

def generate_podcast_script(text_content):
    """Usa Gemini Pro para convertir texto técnico en un diálogo."""
    if not configure_gemini():
        return None

    # Usamos Gemini 1.5 Flash para rapidez, o Pro para calidad
    model = genai.GenerativeModel('gemini-3-flash-preview')

    prompt = f"""
    Eres un guionista de podcasts experto y creativo.
    
    TU TAREA:
    Convierte el siguiente texto (extraído de un documento PDF) en un guion de podcast atractivo entre dos personas: Alex (Curioso) y Sam (Experto).
    
    REGLAS:
    1. Idioma: Español.
    2. Tono: Conversacional, educativo, dinámico y minimalista.
    3. Estructura: 
       - Breve intro.
       - Discusión de los 3 puntos más importantes del texto.
       - Conclusión rápida.
    4. Formato de salida: Solo el texto del diálogo. No uses acotaciones de sonido como [Música] o [Aplausos].
    
    TEXTO ORIGINAL:
    {text_content[:30000]}  # Limitamos caracteres por seguridad
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error en Gemini: {e}"