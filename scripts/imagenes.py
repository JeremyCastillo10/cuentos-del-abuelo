"""Busca un video o una foto real para cada escena en Pixabay y Pexels.

Primero intenta un video de archivo cuyas etiquetas coincidan con lo que se dice en la escena;
si no hay uno que encaje, usa una foto. Los videos se recortan a vertical, se oscurecen y se dejan
listos para Remotion con ffmpeg.

Las dos licencias permiten uso comercial gratis y sin atribución obligatoria
(https://www.pexels.com/license/ y https://pixabay.com/service/license-summary/).
Aun así se guarda el autor de cada foto en el episodio por transparencia.
Necesita PEXELS_API_KEY (gratis en https://www.pexels.com/api/); PIXABAY_API_KEY es opcional.
"""

import json
import os
import random
import urllib.parse
import urllib.request

from comun import EPISODIO, PUBLIC, cargar_env, http

UA = {"User-Agent": "cuentos-del-abuelo/1.0"}
MAX_VIDEOS = int(os.environ.get("MAX_VIDEOS", "24"))


def pexels(consulta: str) -> list[dict]:
    clave = os.environ.get("PEXELS_API_KEY")
    if not clave:
        return []
    q = urllib.parse.urlencode({"query": consulta, "orientation": "portrait", "size": "large", "per_page": 20})
    datos = http(f"https://api.pexels.com/v1/search?{q}", headers={"Authorization": clave} | UA)
    return [
        {"url": f["src"]["large2x"], "autor": f["photographer"], "fuente": "Pexels", "id": f"pexels-{f['id']}",
         "etiquetas": f.get("alt") or ""}
        for f in datos.get("photos", [])
    ]


def pixabay(consulta: str) -> list[dict]:
    clave = os.environ.get("PIXABAY_API_KEY")
    if not clave:
        return []
    q = urllib.parse.urlencode(
        {"key": clave, "q": consulta, "image_type": "photo", "orientation": "vertical", "safesearch": "true",
         "per_page": 40, "order": "popular"}
    )
    datos = http(f"https://pixabay.com/api/?{q}", headers=UA)
    return [
        {"url": f["largeImageURL"], "autor": f["user"], "fuente": "Pixabay", "id": f"pixabay-{f['id']}",
         "etiquetas": f.get("tags", "")}
        for f in datos.get("hits", [])
    ]


def pixabay_videos(consulta: str) -> list[dict]:
    clave = os.environ.get("PIXABAY_API_KEY")
    if not clave:
        return []
    q = urllib.parse.urlencode({"key": clave, "q": consulta, "safesearch": "true", "per_page": 30, "order": "popular"})
    datos = http(f"https://pixabay.com/api/videos/?{q}", headers=UA)
    salida = []
    for v in datos.get("hits", []):
        archivos = v.get("videos", {})
        mejor = next((archivos[k] for k in ("large", "medium") if archivos.get(k, {}).get("url")), None)
        if not mejor or v.get("duration", 0) < 4:
            continue
        salida.append({
            "url": mejor["url"], "autor": v.get("user", ""), "fuente": "Pixabay", "id": f"pixabay-v{v['id']}",
            "etiquetas": v.get("tags", ""), "vertical": mejor.get("height", 0) > mejor.get("width", 1),
            "ancho": mejor.get("width", 0),
        })
    return salida


def pexels_videos(consulta: str) -> list[dict]:
    clave = os.environ.get("PEXELS_API_KEY")
    if not clave:
        return []
    q = urllib.parse.urlencode({"query": consulta, "orientation": "portrait", "per_page": 20})
    datos = http(f"https://api.pexels.com/videos/search?{q}", headers={"Authorization": clave} | UA)
    salida = []
    for v in datos.get("videos", []):
        archivos = [f for f in v.get("video_files", []) if f.get("width") and f.get("height") and f["height"] <= 2160]
        if not archivos or v.get("duration", 0) < 4:
            continue
        mejor = max(archivos, key=lambda f: f["height"])
        # Pexels no da etiquetas, pero la URL de la página describe el video ("foggy-forest-at-night-123")
        salida.append({
            "url": mejor["link"], "autor": v.get("user", {}).get("name", ""), "fuente": "Pexels",
            "id": f"pexels-v{v['id']}", "etiquetas": v.get("url", "").replace("-", " "),
            "vertical": mejor["height"] > mejor["width"], "ancho": mejor["width"],
        })
    return salida


