"""Genera los efectos de sonido, la música y el grano de película en public/sfx/.

Todo se crea por código (osciladores y ruido filtrado), así que es material original y propio:
se puede monetizar sin reclamos de derechos. Se ejecuta una vez y los archivos se guardan en el repo.

    python scripts/sonidos.py
"""

import wave
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.signal import butter, sosfilt

SR = 22050
SALIDA = Path(__file__).resolve().parent.parent / "public" / "sfx"
rng = np.random.default_rng(7)


def t_de(seg: float) -> np.ndarray:
    return np.arange(int(seg * SR)) / SR


def filtro(x: np.ndarray, tipo: str, corte) -> np.ndarray:
    return sosfilt(butter(2, corte, btype=tipo, fs=SR, output="sos"), x)


def eco(x: np.ndarray, retardos=(0.11, 0.17, 0.23, 0.31), caida=0.45, cola=2.0) -> np.ndarray:
    """Reverberación sencilla: varias repeticiones con retroalimentación (da sensación de espacio vacío)."""
    y = np.concatenate([x, np.zeros(int(cola * SR))])
    salida = y.copy()
    for d in retardos:
        n = int(d * SR)
        r = np.zeros_like(y)
        for k in range(1, 8):
            if n * k >= len(y):
                break
            r[n * k :] += y[: len(y) - n * k] * (caida**k)
        salida += filtro(r, "lowpass", 3000) * 0.5
    return salida


