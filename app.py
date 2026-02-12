import streamlit as st
from textwrap import dedent
from utils.pdf_processor import extract_text_from_pdf
from services.gemini_llm import (
    answer_question_with_rag,
    build_rag_index,
    generate_infographic_image,
    generate_podcast_script,
)
from services.google_tts import text_to_audio

# --- Configuracion de Pagina ---
st.set_page_config(
    page_title="Paper-to-Podcast",
    page_icon="🎙️",
    layout="centered"
)


st.markdown(
    dedent(
        """
<style>
@import url('https://fonts.googleapis.com/css2?family=Hind+Madurai:wght@300;400;500;600;700&family=Lora:wght@400;500;600;700&family=Montserrat:wght@500;600;700;800&display=swap');

:root {
    --font-title: 'Montserrat', sans-serif;
    --font-subtitle: 'Lora', serif;
    --font-body: 'Hind Madurai', sans-serif;
}

/* Ocultar elementos default de Streamlit */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

/* Tipografia global (texto) */
html, body, .stApp,
[data-testid="stAppViewContainer"],
[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] li,
[data-testid="stMarkdownContainer"] span,
[data-testid="stTextInput"] label p,
[data-testid="stFileUploader"] label,
[data-testid="stButton"] button,
[data-testid="stDownloadButton"] button,
[data-testid="stExpander"] summary,
[data-testid="stTextInput"] input,
.stTextArea textarea {
    font-family: var(--font-body) !important;
}

/* Titulos */
h1,
[data-testid="stMarkdownContainer"] h1 {
    color: #213e47;
    font-family: var(--font-title) !important;
    font-weight: 700 !important;
    text-align: center;
    margin-bottom: 2rem;
}

/* Subtitulos */
h2, h3, h4,
[data-testid="stMarkdownContainer"] h2,
[data-testid="stMarkdownContainer"] h3,
[data-testid="stMarkdownContainer"] h4,
.api-key-title, .app-subtitle {
    font-family: var(--font-subtitle) !important;
}

.app-subtitle {
    text-align: center;
    color: #213e47;
    opacity: 0.7;
}

/* Bloque minimalista para API Key */
.api-key-card {
    border: 1px solid #213e47;
    border-radius: 10px;
    background: #f9dec4;
    padding: 0.75rem 1rem;
    margin-bottom: 0.6rem;
}
.api-key-title {
    color: #213e47;
    font-weight: 700;
    margin: 0;
}
.api-key-copy {
    color: #213e47;
    opacity: 0.8;
    margin: 0.2rem 0 0 0;
    font-size: 0.92rem;
}

/* Estilo del area de carga */
.stFileUploader {
    border: 1px dashed #213e47;
    border-radius: 10px;
    padding: 10px;
}

/* Botones Personalizados */
div.stButton > button {
    background-color: #213e47;
    color: #f9dec4;
    border: none;
    border-radius: 5px;
    padding: 0.5rem 1rem;
    font-weight: bold;
    width: 100%;
    transition: all 0.3s;
}
div.stButton > button:hover {
    background-color: #1a3138;
    color: #fff;
}

/* Inputs */
.stTextArea textarea,
div[data-testid="stTextInput"] input {
    background-color: #fff;
    color: #213e47;
    border: 1px solid #213e47;
}
div[data-testid="stTextInput"] label p {
    color: #213e47;
    font-weight: 600;
}
</style>
"""
    ),
    unsafe_allow_html=True,
)

# --- Estado de la Sesion ---
if "script" not in st.session_state:
    st.session_state["script"] = None
if "audio_file" not in st.session_state:
    st.session_state["audio_file"] = None
if "infographic_image" not in st.session_state:
    st.session_state["infographic_image"] = None
if "pdf_text" not in st.session_state:
    st.session_state["pdf_text"] = None
if "pdf_token" not in st.session_state:
    st.session_state["pdf_token"] = None
if "rag_index" not in st.session_state:
    st.session_state["rag_index"] = None
if "chat_messages" not in st.session_state:
    st.session_state["chat_messages"] = []

# --- Interfaz Principal ---

st.title("Paper to Podcast 🎙️")
st.markdown("<p class='app-subtitle'>Convierte tus documentos en audio con IA de Google</p>", unsafe_allow_html=True)
st.markdown("---")

