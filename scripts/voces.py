"""Narra la historia con voz de locutor de historias, con emoción.

Motor principal: Gemini TTS (gratis con la clave de Google AI Studio). Narra en trozos de varias
escenas para que la interpretación fluya (suspenso, pausas, susurros) y casi no haya cortes.
Si Gemini no tiene cupo, la historia ENTERA se narra con Microsoft Edge (para no mezclar voces).
Con GOOGLE_TTS_KEY se usa Google Cloud TTS.
"""

import base64
import json
import os
import time
import urllib.error

import tts_edge
from comun import EPISODIO, PUBLIC, CuotaDiaria, cargar_env, env, gemini
from tts_cloud import guardar_wav, sintetizar, suavizar

VOCES_CLOUD = env(
    "VOCES_TTS",
    "es-US-Chirp3-HD-Charon,es-US-Chirp3-HD-Orus,es-US-Chirp3-HD-Fenrir,es-US-Neural2-B",
).split(",")
VOZ_EDGE = env("VOZ_EDGE", "es-MX-JorgeNeural")

# Sin modelos "lite": leen las instrucciones en voz alta y no sirven para actuar
MODELOS_TTS = [
    "gemini-3.8-flash-tts",
    "gemini-3.1-flash-tts-preview",
    "gemini-2.5-flash-preview-tts",
    "gemini-2.5-pro-preview-tts",
]
VOZ_GEMINI = env("VOZ_GEMINI", "Algenib")  # masculina, grave y con textura
ESCENAS_POR_TROZO = int(env("ESCENAS_POR_TROZO", "10"))  # ~1,5 min por pedido: 4-5 pedidos por historia
# Indicación corta, en el formato que recomienda Google para sus voces ("Di de tal forma: texto")
ESTILO = (
    "Narra con naturalidad, como un narrador de documentales de misterio: voz grave y serena, "
    "con emoción contenida y un toque de intriga, sin exagerar ni dramatizar"
)
# Palabras de la indicación que NO deben oírse en el audio
RASTROS = ("narra con naturalidad", "documentales", "emoción contenida", "sin exagerar", "dramatizar", "voz grave", "instrucci")


class SinVozGemini(Exception):
    """Gemini no pudo narrar (sin cupo o caído)."""


def _wav_bytes(pcm: bytes) -> bytes:
    import io
    import wave

    b = io.BytesIO()
    with wave.open(b, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(24000)
        w.writeframes(pcm)
    return b.getvalue()


def inicio_transcrito(pcm: bytes, segundos: int = 20) -> str | None:
    """Transcribe el principio del audio con Whisper de Groq. None si no se puede comprobar."""
    import urllib.request
    import uuid

    clave = os.environ.get("GROQ_API_KEY")
    if not clave:
        return None
    audio = _wav_bytes(pcm[: 24000 * 2 * segundos])
    for modelo in ("whisper-large-v3-turbo", "whisper-large-v3"):
        texto = _transcribir(audio, modelo, clave)
        if texto is not None:
            return texto
    return None


def _transcribir(audio: bytes, modelo: str, clave: str) -> str | None:
    import urllib.request
    import uuid

    limite = uuid.uuid4().hex
    partes = [
        f'--{limite}\r\nContent-Disposition: form-data; name="model"\r\n\r\n{modelo}\r\n'.encode(),
        f'--{limite}\r\nContent-Disposition: form-data; name="language"\r\n\r\nes\r\n'.encode(),
        f'--{limite}\r\nContent-Disposition: form-data; name="file"; filename="inicio.wav"\r\n'
        "Content-Type: audio/wav\r\n\r\n".encode() + audio + b"\r\n",
        f"--{limite}--\r\n".encode(),
    ]
    req = urllib.request.Request(
        "https://api.groq.com/openai/v1/audio/transcriptions",
        data=b"".join(partes),
        headers={"Authorization": f"Bearer {clave}", "Content-Type": f"multipart/form-data; boundary={limite}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read()).get("text", "")
    except Exception as e:
        print(f"  Whisper {modelo} no disponible ({e})")
        return None


def leyo_indicacion(pcm: bytes, texto: str) -> bool | None:
    """True si al principio del audio se oye la indicación; None si no se puede comprobar (sin Whisper)."""
    oido = inicio_transcrito(pcm)
    if oido is None:
        return None
    print(f"  Whisper oyó al principio: «{oido[:120]}»")
    oido = oido.lower()
    principio = " ".join(texto.lower().split()[:40])
    # Solo cuenta si la palabra se oye pero no forma parte del propio texto de la historia
    return any(r in oido and r not in principio for r in RASTROS)


# Si no se puede escuchar el audio con Whisper, no se usa indicación (así nunca se cuela en el audio)
_verificable = {"ok": True}


def voz_gemini(texto: str, modelos: list[str]) -> bytes:
    """PCM 24 kHz con fundido. Si se oye la indicación, se repite; si insiste, se narra sin indicación."""
    con_estilo, repeticiones, esperas = _verificable["ok"], 0, 0
    while True:
        if not modelos:
            raise SinVozGemini("sin cupo en todos los modelos de voz")
        pedido = f"{ESTILO}:\n{texto}" if con_estilo else texto
        try:
            r = gemini(
                modelos[0],
                {
                    "contents": [{"parts": [{"text": pedido}]}],
                    "generationConfig": {
                        "responseModalities": ["AUDIO"],
                        "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": VOZ_GEMINI}}},
                    },
                },
            )
        except CuotaDiaria:
            print(f"{modelos[0]} sin cupo por hoy, probando el siguiente modelo")
            modelos.pop(0)
            continue
        except urllib.error.HTTPError as e:
            esperas += 1
            if esperas > 3:
                print(f"{modelos[0]} sigue fallando ({e}), probando el siguiente modelo")
                modelos.pop(0)
                esperas = 0
            else:
                print(f"{modelos[0]} ocupado ({e}), esperando un minuto")
                time.sleep(60)
            continue
        audio = base64.b64decode(r["candidates"][0]["content"]["parts"][0]["inlineData"]["data"])
        leida = leyo_indicacion(audio, texto) if con_estilo else False
        if leida is None:
            print("  no se puede escuchar el audio con Whisper: se narra sin indicación")
            _verificable["ok"] = False
            con_estilo = False
            continue
        if leida:
            repeticiones += 1
            if repeticiones >= 2:
                print("  sigue leyendo la indicación: se narra este trozo sin indicación")
                con_estilo = False
            else:
                print("  se oyó la indicación en el audio; repitiendo")
            continue
        return suavizar(audio)