def guardar(nombre: str, x: np.ndarray, pico: float = 0.85) -> None:
    x = x / (np.max(np.abs(x)) or 1) * pico
    with wave.open(str(SALIDA / nombre), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((x * 32767).astype("<i2").tobytes())
    print(f"  {nombre}: {len(x) / SR:.1f} s")


def bucle(x: np.ndarray, cruce: float = 2.0) -> np.ndarray:
    """Une el final con el principio para que se repita sin salto."""
    n = int(cruce * SR)
    f = np.linspace(0, 1, n)
    cuerpo = x[:-n].copy()
    cuerpo[:n] = cuerpo[:n] * f + x[-n:] * (1 - f)
    return cuerpo


def golpe() -> np.ndarray:
    """Impacto grave de cine (el "BUM" de las revelaciones)."""
    t = t_de(2.2)
    frec = 30 + 70 * np.exp(-t * 6)
    cuerpo = np.sin(2 * np.pi * np.cumsum(frec) / SR) * np.exp(-t * 2.2)
    ruido = filtro(rng.uniform(-1, 1, len(t)), "lowpass", 900) * np.exp(-t * 14) * 0.9
    return eco(cuerpo + ruido, caida=0.35, cola=1.5)


def whoosh() -> np.ndarray:
    """Barrido de aire para los cambios de foto."""
    t = t_de(0.9)
    env = np.sin(np.pi * np.clip(t / 0.9, 0, 1)) ** 2
    ruido = rng.uniform(-1, 1, len(t))
    # Dos bandas que suben de tono: suena como algo que pasa rápido
    bajo = filtro(ruido, "bandpass", (250, 900))
    alto = filtro(ruido, "bandpass", (900, 3500)) * np.clip(t / 0.9, 0, 1)
    return (bajo + alto * 0.6) * env


def subida() -> np.ndarray:
    """Tensión que crece 3 segundos y se corta en seco (antes de un giro)."""
    t = t_de(3.0)
    p = t / 3.0
    frec = 110 * 2 ** (p * 2.5)
    tono = sum(np.sin(2 * np.pi * np.cumsum(frec * m) / SR) / m for m in (1, 1.5, 2.01))
    ruido = filtro(rng.uniform(-1, 1, len(t)), "highpass", 1500)
    x = (tono * 0.5 + ruido * 0.35) * p**2.2
    x[-int(0.02 * SR) :] *= np.linspace(1, 0, int(0.02 * SR))
    return x


def latido() -> np.ndarray:
    """Latido de corazón en bucle (dos golpes por pulso, ~70 pulsaciones por minuto)."""
    t = t_de(3.4)
    x = np.zeros_like(t)
    for inicio in np.arange(0, 3.4, 0.85):
        for desfase, fuerza in ((0.0, 1.0), (0.24, 0.7)):
            s = int((inicio + desfase) * SR)
            n = int(0.22 * SR)
            tt = np.arange(n) / SR
            g = np.sin(2 * np.pi * (55 - 20 * tt / 0.22) * tt) * np.exp(-tt * 22) * fuerza
            fin = min(len(x), s + n)
            x[s:fin] += g[: fin - s]
    return filtro(x, "lowpass", 200)


def estatica() -> np.ndarray:
    """Interferencia de radio/TV, para los glitches."""
    t = t_de(0.5)
    ruido = rng.uniform(-1, 1, len(t))
    corte = (rng.uniform(0, 1, len(t) // 400 + 1) > 0.35).repeat(400)[: len(t)]
    zumbido = np.sign(np.sin(2 * np.pi * 60 * t)) * 0.25
    return (filtro(ruido, "bandpass", (600, 6000)) + zumbido) * corte * np.exp(-t * 3)


def musica_calma() -> np.ndarray:
    """Fondo inquietante y suave: acorde menor flotando + caja de música lejana."""
    dur = 50.0
    t = t_de(dur)
    x = np.zeros_like(t)
    # Acorde La menor con la segunda menor (Si bemol) que lo hace raro
    for f, a in ((110, 0.5), (130.81, 0.35), (164.81, 0.3), (116.54, 0.12), (220.4, 0.15)):
        trem = 0.7 + 0.3 * np.sin(2 * np.pi * t / (7 + f % 5) + f)
        x += a * trem * (np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * f * 1.003 * t))
    x = filtro(x, "lowpass", 700) * 0.6
    # Notas sueltas de caja de música (escala menor, muy espaciadas)
    escala = [440, 523.25, 587.33, 659.25, 698.46, 880, 466.16]
    nota = np.zeros_like(t)
    for inicio in np.arange(1.5, dur - 3, 2.3):
        if rng.uniform() < 0.3:
            continue
        f = escala[rng.integers(len(escala))]
        n = int(2.5 * SR)
        tt = np.arange(n) / SR
        s = int(inicio * SR)
        tono = (np.sin(2 * np.pi * f * tt) + 0.4 * np.sin(2 * np.pi * f * 2 * tt)) * np.exp(-tt * 2.5)
        nota[s : s + n] += tono[: len(nota) - s] * 0.22
    x += eco(nota, caida=0.5, cola=0)[: len(x)]
    viento = filtro(rng.uniform(-1, 1, len(t)), "bandpass", (200, 600)) * (0.5 + 0.5 * np.sin(2 * np.pi * t / 13))
    return bucle(x + viento * 0.25)


def musica_tension() -> np.ndarray:
    """Fondo de suspenso: zumbido grave, pulso que late y cuerdas disonantes que crecen."""
    dur = 50.0
    t = t_de(dur)
    dron = np.sin(2 * np.pi * 41.2 * t) + 0.7 * np.sin(2 * np.pi * 43.65 * t) + 0.3 * np.sin(2 * np.pi * 82.4 * t)
    dron *= 0.55
    # Pulso grave cada 0.75 s
    pulso = np.zeros_like(t)
    n = int(0.4 * SR)
    tt = np.arange(n) / SR
    bum = np.sin(2 * np.pi * (70 - 30 * tt / 0.4) * tt) * np.exp(-tt * 9)
    for inicio in np.arange(0, dur, 0.75):
        s = int(inicio * SR)
        fin = min(len(t), s + n)
        pulso[s:fin] += bum[: fin - s]
    # Cuerdas en tritono (el intervalo "del diablo") que suben y bajan
    ola = 0.5 - 0.5 * np.cos(2 * np.pi * t / 12.5)
    cuerdas = sum(
        np.sin(2 * np.pi * f * t + 0.8 * np.sin(2 * np.pi * 5.5 * t)) for f in (329.6, 466.2, 659.3)
    )
    cuerdas = filtro(cuerdas, "lowpass", 2500) * ola * 0.18
    tic = np.zeros_like(t)
    for inicio in np.arange(0.375, dur, 0.75):
        s = int(inicio * SR)
        m = int(0.015 * SR)
        tic[s : s + m] += rng.uniform(-1, 1, m) * 0.25
    return bucle(dron + pulso * 0.8 + cuerdas + filtro(tic, "highpass", 3000))


def grano() -> None:
    """Cuatro texturas de grano de película (se van alternando en el video)."""
    for k in range(4):
        ruido = rng.normal(128, 40, (480, 270)).clip(0, 255).astype("uint8")
        Image.fromarray(ruido, "L").resize((1080, 1920), Image.NEAREST).save(SALIDA / f"grano{k}.png", optimize=True)
    print("  grano0-3.png")


def main() -> None:
    SALIDA.mkdir(parents=True, exist_ok=True)
    print("Generando sonidos en", SALIDA)
    guardar("golpe.wav", golpe())
    guardar("whoosh.wav", whoosh(), 0.7)
    guardar("subida.wav", subida(), 0.7)
    guardar("latido.wav", latido())
    guardar("estatica.wav", estatica(), 0.6)
    guardar("musica_calma.wav", musica_calma(), 0.8)
    guardar("musica_tension.wav", musica_tension(), 0.8)
    grano()


if __name__ == "__main__":
    main()
