import base64
import json
import math
import re

try:
    import google.generativeai as genai
except Exception:
    genai = None

try:
    from google import genai as google_genai
    from google.genai import types
except Exception:
    google_genai = None
    types = None


def configure_gemini(api_key):
    try:
        if genai is None:
            return False
        if not api_key:
            return False
        genai.configure(api_key=api_key)
        return True
    except Exception:
        return False


def generate_podcast_script(text_content, api_key):
    """Usa Gemini Pro para convertir texto tecnico en un dialogo."""
    if genai is None:
        return "Error en Gemini: falta dependencia 'google-generativeai'. Ejecuta: pip install -r requirements.txt"

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


def _chunk_text(text_content, chunk_size_words=220, overlap_words=40):
    """Divide texto en chunks con solapamiento para retrieval."""
    normalized = re.sub(r"\s+", " ", text_content or "").strip()
    if not normalized:
        return []

    words = normalized.split(" ")
    if len(words) <= chunk_size_words:
        return [normalized]

    chunks = []
    step = max(1, chunk_size_words - overlap_words)
    for start in range(0, len(words), step):
        end = start + chunk_size_words
        chunk_words = words[start:end]
        if not chunk_words:
            break
        chunks.append(" ".join(chunk_words))
        if end >= len(words):
            break
    return chunks


def _parse_embedding_response(response):
    """Extrae un vector de embedding de respuestas con distintos formatos."""
    if response is None:
        return None

    if isinstance(response, dict):
        vector = response.get("embedding")
        if isinstance(vector, list) and vector and isinstance(vector[0], (int, float)):
            return vector
        if isinstance(vector, dict):
            values = vector.get("values")
            if isinstance(values, list) and values and isinstance(values[0], (int, float)):
                return values

    vector = getattr(response, "embedding", None)
    if isinstance(vector, list) and vector and isinstance(vector[0], (int, float)):
        return vector
    if isinstance(vector, dict):
        values = vector.get("values")
        if isinstance(values, list) and values and isinstance(values[0], (int, float)):
            return values

    values = getattr(response, "values", None)
    if isinstance(values, list) and values and isinstance(values[0], (int, float)):
        return values

    return None


def _cosine_similarity(vec_a, vec_b):
    if not vec_a or not vec_b:
        return -1.0

    size = min(len(vec_a), len(vec_b))
    if size == 0:
        return -1.0

    dot = 0.0
    norm_a = 0.0
    norm_b = 0.0
    for idx in range(size):
        a = float(vec_a[idx])
        b = float(vec_b[idx])
        dot += a * b
        norm_a += a * a
        norm_b += b * b

    if norm_a == 0 or norm_b == 0:
        return -1.0
    return dot / (math.sqrt(norm_a) * math.sqrt(norm_b))


def _lexical_score(question, chunk):
    """Fallback simple cuando embeddings no esten disponibles."""
    q_tokens = set(re.findall(r"\w+", (question or "").lower()))
    c_tokens = set(re.findall(r"\w+", (chunk or "").lower()))
    if not q_tokens or not c_tokens:
        return 0.0
    overlap = q_tokens.intersection(c_tokens)
    return len(overlap) / len(q_tokens)


def build_rag_index(text_content, api_key):
    """
    Crea un indice RAG en memoria.
    Retorna un dict con chunks + embeddings (si estan disponibles).
    """
    chunks = _chunk_text(text_content)
    if not chunks:
        return {"chunks": [], "embeddings": [], "retrieval_mode": "lexical"}

    # Si falla configuracion o embeddings, dejamos fallback lexical.
    if genai is None or not configure_gemini(api_key):
        return {"chunks": chunks, "embeddings": [], "retrieval_mode": "lexical"}

    embeddings = []
    for chunk in chunks:
        try:
            response = genai.embed_content(
                model="models/text-embedding-004",
                content=chunk,
                task_type="retrieval_document",
            )
            vector = _parse_embedding_response(response)
            if vector is None:
                embeddings = []
                break
            embeddings.append(vector)
        except Exception:
            embeddings = []
            break

    retrieval_mode = "semantic" if len(embeddings) == len(chunks) else "lexical"
    if retrieval_mode != "semantic":
        embeddings = []

    return {
        "chunks": chunks,
        "embeddings": embeddings,
        "retrieval_mode": retrieval_mode,
    }