def narrar_con_gemini(escenas: list[dict], carpeta) -> None:
    """Un audio por trozo de escenas. El primer audio del trozo lleva la marca del grupo."""
    modelos = env("GEMINI_MODELOS_TTS", ",".join(MODELOS_TTS)).split(",")
    for g, inicio in enumerate(range(0, len(escenas), ESCENAS_POR_TROZO)):
        trozo = escenas[inicio : inicio + ESCENAS_POR_TROZO]
        texto = " ".join(e["texto"] for e in trozo)
        archivo = carpeta / f"g{g:02d}.wav"
        guardar_wav(voz_gemini(texto, modelos), archivo)
        for e in trozo:
            e["grupo"] = g
            e["palabras"] = len(e["texto"].split())
        trozo[0]["audio"] = f"audio/{archivo.name}"
        print(f"{archivo.name}: escenas {inicio}-{inicio + len(trozo) - 1}")


def narrar_por_escena(escenas: list[dict], carpeta, motor: str) -> None:
    for i, escena in enumerate(escenas):
        archivo = carpeta / f"{i:02d}.wav"
        if motor == "cloud":
            pcm = sintetizar(escena["texto"], VOCES_CLOUD, velocidad=float(env("VELOCIDAD_TTS", "1.0")))
        else:
            pcm = tts_edge.sintetizar(
                escena["texto"], VOZ_EDGE, velocidad=env("VELOCIDAD_EDGE", "+5%"), tono=env("TONO_EDGE", "-2Hz")
            )
        guardar_wav(pcm, archivo)
        escena["audio"] = f"audio/{archivo.name}"
        print(f"{archivo.name}: {escena['texto'][:70]}")


def limpiar(escenas: list[dict], carpeta) -> None:
    for e in escenas:
        for clave in ("audio", "grupo", "palabras"):
            e.pop(clave, None)
    for viejo in carpeta.glob("*.*"):
        viejo.unlink()


def main() -> None:
    cargar_env()
    episodio = json.loads(EPISODIO.read_text(encoding="utf-8"))
    escenas = episodio["escenas"]
    carpeta = PUBLIC / "audio"
    carpeta.mkdir(exist_ok=True)
    limpiar(escenas, carpeta)

    motor = "cloud" if os.environ.get("GOOGLE_TTS_KEY") else env("MOTOR_VOZ", "gemini")
    if motor == "gemini":
        try:
            print(f"Voces con Gemini TTS ({VOZ_GEMINI}), {ESCENAS_POR_TROZO} escenas por trozo")
            narrar_con_gemini(escenas, carpeta)
        except SinVozGemini as e:
            print(f"Gemini no pudo narrar ({e}): toda la historia se narra con Microsoft Edge")
            limpiar(escenas, carpeta)
            motor = "edge"
    if motor != "gemini":
        print("Voces con", "Google Cloud TTS" if motor == "cloud" else f"Edge TTS ({VOZ_EDGE})")
        narrar_por_escena(escenas, carpeta, motor)
    episodio["voz"] = motor
    EPISODIO.write_text(json.dumps(episodio, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
