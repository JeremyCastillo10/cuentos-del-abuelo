"""Narra cada escena con voz de narrador locutor.

Motor por defecto: Microsoft Edge (gratis, sin clave ni límite), voz es-MX-JorgeNeural.
Con GOOGLE_TTS_KEY usa Google Cloud TTS; con MOTOR_VOZ=gemini usa Gemini TTS.
"""

import base64
import json
import os
import time
import urllib.error

from comun import EPISODIO, PUBLIC, CuotaDiaria, cargar_env, env, gemini
from tts_cloud import guardar_wav, sintetizar, suavizar
import tts_edge

VOZ_EDGE = env("VOZ_EDGE", "es-MX-JorgeNeural")  # locutor grave; alternativa dominicana: es-DO-EmilioNeural

# Google Cloud TTS (solo si hay GOOGLE_TTS_KEY)
VOCES_CLOUD = env(
    "VOCES_TTS",
    "es-US-Chirp3-HD-Charon,es-US-Chirp3-HD-Orus,es-US-Chirp3-HD-Fenrir,es-US-Neural2-B",
).split(",")

# Gemini TTS: cada modelo tiene su propio cupo diario; al agotarse uno se pasa al siguiente
MODELOS_TTS = [
    "gemini-3.8-flash-tts",
    "gemini-3.1-flash-tts-preview",
    "gemini-2.5-flash-preview-tts",
    "gemini-2.5-pro-preview-tts",
    "gemini-3.8-flash-lite-tts",
]
VOZ_GEMINI = env("VOZ_GEMINI", "Algenib")  # grave y con textura; alternativa: "Charon"
ESTILO = (
    "como un abuelo dominicano de campo contando una historia de miedo de noche: "
    "voz grave, pausada, en tono bajo y misterioso, con acento caribeño suave"
)


def voz_gemini(texto: str, modelos: list[str]) -> bytes:
    """PCM 24 kHz con fundido. Si el modelo lee las instrucciones en voz alta, repite solo con el texto."""
    indicacion = (
        f"Instrucción de actuación (NO la leas en voz alta): narra {ESTILO}.\n"
        f'Lee en voz alta únicamente este texto, palabra por palabra: "{texto}"'
    )
    maximo = len(texto.split()) / 1.8 + 3  # si dura mucho más, leyó las instrucciones
    con_estilo, esperas = True, 0
    while True:
        if not modelos:
            raise SystemExit("Se agotó el cupo gratis de todos los modelos de voz por hoy")
        if "lite" in modelos[0]:
            con_estilo = False  # los modelos lite leen cualquier instrucción
        try:
            r = gemini(
                modelos[0],
                {
                    "contents": [{"parts": [{"text": indicacion if con_estilo else texto}]}],
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
        if con_estilo and len(audio) / (24000 * 2) > maximo:
            print("  leyó las instrucciones; repitiendo solo con el texto")
            con_estilo = False
            continue
        return suavizar(audio)


def main() -> None:
    cargar_env()
    episodio = json.loads(EPISODIO.read_text(encoding="utf-8"))
    carpeta = PUBLIC / "audio"
    carpeta.mkdir(exist_ok=True)
    for viejo in carpeta.glob("*.*"):
        viejo.unlink()
    motor = "cloud" if os.environ.get("GOOGLE_TTS_KEY") else env("MOTOR_VOZ", "edge")
    modelos = env("GEMINI_MODELOS_TTS", ",".join(MODELOS_TTS)).split(",")
    print("Voces con", {"cloud": "Google Cloud TTS", "gemini": f"Gemini TTS ({VOZ_GEMINI})"}.get(motor, f"Edge TTS ({VOZ_EDGE})"))
    for i, escena in enumerate(episodio["escenas"]):
        archivo = carpeta / f"{i:02d}.wav"
        if motor == "cloud":
            pcm = sintetizar(escena["texto"], VOCES_CLOUD, velocidad=float(env("VELOCIDAD_TTS", "0.92")))
        elif motor == "gemini":
            pcm = voz_gemini(escena["texto"], modelos)
        else:
            pcm = tts_edge.sintetizar(escena["texto"], VOZ_EDGE, velocidad=env("VELOCIDAD_EDGE", "+5%"), tono=env("TONO_EDGE", "-2Hz"))
        guardar_wav(pcm, archivo)
        escena["audio"] = f"audio/{archivo.name}"
        print(f"{archivo.name}: {escena['texto'][:70]}")
    EPISODIO.write_text(json.dumps(episodio, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
