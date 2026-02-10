from gtts import gTTS
from io import BytesIO

def text_to_audio(text, language='es'):
    """Convierte texto a audio usando Google TTS."""
    try:
        # Usamos gTTS (Google Text-to-Speech wrapper)
        tts = gTTS(text=text, lang=language, slow=False)
        
        # Guardamos en memoria (buffer) en lugar de disco
        mp3_fp = BytesIO()
        tts.write_to_fp(mp3_fp)
        mp3_fp.seek(0)
        return mp3_fp
    except Exception as e:
        return None