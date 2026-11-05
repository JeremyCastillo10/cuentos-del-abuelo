"""Publicación en la página de Facebook: fotos con texto (crónicas) y Reels (el mismo video de Instagram)."""

import json
import sys
import time
import urllib.error
import urllib.request
import uuid

from comun import EPISODIO, RAIZ, cargar_env, env, http

API = "https://graph.facebook.com/v21.0"


_token = {}


def token_pagina() -> str:
    """Token de la página. Si en FB_PAGE_TOKEN se guardó un token de usuario, saca de él el de la página."""
    if "t" not in _token:
        token, pagina = env("FB_PAGE_TOKEN"), env("FB_PAGE_ID")
        dueno = http(f"{API}/me?fields=id&access_token={token}").get("id")
        if dueno != pagina:
            cuentas = http(f"{API}/me/accounts?fields=id,name,access_token&limit=100&access_token={token}")["data"]
            elegida = next((c for c in cuentas if c["id"] == pagina), None)
            if not elegida:
                raise SystemExit(f"El token no administra la página {pagina}: {[c['name'] for c in cuentas]}")
            print("Usando el token de la página", elegida["name"], "(sacado del token de usuario)")
            token = elegida["access_token"]
        _token["t"] = token
    return _token["t"]


def _multipart_varios(campos: dict, archivos: list[tuple[str, str, bytes, str]]) -> tuple[bytes, str]:
    """Cuerpo multipart con varios archivos: (campo, nombre, bytes, tipo)."""
    limite = uuid.uuid4().hex
    partes = []
    for k, v in campos.items():
        partes.append(f'--{limite}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
    for campo, nombre, datos, mime in archivos:
        partes.append(
            f'--{limite}\r\nContent-Disposition: form-data; name="{campo}"; filename="{nombre}"\r\n'
            f"Content-Type: {mime}\r\n\r\n".encode() + datos + b"\r\n"
        )
    partes.append(f"--{limite}--\r\n".encode())
    return b"".join(partes), f"multipart/form-data; boundary={limite}"


def _multipart(campos: dict, archivo: tuple[str, bytes, str]) -> tuple[bytes, str]:
    limite = uuid.uuid4().hex
    partes = []
    for k, v in campos.items():
        partes.append(f'--{limite}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
    nombre, datos, tipo = archivo
    partes.append(
        f'--{limite}\r\nContent-Disposition: form-data; name="source"; filename="{nombre}"\r\n'
        f"Content-Type: {tipo}\r\n\r\n".encode()
        + datos
        + b"\r\n"
    )
    partes.append(f"--{limite}--\r\n".encode())
    return b"".join(partes), f"multipart/form-data; boundary={limite}"


def publicar_foto(ruta_png, mensaje: str) -> str:
    """Publica una imagen con texto en el muro de la página."""
    pagina, token = env("FB_PAGE_ID"), token_pagina()
    cuerpo, tipo = _multipart(
        {"message": mensaje, "access_token": token},
        ("cronica.png", ruta_png.read_bytes(), "image/png"),
    )
    req = urllib.request.Request(f"{API}/{pagina}/photos", data=cuerpo, headers={"Content-Type": tipo})
    with urllib.request.urlopen(req, timeout=180) as r:
        resultado = json.loads(r.read())
    print("Publicado en Facebook:", resultado.get("post_id") or resultado.get("id"))
    return resultado.get("post_id") or resultado["id"]


def comentar(post_id: str, mensaje: str) -> str | None:
    """Primer comentario en un post de la página (para poner ahí el enlace a la noticia)."""
    token = token_pagina()
    try:
        resultado = http(f"{API}/{post_id}/comments", {"message": mensaje, "access_token": token})
    except Exception as e:  # si el comentario falla, el post ya está publicado: no tumbar la crónica
        print("No se pudo comentar el enlace:", e)
        return None
    print("Comentario con enlace:", resultado.get("id"))
    return resultado.get("id")


def publicar_enlace(enlace: str, mensaje: str) -> str:
    """Publica texto con enlace a una noticia; Facebook muestra la foto del medio en la vista previa."""
    pagina, token = env("FB_PAGE_ID"), token_pagina()
    resultado = http(f"{API}/{pagina}/feed", {"message": mensaje, "link": enlace, "access_token": token})
    print("Publicado en Facebook:", resultado["id"])
    return resultado["id"]


def publicar_reel(ruta_mp4, descripcion: str) -> str:
    """Sube un Reel a la página en tres fases: iniciar, subir el archivo y publicar."""
    pagina, token = env("FB_PAGE_ID"), token_pagina()
    video = ruta_mp4.read_bytes()
    inicio = http(f"{API}/{pagina}/video_reels", {"upload_phase": "start", "access_token": token})
    video_id = inicio["video_id"]
    http(
        inicio.get("upload_url") or f"https://rupload.facebook.com/video-upload/v21.0/{video_id}",
        video,
        {"Authorization": f"OAuth {token}", "offset": "0", "file_size": str(len(video)), "Content-Type": "application/octet-stream"},
        "POST",
    )
    http(
        f"{API}/{pagina}/video_reels",
        {
            "upload_phase": "finish",
            "video_id": video_id,
            "video_state": "PUBLISHED",
            "description": descripcion,
            "access_token": token,
        },
    )
    # Facebook procesa el video después de publicar; esperamos a que quede listo
    for _ in range(40):
        estado = http(f"{API}/{video_id}?fields=status&access_token={token}")["status"]
        print("estado Facebook:", estado.get("video_status"))
        if estado.get("video_status") in ("ready", "published"):
            break
        if estado.get("video_status") == "error":
            raise SystemExit(f"Facebook rechazó el Reel: {estado}")
        time.sleep(15)
    print("Reel publicado en Facebook:", video_id)
    return video_id


def _post_video(pagina: str, campos: dict, archivos: list | None = None, intentos: int = 4) -> dict:
    """POST a /videos de graph-video con reintentos (cortes de red y errores pasajeros)."""
    cuerpo, tipo = _multipart_varios(campos, archivos or [])
    for intento in range(1, intentos + 1):
        req = urllib.request.Request(
            f"https://graph-video.facebook.com/v21.0/{pagina}/videos", data=cuerpo, headers={"Content-Type": tipo}
        )
        try:
            with urllib.request.urlopen(req, timeout=600) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            detalle = e.read().decode(errors="ignore")[:600]
            print(f"Facebook respondió {e.code} (intento {intento}): {detalle}")
            if intento == intentos or e.code not in (400, 500, 502, 503):
                raise SystemExit(f"Facebook no aceptó el video: {detalle}")
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            print(f"Corte de conexión con Facebook (intento {intento}): {e}")
            if intento == intentos:
                raise
        time.sleep(20 * intento)
    raise AssertionError


def publicar_video(ruta_mp4, titulo: str, descripcion: str, portada=None) -> str:
    """Video en la página (Facebook lo muestra también como Reel), con título y miniatura propia.

    Se sube por trozos (subida reanudable): con videos de 100 MB o más, la subida de una sola vez se corta.
    """
    pagina, token = env("FB_PAGE_ID"), token_pagina()
    datos = ruta_mp4.read_bytes()
    inicio = _post_video(pagina, {"upload_phase": "start", "file_size": str(len(datos)), "access_token": token})
    sesion, video_id = inicio["upload_session_id"], inicio["video_id"]
    desde, hasta = int(inicio["start_offset"]), int(inicio["end_offset"])
    while desde < hasta:
        r = _post_video(
            pagina,
            {"upload_phase": "transfer", "upload_session_id": sesion, "start_offset": str(desde), "access_token": token},
            [("video_file_chunk", "trozo.mp4", datos[desde:hasta], "application/octet-stream")],
        )
        desde, hasta = int(r["start_offset"]), int(r["end_offset"])
        print(f"  subido {desde // 1048576} de {len(datos) // 1048576} MB")
    _post_video(
        pagina,
        {"upload_phase": "finish", "upload_session_id": sesion, "title": titulo, "description": descripcion,
         "published": "true", "access_token": token},
    )
    print("Video publicado en Facebook:", video_id)
    if portada and portada.exists():
        try:
            cuerpo, tipo = _multipart_varios(
                {"is_preferred": "true", "access_token": token}, [("source", "portada.jpg", portada.read_bytes(), "image/jpeg")]
            )
            req = urllib.request.Request(f"{API}/{video_id}/thumbnails", data=cuerpo, headers={"Content-Type": tipo})
            with urllib.request.urlopen(req, timeout=120) as r:
                print("Portada puesta:", r.read().decode()[:100])
        except Exception as e:  # el video ya está publicado: sin portada propia no es grave
            detalle = e.read().decode(errors="ignore")[:300] if hasattr(e, "read") else e
            print("No se pudo poner la portada:", detalle)
    return video_id


def duracion(ruta_mp4) -> float:
    import subprocess

    salida = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(ruta_mp4)],
        check=True, capture_output=True, text=True,
    ).stdout
    return float(salida.strip())


if __name__ == "__main__":
    # Uso: python scripts/facebook.py reel -> sube out/episodio.mp4 como Reel (<= 90 s) o como video
    cargar_env()
    if sys.argv[1:] == ["reel"]:
        episodio = json.loads(EPISODIO.read_text(encoding="utf-8"))
        ruta = RAIZ / "out" / "episodio.mp4"
        if duracion(ruta) <= 89:
            publicar_reel(ruta, episodio.get("caption", ""))
        else:
            video_id = publicar_video(
                ruta, episodio.get("titulo_facebook") or episodio.get("titulo", ""), episodio.get("caption", ""),
                RAIZ / "out" / "portada.jpg",
            )
            fuentes = (episodio.get("fuente") or {}).get("fuentes") or []
            if fuentes:
                # Las fuentes en el primer comentario: da confianza y el comentario suma interacción
                comentar(video_id, "📚 Fuentes consultadas para esta historia: " + ", ".join(fuentes[:8])
                         + "\n\n¿Conocías este caso? Cuéntanos qué crees que pasó 👇")
