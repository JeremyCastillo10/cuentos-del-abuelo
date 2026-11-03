"""Voces con Google Cloud Text-to-Speech (API REST con clave).

La clave va en GOOGLE_TTS_KEY. En LINEAR16 la API ya devuelve el WAV con cabecera,
así que solo se extrae el audio y se le pone un fundido corto al inicio y al final.
"""

import array
import base64
import io
import sys
import urllib.error
import wave

from comun import env, http

URL = "https://texttospeech.googleapis.com/v1/text:synthesize"
RATE = 24000


def _pcm_de_wav(datos: bytes) -> bytes:
    with wave.open(io.BytesIO(datos)) as w:
        return w.readframes(w.getnframes())


def suavizar(pcm: bytes, rate: int = RATE, fundido: float = 0.03, silencio: float = 0.12) -> bytes:
    """Fundido de entrada y salida y un poco de silencio alrededor, para que no suene un corte."""
    muestras = array.array("h", pcm)
    if sys.byteorder == "big":
        muestras.byteswap()
    n = min(len(muestras) // 2, int(rate * fundido))
    for i in range(n):
        f = i / n
        muestras[i] = int(muestras[i] * f)
        muestras[-1 - i] = int(muestras[-1 - i] * f)
    relleno = array.array("h", [0]) * int(rate * silencio)
    salida = relleno + muestras + relleno
    if sys.byteorder == "big":
        salida.byteswap()
    return salida.tobytes()


def sintetizar(texto: str, voces: list[str], idioma: str = "es-US", velocidad: float = 1.0) -> bytes:
    """Devuelve PCM 16 bits mono a 24 kHz. Prueba las voces en orden hasta que una funcione."""
    errores = []
    for voz in voces:
        cuerpo = {
            "input": {"text": texto},
            "voice": {"languageCode": idioma, "name": voz},
            "audioConfig": {"audioEncoding": "LINEAR16", "sampleRateHertz": RATE, "speakingRate": velocidad},
        }
        try:
            r = http(URL, cuerpo, {"x-goog-api-key": env("GOOGLE_TTS_KEY")})
            return suavizar(_pcm_de_wav(base64.b64decode(r["audioContent"])))
        except urllib.error.HTTPError as e:
            detalle = e.read().decode(errors="ignore")[:300]
            errores.append(f"{voz} {e.code}: {detalle}")
            print(f"Cloud TTS {voz} respondió {e.code}: {detalle}")
            if e.code in (401, 403):
                break  # clave mal o API sin activar: las otras voces fallarán igual
    raise RuntimeError("Google Cloud TTS no generó el audio: " + " | ".join(errores))


def guardar_wav(pcm: bytes, ruta) -> None:
    with wave.open(str(ruta), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(pcm)