st.markdown(
    """
    <div class="api-key-card">
        <p class="api-key-title">Tu API Key de Google</p>
        <p class="api-key-copy">Introduce tu clave para generar el guion. No se guarda en el proyecto.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

api_key = st.text_input(
    "API Key",
    type="password",
    placeholder="Introduce tu API key de Google...",
    help="Se usa solo en esta sesion para llamar a Gemini.",
)

# 1. Subida de Archivo
uploaded_file = st.file_uploader("Sube tu PDF aqui", type="pdf")

if uploaded_file is not None:
    current_pdf_token = f"{uploaded_file.name}:{uploaded_file.size}"

    if st.session_state["pdf_token"] != current_pdf_token:
        raw_text = extract_text_from_pdf(uploaded_file)
        if raw_text.startswith("Error al leer el PDF:"):
            st.session_state["pdf_text"] = None
            st.session_state["pdf_token"] = None
            st.session_state["rag_index"] = None
            st.session_state["chat_messages"] = []
            st.error(raw_text)
            st.stop()

        st.session_state["pdf_token"] = current_pdf_token
        st.session_state["pdf_text"] = raw_text
        st.session_state["rag_index"] = None
        st.session_state["chat_messages"] = []
        st.session_state["script"] = None
        st.session_state["audio_file"] = None
        st.session_state["infographic_image"] = None

    if st.session_state["pdf_text"]:
        st.caption(
            f"PDF listo para preguntas ({len(st.session_state['pdf_text'].split()):,} palabras extraidas)."
        )

    # Boton de Procesamiento
    if st.button("Generar Podcast e Infografia"):
        clean_key = api_key.strip()
        if not clean_key:
            st.warning("Introduce tu API key para continuar.")
        else:
            with st.status("Analizando documento...", expanded=True) as status:
                raw_text = st.session_state["pdf_text"]
                if not raw_text:
                    st.session_state["script"] = None
                    st.session_state["audio_file"] = None
                    st.session_state["infographic_image"] = None
                    status.update(label="No se pudo leer el PDF", state="error", expanded=True)
                    st.error("No se encontro texto valido en el PDF.")
                    st.stop()

                st.write("Gemini esta escribiendo el guion...")
                script = generate_podcast_script(raw_text, clean_key)

                if not script:
                    st.session_state["script"] = None
                    st.session_state["audio_file"] = None
                    st.session_state["infographic_image"] = None
                    status.update(label="No se pudo generar el guion", state="error", expanded=True)
                    st.error("API key invalida o error de conexion con Gemini.")
                elif script.startswith("Error en Gemini:"):
                    st.session_state["script"] = None
                    st.session_state["audio_file"] = None
                    st.session_state["infographic_image"] = None
                    status.update(label="Error de Gemini", state="error", expanded=True)
                    st.error(script)
                else:
                    st.session_state["script"] = script

                    st.write("Generando infografia...")
                    infographic_image = generate_infographic_image(raw_text, clean_key)
                    if isinstance(infographic_image, str) and infographic_image.startswith("Error en Imagen:"):
                        st.session_state["infographic_image"] = None
                        st.warning(infographic_image)
                    else:
                        st.session_state["infographic_image"] = infographic_image

                    st.write("Generando voces...")
                    audio_bytes = text_to_audio(script)

                    if audio_bytes is None:
                        st.session_state["audio_file"] = None
                        status.update(label="No se pudo generar el audio", state="error", expanded=True)
                        st.error("Error al convertir el guion a audio.")
                    else:
                        st.session_state["audio_file"] = audio_bytes
                        status.update(label="Podcast listo", state="complete", expanded=False)

    st.markdown("### Chat con tu PDF (RAG)")

    clean_key = api_key.strip()
    if not clean_key:
        st.info("Introduce tu API key para activar el chat sobre el PDF.")

    for message in st.session_state["chat_messages"]:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    question = st.chat_input("Haz una pregunta especifica sobre el PDF...")
    if question:
        st.session_state["chat_messages"].append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)

        with st.chat_message("assistant"):
            if not clean_key:
                answer = "Necesito una API key de Google valida para responder."
            elif not st.session_state["pdf_text"]:
                answer = "No hay contenido del PDF disponible para consultar."
            else:
                if st.session_state["rag_index"] is None:
                    with st.spinner("Indexando PDF para RAG..."):
                        st.session_state["rag_index"] = build_rag_index(
                            st.session_state["pdf_text"],
                            clean_key,
                        )
                with st.spinner("Buscando en el documento..."):
                    answer = answer_question_with_rag(
                        question=question,
                        rag_index=st.session_state["rag_index"],
                        api_key=clean_key,
                    )

            st.markdown(answer)
            st.session_state["chat_messages"].append({"role": "assistant", "content": answer})
else:
    st.session_state["pdf_text"] = None
    st.session_state["pdf_token"] = None
    st.session_state["rag_index"] = None
    st.session_state["chat_messages"] = []

# --- Visualizacion de Resultados ---
if st.session_state["script"]:
    st.markdown("### Tu Podcast")

    # Reproductor de Audio
    if st.session_state["audio_file"]:
        st.audio(st.session_state["audio_file"], format="audio/mp3")

        # Boton de descarga
        st.download_button(
            label="Descargar MP3",
            data=st.session_state["audio_file"],
            file_name="mi_podcast.mp3",
            mime="audio/mp3"
        )

    st.markdown("---")

    if st.session_state["infographic_image"]:
        st.markdown("### Tu Infografia")
        st.image(
            st.session_state["infographic_image"],
            caption="Infografia generada con IA de Google",
            use_container_width=True,
        )
        st.download_button(
            label="Descargar Infografia (PNG)",
            data=st.session_state["infographic_image"],
            file_name="infografia.png",
            mime="image/png",
        )
        st.markdown("---")

    # Mostrar el Guion
    with st.expander("Ver el guion generado"):
        st.write(st.session_state["script"])
