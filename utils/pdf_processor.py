import PyPDF2

def extract_text_from_pdf(uploaded_file):
    """Extrae todo el texto de un archivo PDF subido."""
    try:
        pdf_reader = PyPDF2.PdfReader(uploaded_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        return f"Error al leer el PDF: {e}"