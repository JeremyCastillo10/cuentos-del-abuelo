"""Genera public/musica.wav: un fondo de suspenso original (zumbido grave, viento y latidos).

Se ejecuta una vez y el archivo se guarda en el repo. Sin derechos de terceros.
"""

import array
import math
import random
import wave
from pathlib import Path

SR = 22050
DURACION = 32.0  # segundos; el video lo repite en bucle
N = int(SR * DURACION)
SALIDA = Path(__file__).resolve().parent.parent / "public" / "musica.wav"


def main() -> None:
    random.seed(13)
    buf = [0.0] * N
    # Zumbido grave con dos notas un poco desafinadas (sensación de inquietud)
    for i in range(N):
        t = i / SR
        lfo = 0.6 + 0.4 * math.sin(2 * math.pi * t / DURACION * 2)
        buf[i] += 0.22 * lfo * math.sin(2 * math.pi * 55 * t)
        buf[i] += 0.12 * lfo * math.sin(2 * math.pi * 58.3 * t)
        buf[i] += 0.05 * math.sin(2 * math.pi * 110.7 * t) * math.sin(2 * math.pi * t / 8)
    # Viento: ruido filtrado que sube y baja
    filtrado = 0.0
    for i in range(N):
        t = i / SR
        filtrado += 0.02 * (random.uniform(-1, 1) - filtrado)
        buf[i] += filtrado * (0.9 + 0.8 * math.sin(2 * math.pi * t / 11)) * 1.6
    # Latido cada ~1.2 s, muy suave
    for inicio in [k * 1.2 for k in range(int(DURACION / 1.2))]:
        for golpe in (0.0, 0.22):
            s = int((inicio + golpe) * SR)
            for j in range(int(0.18 * SR)):
                if s + j < N:
                    env = math.exp(-j / (0.04 * SR))
                    buf[s + j] += 0.18 * env * math.sin(2 * math.pi * 48 * j / SR)
    # Normalizar y que el final empalme con el inicio sin salto
    pico = max(abs(x) for x in buf) or 1
    n = int(0.5 * SR)
    for i in range(n):
        f = i / n
        buf[i] *= f
        buf[-1 - i] *= f
    datos = array.array("h", (int(x / pico * 0.8 * 32767) for x in buf))
    with wave.open(str(SALIDA), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(datos.tobytes())
    print("Música guardada en", SALIDA)


if __name__ == "__main__":
    main()