def buscar_video(consulta: str, usadas: set[str]) -> dict | None:
    """Video de archivo que encaje con la escena: más exigente que con las fotos."""
    palabras = clave(consulta)
    if not palabras:
        return None
    minimo = len(palabras) if len(palabras) <= 2 else len(palabras) - 1
    candidatos = []
    for fuente in (pixabay_videos, pexels_videos):
        try:
            candidatos += [c for c in fuente(consulta) if c["id"] not in usadas]
        except Exception as e:
            print(f"{fuente.__name__} falló con '{consulta}': {e}")
    buenos = [c for c in candidatos if puntaje(c, consulta) >= minimo and c["ancho"] >= 1080]
    if not buenos:
        return None
    # Más coincidencias primero; a igualdad, mejor si ya es vertical (no pierde calidad al recortar)
    return max(buenos, key=lambda c: (puntaje(c, consulta), c["vertical"]))


SEGUNDOS_VIDEO = 14  # cada escena dura unos 8-10 s; en Remotion va algo más lento y en bucle si hace falta


def preparar_video(url: str, ruta) -> float:
    """Descarga el video, lo recorta a 1080x1920, lo oscurece igual que las fotos y le quita el sonido."""
    import subprocess
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".mp4") as tmp:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=180) as r:
            tmp.write(r.read())
        tmp.flush()
        filtro = (
            "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=24,"
            "eq=saturation=0.7:contrast=1.12,colorchannelmixer=rr=0.62:gg=0.62:bb=0.62"
        )
        subprocess.run(
            ["ffmpeg", "-v", "error", "-y", "-i", tmp.name, "-t", str(SEGUNDOS_VIDEO), "-an", "-vf", filtro,
             "-c:v", "libx264", "-preset", "veryfast", "-crf", "24", "-pix_fmt", "yuv420p", str(ruta)],
            check=True,
        )
    salida = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(ruta)],
        check=True, capture_output=True, text=True,
    ).stdout
    return float(salida.strip())


# Palabras que casi cualquier video tiene: no sirven para saber si encaja con la escena
GENERICAS = {
    "night", "old", "dark", "dim", "closed", "interior", "view", "light", "ancient", "vintage", "small", "big",
    "empty", "scene", "the", "with", "and", "for", "from", "inside", "outside", "close", "shot", "background",
    "black", "white", "gray", "grey", "time", "lapse", "evening", "day", "dramatic", "mysterious", "creepy",
}
# Nunca niños en los videos ni en las fotos
PROHIBIDAS = {"child", "children", "kid", "kids", "baby", "toddler", "boy", "girl", "childhood", "infant", "teen"}


def _fichas(etiquetas: str) -> set[str]:
    return {w for w in etiquetas.lower().replace(",", " ").replace("-", " ").split() if w}


def clave(consulta: str) -> list[str]:
    """Las palabras que importan de la búsqueda (el objeto o lugar, no el adjetivo ni la hora)."""
    return [p for p in consulta.lower().split() if len(p) > 2 and p not in GENERICAS]


def coincide(p: str, fichas: set[str]) -> bool:
    return p in fichas or p + "s" in fichas or p.rstrip("s") in fichas or p + "es" in fichas


def puntaje(candidata: dict, consulta: str) -> int:
    """Cuántas palabras importantes de la búsqueda aparecen como etiqueta (palabra entera)."""
    fichas = _fichas(candidata.get("etiquetas", ""))
    if fichas & PROHIBIDAS:
        return -1
    return sum(1 for p in clave(consulta) if coincide(p, fichas))


