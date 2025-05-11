import speech_recognition as sr
from pydub import AudioSegment
import os
import uuid

def voice_to_text(file_path, language="ru-RU"):
    audio = AudioSegment.from_ogg(file_path)
    temp_wav_path = f"temp_{uuid.uuid4()}.wav"

    try:
        audio.export(temp_wav_path, format="wav")

        recognizer = sr.Recognizer()
        with sr.AudioFile(temp_wav_path) as source:
            audio_data = recognizer.record(source)
            try:
                text = recognizer.recognize_google(audio_data, language=language)
                return text
            except sr.UnknownValueError:
                return "Не удалось распознать речь"
    finally:
        if os.path.exists(temp_wav_path):
            os.remove(temp_wav_path)