def _retrieve_top_chunks(question, rag_index, api_key, top_k=4):
    chunks = (rag_index or {}).get("chunks", [])
    if not chunks:
        return []

    retrieval_mode = (rag_index or {}).get("retrieval_mode", "lexical")
    if retrieval_mode == "semantic":
        try:
            configure_gemini(api_key)
            query_response = genai.embed_content(
                model="models/text-embedding-004",
                content=question,
                task_type="retrieval_query",
            )
            query_vector = _parse_embedding_response(query_response)
            if query_vector:
                scored = []
                for idx, chunk_vector in enumerate((rag_index or {}).get("embeddings", [])):
                    score = _cosine_similarity(query_vector, chunk_vector)
                    scored.append((score, idx))
                scored.sort(reverse=True, key=lambda item: item[0])
                selected_idx = [idx for score, idx in scored[:top_k] if score >= 0.15]
                return [chunks[idx] for idx in selected_idx]
        except Exception:
            pass

    scored = []
    for idx, chunk in enumerate(chunks):
        score = _lexical_score(question, chunk)
        scored.append((score, idx))
    scored.sort(reverse=True, key=lambda item: item[0])
    selected_idx = [idx for score, idx in scored[:top_k] if score > 0]

    if not selected_idx:
        return []
    return [chunks[idx] for idx in selected_idx]


def answer_question_with_rag(question, rag_index, api_key):
    """Responde preguntas usando solo contexto recuperado del PDF."""
    if genai is None:
        return "Error en Gemini: falta dependencia 'google-generativeai'. Ejecuta: pip install -r requirements.txt"

    if not configure_gemini(api_key):
        return "Error en Gemini: API key invalida o vacia."

    top_chunks = _retrieve_top_chunks(question, rag_index, api_key=api_key, top_k=4)
    if not top_chunks:
        return "No encuentro esa informacion en el PDF."

    context_blocks = []
    for idx, chunk in enumerate(top_chunks, start=1):
        context_blocks.append(f"[C{idx}] {chunk[:1700]}")
    context = "\n\n".join(context_blocks)

    prompt = f"""
Eres un asistente de preguntas y respuestas sobre un PDF.

Reglas estrictas:
1. Responde solo con informacion contenida en el CONTEXTO.
2. Si la respuesta no esta en el CONTEXTO, responde exactamente:
   "No encuentro esa informacion en el PDF."
3. No uses conocimiento externo.
4. Responde en espanol y de forma concisa.
5. Si respondes con contenido del contexto, incluye al final "Fuentes: [C#]" con los fragmentos usados.

PREGUNTA DEL USUARIO:
{question}

CONTEXTO:
{context}
"""

    try:
        model = genai.GenerativeModel("gemini-3-flash-preview")
        response = model.generate_content(prompt)
        answer = getattr(response, "text", "") or _extract_text_from_response(response)
        return answer.strip() if answer else "No encuentro esa informacion en el PDF."
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


def _extract_text_from_response(response):
    """Extrae texto de respuestas de generate_content en distintos formatos."""
    if not response:
        return ""

    direct_text = getattr(response, "text", None)
    if isinstance(direct_text, str) and direct_text.strip():
        return direct_text

    candidates = getattr(response, "candidates", None)
    if not candidates:
        return ""

    chunks = []
    for candidate in candidates:
        content = getattr(candidate, "content", None)
        parts = getattr(content, "parts", None) if content else None
        if not parts:
            continue
        for part in parts:
            text = getattr(part, "text", None)
            if text:
                chunks.append(text)

    return "\n".join(chunks).strip()


def _extract_json_object(text):
    """Extrae el primer objeto JSON valido de un bloque de texto."""
    if not text:
        return None

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None

    candidate = text[start:end + 1]
    try:
        return json.loads(candidate)
    except Exception:
        return None


def _normalize_infographic_outline(raw_outline):
    """Normaliza el esquema para tener una estructura estable."""
    if not isinstance(raw_outline, dict):
        return None

    title = str(raw_outline.get("title", "")).strip()
    subtitle = str(raw_outline.get("subtitle", "")).strip()
    conclusion = str(raw_outline.get("conclusion", "")).strip()
    points = raw_outline.get("key_points", [])

    if not title or not subtitle or not conclusion or not isinstance(points, list):
        return None

    normalized_points = []
    for item in points[:6]:
        if not isinstance(item, dict):
            continue
        heading = str(item.get("heading", "")).strip()
        detail = str(item.get("detail", "")).strip()
        if heading and detail:
            normalized_points.append({"heading": heading, "detail": detail})

    if len(normalized_points) < 4:
        return None

    return {
        "title": title,
        "subtitle": subtitle,
        "key_points": normalized_points,
        "conclusion": conclusion,
    }