def buscar(consulta: str, usadas: set[str], respaldo: str = "") -> dict | None:
    """La foto cuyas etiquetas más coinciden con la búsqueda; si ninguna coincide, el escenario de la historia."""
    for q in [consulta] + ([respaldo] if respaldo and respaldo != consulta else []):
        for fuente in (pixabay, pexels):
            try:
                candidatas = [c for c in fuente(q) if c["id"] not in usadas]
            except Exception as e:
                print(f"{fuente.__name__} falló con '{q}': {e}")
                continue
            if not candidatas:
                continue
            mejor = max(candidatas, key=lambda c: puntaje(c, q))
            # Pixabay da etiquetas: exigir al menos la mitad de las palabras; Pexels no las da
            minimo = max(1, (len(clave(q)) + 1) // 2) if "etiquetas" in mejor else 0
            if puntaje(mejor, q) >= minimo:
                return mejor
    return None


def descargar(url: str, ruta) -> None:
    """Descarga la foto, la recorta a vertical 1080x1920 y la oscurece para el ambiente de misterio."""
    import io

    from PIL import Image, ImageEnhance

    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        foto = Image.open(io.BytesIO(r.read())).convert("RGB")
    # Recorte centrado a 9:16 un poco más grande que el video (deja margen al acercamiento lento)
    ancho, alto = 1188, 2112
    escala = max(ancho / foto.width, alto / foto.height)
    foto = foto.resize((round(foto.width * escala), round(foto.height * escala)), Image.LANCZOS)
    x, y = (foto.width - ancho) // 2, (foto.height - alto) // 2
    foto = foto.crop((x, y, x + ancho, y + alto))
    foto = ImageEnhance.Color(foto).enhance(0.7)
    foto = ImageEnhance.Contrast(foto).enhance(1.12)
    foto = ImageEnhance.Brightness(foto).enhance(0.62)
    foto.save(ruta, "JPEG", quality=88)


def portada(episodio: dict, usadas: set[str], carpeta) -> None:
    """Foto para la miniatura del video: la más impactante que pidió el guion (sin oscurecer tanto)."""
    consulta = (episodio.get("portada_imagen") or episodio.get("escenario") or "").strip().lower()
    elegida = buscar(consulta, usadas, episodio.get("escenario", "")) if consulta else None
    if not elegida:
        return
    archivo = carpeta / "portada.jpg"
    descargar(elegida["url"], archivo)
    episodio["portada_foto"] = f"imagenes/{archivo.name}"
    print(f"  portada: '{consulta}' -> {elegida['fuente']} ({elegida['autor']})")


def main() -> None:
    cargar_env()
    if not (os.environ.get("PEXELS_API_KEY") or os.environ.get("PIXABAY_API_KEY")):
        raise SystemExit("Falta PEXELS_API_KEY (gratis en https://www.pexels.com/api/)")
    episodio = json.loads(EPISODIO.read_text(encoding="utf-8"))
    carpeta = PUBLIC / "imagenes"
    carpeta.mkdir(exist_ok=True)
    for vieja in carpeta.glob("*.*"):
        vieja.unlink()

    usadas: set[str] = set()
    por_consulta: dict[str, tuple[str, dict]] = {}
    videos = 0
    for i, escena in enumerate(episodio["escenas"]):
        consulta = (escena.get("imagen") or escena.get("ambiente") or "dark night").strip().lower()
        # Escenas seguidas con la misma descripción comparten foto, para no marear
        if consulta in por_consulta:
            tipo, medio = por_consulta[consulta]
            escena[tipo] = medio
            continue
        # 1. Video de archivo que encaje (hasta MAX_VIDEOS por historia para no alargar el render)
        if videos < MAX_VIDEOS:
            video = buscar_video(consulta, usadas)
            if video:
                archivo = carpeta / f"{i:02d}.mp4"
                try:
                    segundos = preparar_video(video["url"], archivo)
                except Exception as e:
                    print(f"  {i:02d}: no se pudo preparar el video ({e}), se busca foto")
                else:
                    usadas.add(video["id"])
                    videos += 1
                    medio = {"archivo": f"imagenes/{archivo.name}", "autor": video["autor"], "fuente": video["fuente"],
                             "segundos": round(segundos, 2)}
                    por_consulta[consulta] = ("video", medio)
                    escena["video"] = medio
                    print(f"  {i:02d}: '{consulta}' -> VIDEO {video['fuente']} ({video['etiquetas'][:60]})")
                    continue
        # 2. Foto
        elegida = buscar(consulta, usadas, episodio.get("escenario", ""))
        if not elegida:
            print(f"  {i:02d}: sin foto para '{consulta}', se usa la anterior")
            anterior = episodio["escenas"][i - 1] if i > 0 else {}
            for tipo in ("video", "foto"):
                if anterior.get(tipo):
                    escena[tipo] = anterior[tipo]
            continue
        archivo = carpeta / f"{i:02d}.jpg"
        descargar(elegida["url"], archivo)
        usadas.add(elegida["id"])
        foto = {"archivo": f"imagenes/{archivo.name}", "autor": elegida["autor"], "fuente": elegida["fuente"]}
        por_consulta[consulta] = ("foto", foto)
        escena["foto"] = foto
        print(f"  {i:02d}: '{consulta}' -> {elegida['fuente']} ({elegida['autor']})")

    portada(episodio, usadas, carpeta)
    sin_foto = sum(1 for e in episodio["escenas"] if not e.get("foto") and not e.get("video"))
    if sin_foto == len(episodio["escenas"]):
        raise SystemExit("No se encontró ninguna foto: revisa PEXELS_API_KEY")
    EPISODIO.write_text(json.dumps(episodio, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{len(usadas)} medios distintos ({videos} videos), {sin_foto} escenas sin imagen")


if __name__ == "__main__":
    main()
