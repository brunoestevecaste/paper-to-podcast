import google.generativeai as genai
import base64

try:
    from google import genai as google_genai
    from google.genai import types
except Exception:
    google_genai = None
    types = None


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


def _extract_image_bytes(response):
    """Extrae bytes de imagen de distintas formas de respuesta del SDK."""
    if not response:
        return None

    generated_images = getattr(response, "generated_images", None)
    if generated_images:
        first_image = generated_images[0]
        image_obj = getattr(first_image, "image", None)
        image_bytes = getattr(image_obj, "image_bytes", None)
        if image_bytes:
            return image_bytes

    images = getattr(response, "images", None)
    if images:
        first_image = images[0]
        image_bytes = getattr(first_image, "image_bytes", None)
        if image_bytes:
            return image_bytes

    return None


def _extract_inline_image_bytes(response):
    """Extrae bytes de imagen desde respuestas de generate_content."""
    if not response:
        return None

    parts = getattr(response, "parts", None)
    if parts:
        for part in parts:
            inline_data = getattr(part, "inline_data", None)
            if not inline_data:
                continue

            mime_type = getattr(inline_data, "mime_type", "")
            data = getattr(inline_data, "data", None)
            if not data or not str(mime_type).startswith("image/"):
                continue

            if isinstance(data, bytes):
                return data
            if isinstance(data, str):
                try:
                    return base64.b64decode(data)
                except Exception:
                    continue

    candidates = getattr(response, "candidates", None)
    if candidates:
        for candidate in candidates:
            content = getattr(candidate, "content", None)
            candidate_parts = getattr(content, "parts", None) if content else None
            if not candidate_parts:
                continue
            for part in candidate_parts:
                inline_data = getattr(part, "inline_data", None)
                if not inline_data:
                    continue
                mime_type = getattr(inline_data, "mime_type", "")
                data = getattr(inline_data, "data", None)
                if not data or not str(mime_type).startswith("image/"):
                    continue
                if isinstance(data, bytes):
                    return data
                if isinstance(data, str):
                    try:
                        return base64.b64decode(data)
                    except Exception:
                        continue

    return None


def generate_infographic_image(text_content, api_key):
    """
    Genera una infografia en PNG a partir del contenido del PDF.
    Retorna:
    - bytes de imagen (ok)
    - str con mensaje de error (fallo)
    """
    if not api_key:
        return "Error en Imagen: API key vacia."
    if google_genai is None or types is None:
        return "Error en Imagen: falta dependencia 'google-genai'. Ejecuta: pip install -r requirements.txt"

    prompt = f"""
    Eres un director creativo experto en infografias educativas.

    OBJETIVO:
    Crea una sola infografia clara y profesional en espanol, basada en el texto dado.

    INSTRUCCIONES DE DISENO:
    - Estilo: moderno, limpio, legible y minimalista.
    - Estructura:
      1) Titulo principal.
      2) Subtitulo breve.
      3) 4 a 6 bloques con los hallazgos mas relevantes.
      4) Una seccion final con "Conclusiones clave".
    - Priorizacion: incluye solo lo mas importante del documento.
    - Texto corto por bloque, sin parrafos largos.
    - Usa iconografia simple y jerarquia visual fuerte.
    - Evita contenido inventado; usa solo informacion respaldada por el texto.
    - Todo el texto dentro de la imagen debe estar en espanol.

    CONTENIDO FUENTE:
    {text_content[:30000]}
    """

    try:
        client = google_genai.Client(api_key=api_key)
        content_models = [
            "gemini-2.5-flash-image",
            "gemini-2.5-flash-image-preview",
            "gemini-3-pro-image-preview",
        ]
        model_errors = []

        for model_name in content_models:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=[prompt],
                )
                image_bytes = _extract_inline_image_bytes(response)
                if image_bytes:
                    return image_bytes
                model_errors.append(f"{model_name}: respuesta sin imagen")
            except Exception as model_error:
                model_errors.append(f"{model_name}: {model_error}")

        # Fallback opcional a Imagen API (si la cuenta tiene acceso).
        try:
            response = client.models.generate_images(
                model="imagen-3.0-generate-002",
                prompt=prompt,
                config=types.GenerateImagesConfig(
                    number_of_images=1,
                    output_mime_type="image/png",
                ),
            )
            image_bytes = _extract_image_bytes(response)
            if image_bytes:
                return image_bytes
            model_errors.append("imagen-3.0-generate-002: respuesta sin imagen")
        except Exception as imagen_error:
            model_errors.append(f"imagen-3.0-generate-002: {imagen_error}")

        return "Error en Imagen: no fue posible generar la infografia. Detalle: " + " | ".join(model_errors)
    except Exception as e:
        return f"Error en Imagen: {e}"
