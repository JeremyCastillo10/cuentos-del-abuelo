"""Narra cada escena con Google Cloud TTS (voz femenina y pausada: la abuela)."""

import json

from comun import EPISODIO, PUBLIC, cargar_env, env
from tts_cloud import guardar_wav, sintetizar

# Voces en orden de preferencia; si la primera no está disponible se usa la siguiente
VOCES = env(
    "VOCES_TTS",
    "es-US-Chirp3-HD-Kore,es-US-Chirp3-HD-Aoede,es-US-Neural2-A,es-US-Chirp3-HD-Charon",
).split(",")
VELOCIDAD = float(env("VELOCIDAD_TTS", "0.92"))


def main() -> None:
    cargar_env()
    episodio = json.loads(EPISODIO.read_text(encoding="utf-8"))
    carpeta = PUBLIC / "audio"
    carpeta.mkdir(exist_ok=True)
    for viejo in carpeta.glob("*.*"):
        viejo.unlink()
    for i, escena in enumerate(episodio["escenas"]):
        archivo = carpeta / f"{i:02d}.wav"
        guardar_wav(sintetizar(escena["texto"], VOCES, velocidad=VELOCIDAD), archivo)
        escena["audio"] = f"audio/{archivo.name}"
        print(f"{archivo.name}: {escena['texto'][:70]}")
    EPISODIO.write_text(json.dumps(episodio, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
