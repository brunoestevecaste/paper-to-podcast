import streamlit as st
from utils.pdf_processor import extract_text_from_pdf
from services.gemini_llm import generate_podcast_script
from services.google_tts import text_to_audio

# --- Configuración de Página ---
st.set_page_config(
    page_title="Paper-to-Podcast",
    page_icon="🎙️",
    layout="centered"
)


st.markdown("""
    <style>
    /* Ocultar elementos default de Streamlit */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Estilo del Título */
    h1 {
        color: #213e47;
        font-family: 'Helvetica', sans-serif;
        font-weight: 300;
        text-align: center;
        margin-bottom: 2rem;
    }
    
    /* Estilo del área de carga */
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
        background-color: #1a3138; /* Un tono más oscuro */
        color: #fff;
    }
    
    /* Cajas de texto */
    .stTextArea textarea {
        background-color: #fff;
        color: #213e47;
        border: 1px solid #213e47;
    }
    </style>
""", unsafe_allow_html=True)

# --- Estado de la Sesión ---
if 'script' not in st.session_state:
    st.session_state['script'] = None
if 'audio_file' not in st.session_state:
    st.session_state['audio_file'] = None

# --- Interfaz Principal ---

st.title("Paper to Podcast 🎙️")
st.markdown("<p style='text-align: center; color: #213e47; opacity: 0.7;'>Convierte tus documentos en audio con IA de Google</p>", unsafe_allow_html=True)
st.markdown("---")

# 1. Subida de Archivo
uploaded_file = st.file_uploader("Sube tu PDF aquí", type="pdf")

if uploaded_file is not None:
    
    # Botón de Procesamiento
    if st.button("Generar Podcast Mágico ✨"):
        
        with st.status("Analizando documento...", expanded=True) as status:
            # Paso 1: Extraer Texto
            st.write("📄 Leyendo PDF...")
            raw_text = extract_text_from_pdf(uploaded_file)
            
            # Paso 2: Generar Guion con Gemini
            st.write("Gemini está escribiendo el guion...")
            script = generate_podcast_script(raw_text)
            st.session_state['script'] = script
            
            # Paso 3: Generar Audio
            st.write("Generando voces...")
            audio_bytes = text_to_audio(script)
            st.session_state['audio_file'] = audio_bytes
            
            status.update(label="¡Podcast listo!", state="complete", expanded=False)

# --- Visualización de Resultados ---
if st.session_state['script']:
    st.markdown("### 🎧 Tu Podcast")
    
    # Reproductor de Audio
    if st.session_state['audio_file']:
        st.audio(st.session_state['audio_file'], format='audio/mp3')
        
        # Botón de descarga
        st.download_button(
            label="Descargar MP3",
            data=st.session_state['audio_file'],
            file_name="mi_podcast.mp3",
            mime="audio/mp3"
        )

    st.markdown("---")
    
    # Mostrar el Guion
    with st.expander("Ver el guion generado"):
        st.write(st.session_state['script'])