"""Voces neuronales de Microsoft Edge (paquete edge-tts): gratis, sin clave ni límite de caracteres.

Ojo: es un servicio no oficial; si Microsoft lo cambia puede dejar de funcionar.
La salida MP3 se convierte con ffmpeg a PCM 24 kHz mono para ponerle el fundido.
"""

import asyncio
import subprocess
import tempfile
from pathlib import Path

from tts_cloud import RATE, suavizar


async def _guardar_mp3(texto: str, voz: str, velocidad: str, tono: str, ruta: Path) -> None:
    import edge_tts  # se instala en el workflow: pip install edge-tts

    await edge_tts.Communicate(texto, voz, rate=velocidad, pitch=tono).save(str(ruta))


def sintetizar(texto: str, voz: str, velocidad: str = "-6%", tono: str = "-3Hz", reintentos: int = 3) -> bytes:
    """PCM 16 bits mono a 24 kHz con fundido al inicio y al final."""
    ultimo = None
    for _ in range(reintentos):
        with tempfile.TemporaryDirectory() as carpeta:
            mp3 = Path(carpeta) / "voz.mp3"
            try:
                asyncio.run(_guardar_mp3(texto, voz, velocidad, tono, mp3))
                pcm = subprocess.run(
                    ["ffmpeg", "-v", "error", "-i", str(mp3), "-ac", "1", "-ar", str(RATE), "-f", "s16le", "-"],
                    check=True,
                    capture_output=True,
                ).stdout
                if pcm:
                    return suavizar(pcm)
                ultimo = RuntimeError("audio vacío")
            except Exception as e:  # red caída o respuesta rara: reintentar
                ultimo = e
                print(f"Edge TTS falló ({e}), reintentando...")
    raise RuntimeError(f"Edge TTS no generó el audio: {ultimo}")
