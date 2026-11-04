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
ESTILO = (
    "como un locutor profesional de historias de misterio y terror, en español latino neutro: voz masculina "
    "grave y envolvente, con emoción real. Crea suspenso: pausas dramáticas antes de los datos importantes, "
    "baja la voz casi a un susurro en los momentos de tensión, sube la intensidad en los giros y suena "
    "inquietante en las preguntas. Ritmo ágil, sin leer de forma plana"
)


class SinVozGemini(Exception):
    """Gemini no pudo narrar (sin cupo o caído)."""


def voz_gemini(texto: str, modelos: list[str]) -> bytes:
    """PCM 24 kHz con fundido. Si el modelo lee las instrucciones en voz alta, se descarta y reintenta."""
    indicacion = (
        f"Instrucción de actuación (NO la leas en voz alta): narra {ESTILO}.\n"
        f'Lee en voz alta únicamente este texto, palabra por palabra: "{texto}"'
    )
    # A unas 2,3 palabras por segundo; si dura mucho más, leyó también las instrucciones
    maximo = len(texto.split()) / 1.6 + 4
    esperas, repeticiones = 0, 0
    while True:
        if not modelos:
            raise SinVozGemini("sin cupo en todos los modelos de voz")
        try:
            r = gemini(
                modelos[0],
                {
                    "contents": [{"parts": [{"text": indicacion}]}],
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
        if len(audio) / (24000 * 2) > maximo:
            repeticiones += 1
            if repeticiones > 2:
                raise SinVozGemini("el modelo sigue leyendo las instrucciones")
            print("  leyó las instrucciones; repitiendo")
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
