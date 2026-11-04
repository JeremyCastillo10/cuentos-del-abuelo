"""Publica out/episodio.mp4 como Reel de Instagram.

Instagram descarga el video desde una URL pública (video_url). La subida directa
(upload_type=resumable) solo funciona con tokens de Facebook Login for Business,
así que el MP4 se publica temporalmente como asset de una release de GitHub y
se borra al terminar.
"""

import json
import os
import subprocess
import time
import urllib.error
from datetime import datetime, timezone

from comun import EPISODIO, RAIZ, cargar_env, env, http

API = "https://graph.facebook.com/v21.0"


def llamar(url: str, datos: dict | None = None) -> dict:
    """Como http(), pero muestra el mensaje de error de Meta si la petición falla."""
    try:
        return http(url, datos)
    except urllib.error.HTTPError as e:
        cuerpo = e.read().decode(errors="ignore")
        raise SystemExit(f"Error de Instagram {e.code}: {cuerpo}") from e


def subir_a_release(rutas: list, repo: str) -> tuple[str, list[str]]:
    """Sube los archivos a una release temporal y devuelve (tag, URLs públicas)."""
    tag = "reel-" + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    subprocess.run(
        ["gh", "release", "create", tag, *map(str, rutas), "--repo", repo, "--title", tag, "--notes", "Reel temporal para Instagram"],
        check=True,
    )
    return tag, [f"https://github.com/{repo}/releases/download/{tag}/{r.name}" for r in rutas]


def borrar_release(tag: str, repo: str) -> None:
    subprocess.run(["gh", "release", "delete", tag, "--repo", repo, "--yes", "--cleanup-tag"], check=False)


def main() -> None:
    cargar_env()
    usuario = env("IG_USER_ID")
    token = env("IG_ACCESS_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY") or env("GH_REPO")
    ruta = RAIZ / "out" / "episodio.mp4"
    caption = json.loads(EPISODIO.read_text(encoding="utf-8")).get("caption", "")

    portada = RAIZ / "out" / "portada.jpg"
    rutas = [ruta] + ([portada] if portada.exists() else [])
    tag, urls = subir_a_release(rutas, repo)
    try:
        # 1. Crear el contenedor del Reel apuntando al video público (y a la miniatura, si hay)
        datos = {"media_type": "REELS", "video_url": urls[0], "caption": caption, "access_token": token}
        if len(urls) > 1:
            datos["cover_url"] = urls[1]
        contenedor = llamar(f"{API}/{usuario}/media", datos)["id"]

        # 2. Esperar a que Instagram descargue y procese el video
        for _ in range(40):
            estado = llamar(f"{API}/{contenedor}?fields=status_code,status&access_token={token}")
            print("estado:", estado.get("status_code"))
            if estado.get("status_code") == "FINISHED":
                break
            if estado.get("status_code") == "ERROR":
                raise SystemExit(f"Instagram rechazó el video: {estado}")
            time.sleep(15)
        else:
            raise SystemExit("Instagram tardó demasiado procesando el video")

        # 3. Publicar
        publicado = llamar(f"{API}/{usuario}/media_publish", {"creation_id": contenedor, "access_token": token})
        print("Publicado:", publicado["id"])
    finally:
        borrar_release(tag, repo)


if __name__ == "__main__":
    main()
