"""Utilidades compartidas: rutas, .env y llamadas HTTP sin dependencias."""

import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PUBLIC = RAIZ / "public"
EPISODIO = PUBLIC / "episodio.json"

MARCA = "#CuentosDeLaAbuela"
MAX_HASHTAGS = 5  # Instagram recomienda pocos hashtags y relevantes


def ordenar_hashtags(texto: str) -> str:
    """Deja como máximo 5 hashtags al final, sin repetidos y siempre con la marca.

    Los hashtags que el modelo escriba en medio del texto se quitan de ahí y se
    juntan en la última línea, para que el texto se lea limpio.
    """
    import re

    encontrados = re.findall(r"#\w+", texto)
    limpio = re.sub(r"[ \t]*#\w+", "", texto)
    limpio = re.sub(r"\n{3,}", "\n\n", limpio).strip()
    unicos: list[str] = []
    for h in encontrados:
        if h.lower() != MARCA.lower() and h.lower() not in (u.lower() for u in unicos):
            unicos.append(h)
    etiquetas = unicos[: MAX_HASHTAGS - 1] + [MARCA]
    return f"{limpio}\n\n{' '.join(etiquetas)}"


def cargar_env() -> None:
    archivo = RAIZ / ".env"
    if not archivo.exists():
        return
    for linea in archivo.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if linea and not linea.startswith("#") and "=" in linea:
            k, v = linea.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


def env(nombre: str, defecto: str | None = None) -> str:
    valor = os.environ.get(nombre, defecto)
    if valor is None:
        raise SystemExit(f"Falta la variable {nombre} (ponla en .env o en los secrets de GitHub)")
    return valor


def http(url: str, datos: dict | bytes | None = None, headers: dict | None = None, metodo: str | None = None) -> dict:
    cuerpo = json.dumps(datos).encode() if isinstance(datos, dict) else datos
    h = {"Content-Type": "application/json", "User-Agent": "cuentos-de-la-abuela"} | (headers or {})
    req = urllib.request.Request(url, data=cuerpo, headers=h, method=metodo)
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode())


# Cada clave de Gemini tiene su propio cupo diario por modelo. Se prueban en orden:
# GEMINI_API_KEY y, si existe, GEMINI_API_KEY_2 (de otro proyecto).
_agotadas: set[tuple[str, str]] = set()


def gemini(modelo: str, cuerpo: dict, reintentos: int = 4) -> dict:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent"
    env("GEMINI_API_KEY")  # debe existir la principal
    claves = [
        (nombre, os.environ[nombre])
        for nombre in ("GEMINI_API_KEY", "GEMINI_API_KEY_2")
        if os.environ.get(nombre) and (nombre, modelo) not in _agotadas
    ]
    for nombre, clave in claves:
        try:
            return _gemini_con_clave(url, modelo, cuerpo, clave, reintentos)
        except CuotaDiaria:
            _agotadas.add((nombre, modelo))
            print(f"{nombre} sin cupo para {modelo}, probando la siguiente clave")
    raise CuotaDiaria(modelo)


def _gemini_con_clave(url: str, modelo: str, cuerpo: dict, clave: str, reintentos: int) -> dict:
    # El plan gratis a veces tarda o limita por minuto: reintentar con espera
    for intento in range(reintentos):
        try:
            return http(url, cuerpo, {"x-goog-api-key": clave})
        except urllib.error.HTTPError as e:
            detalle = e.read().decode(errors="ignore")
            if "PerDay" in detalle:
                raise CuotaDiaria(modelo) from e
            if e.code not in (429, 500, 503) or intento == reintentos - 1:
                raise
            print(f"Gemini respondió {e.code}, reintentando...")
        except (TimeoutError, urllib.error.URLError) as e:
            if intento == reintentos - 1:
                raise
            print(f"Gemini falló ({e}), reintentando...")
        time.sleep(20 * (intento + 1))
    raise AssertionError


class CuotaDiaria(Exception):
    """Se agotó el cupo gratis diario de ese modelo."""
