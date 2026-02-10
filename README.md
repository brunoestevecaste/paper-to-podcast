# Paper-to-Podcast

## Descripción General

Paper-to-Podcast es una aplicación web desarrollada en Python utilizando el framework Streamlit. Su propósito principal es transformar documentos técnicos, académicos o extensos (en formato PDF) en contenido de audio digerible con formato de podcast o diálogo conversacional.

La aplicación utiliza la infraestructura de Inteligencia Artificial de Google, específicamente los modelos generativos Gemini (vía Google AI Studio) para el procesamiento de lenguaje natural y la generación de guiones, junto con servicios de síntesis de voz (Text-to-Speech) para la producción del audio final.

## Características Principales

* **Extracción de Texto:** Procesamiento automático de archivos PDF para la extracción de contenido textual crudo.
* **Generación de Guiones con IA:** Utilización del modelo Google Gemini 1.5 (Flash/Pro) para analizar el texto, sintetizar los puntos clave y reformular el contenido en un diálogo estructurado entre dos interlocutores.
* **Síntesis de Voz (TTS):** Conversión del guion generado a un archivo de audio (MP3) utilizando tecnologías de Text-to-Speech.
* **Interfaz Minimalista:** Diseño de interfaz de usuario limpio y funcional, optimizado para la legibilidad y la facilidad de uso.

## Arquitectura del Sistema

El flujo de datos de la aplicación sigue una arquitectura lineal de cuatro etapas:

1.  **Ingesta:** El usuario carga un archivo PDF a través de la interfaz de Streamlit.
2.  **Procesamiento:** El módulo `pdf_processor` utiliza `PyPDF2` para extraer la cadena de texto del documento.
3.  **Transformación (LLM):** El texto extraído se envía a la API de Google Generative AI. Mediante ingeniería de prompts, el modelo Gemini convierte el contenido técnico en un guion conversacional.
4.  **Síntesis:** El guion resultante es procesado por el módulo `google_tts` (gTTS) para generar el archivo de audio final, que se presenta al usuario para su reproducción o descarga.

## Requisitos Previos

* Python 3.9 o superior.
* Una cuenta de Google AI Studio y una API Key válida.
* Conexión a internet para realizar las llamadas a la API.

## Instalación y Configuración

Siga los siguientes pasos para ejecutar el proyecto en un entorno local.

### 1. Clonar el repositorio

```bash
git clone [https://github.com/usuario/paper-to-podcast.git](https://github.com/usuario/paper-to-podcast.git)
cd paper-to-podcast