def _build_outline_prompt(text_content):
    return f"""
Eres editor senior de contenido y especialista en sintetizar documentos tecnicos.

Tu tarea:
- Analizar el contenido del PDF y producir un esquema de infografia en ESPANOL.
- Entregar SOLO un JSON valido (sin markdown, sin texto extra).

Formato JSON exacto:
{{
  "title": "string corto",
  "subtitle": "string corto",
  "key_points": [
    {{"heading": "string corto", "detail": "string corto"}}
  ],
  "conclusion": "string corto"
}}

Reglas:
- key_points debe tener entre 4 y 6 elementos.
- Texto claro, factual y coherente.
- No inventes informacion.
- Cada "detail" debe ser breve (maximo 20 palabras).

CONTENIDO DEL PDF:
{text_content[:30000]}
"""


def _generate_infographic_outline(client, text_content):
    """Genera un esquema textual coherente para la infografia."""
    prompt = _build_outline_prompt(text_content)
    outline_models = [
        "gemini-2.5-pro",
        "gemini-2.5-flash",
        "gemini-3-pro-preview",
    ]
    errors = []

    for model_name in outline_models:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=[prompt],
            )
            raw_text = _extract_text_from_response(response)
            raw_outline = _extract_json_object(raw_text)
            normalized = _normalize_infographic_outline(raw_outline)
            if normalized:
                return normalized
            errors.append(f"{model_name}: JSON invalido o incompleto")
        except Exception as model_error:
            errors.append(f"{model_name}: {model_error}")

    return f"No fue posible crear el esquema textual de la infografia. Detalle: {' | '.join(errors)}"


def _build_image_prompt_from_outline(outline):
    """Crea un prompt visual a partir del esquema (texto ya curado)."""
    sections = []
    for idx, point in enumerate(outline["key_points"], start=1):
        sections.append(f"Section {idx} title: {point['heading']}\nSection {idx} text: {point['detail']}")
    sections_block = "\n".join(sections)

    # Prompt en ingles para mejorar fidelidad visual de Imagen/Gemini, pero manteniendo texto final en espanol.
    return f"""
Create a single clean infographic poster with modern editorial style.
All visible text must be in Spanish and must match exactly the provided strings.
Do not add extra paragraphs.
Use strong hierarchy, iconography, and balanced spacing.

Use this exact text content:
Main title: {outline["title"]}
Subtitle: {outline["subtitle"]}
{sections_block}
Final section title: Conclusiones clave
Final section text: {outline["conclusion"]}

Output requirements:
- One vertical infographic image.
- High legibility typography.
- Minimal style, light background.
- No watermarks.
"""


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

    try:
        client = google_genai.Client(api_key=api_key)
        outline = _generate_infographic_outline(client, text_content)
        if isinstance(outline, str):
            return f"Error en Imagen: {outline}"

        prompt = _build_image_prompt_from_outline(outline)
        content_models = [
            "gemini-3-pro-image-preview",
            "gemini-2.5-flash-image",
        ]
        model_errors = []
        content_config = None
        if hasattr(types, "GenerateContentConfig"):
            content_config = types.GenerateContentConfig(
                response_modalities=["IMAGE", "TEXT"],
            )

        for model_name in content_models:
            try:
                request = {
                    "model": model_name,
                    "contents": [prompt],
                }
                if content_config is not None:
                    request["config"] = content_config
                response = client.models.generate_content(**request)
                image_bytes = _extract_inline_image_bytes(response)
                if image_bytes:
                    return image_bytes
                model_errors.append(f"{model_name}: respuesta sin imagen")
            except Exception as model_error:
                model_errors.append(f"{model_name}: {model_error}")

        # Fallback opcional a Imagen API (si la cuenta tiene acceso).
        try:
            response = client.models.generate_images(
                model="imagen-4.0-generate-001",
                prompt=prompt,
                config=types.GenerateImagesConfig(
                    number_of_images=1,
                    output_mime_type="image/png",
                ),
            )
            image_bytes = _extract_image_bytes(response)
            if image_bytes:
                return image_bytes
            model_errors.append("imagen-4.0-generate-001: respuesta sin imagen")
        except Exception as imagen_error:
            model_errors.append(f"imagen-4.0-generate-001: {imagen_error}")

        return "Error en Imagen: no fue posible generar la infografia. Detalle: " + " | ".join(model_errors)
    except Exception as e:
        return f"Error en Imagen: {e}"
