"""Busca una foto real para cada escena en Pexels (y Pixabay de respaldo).

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


def pexels(consulta: str) -> list[dict]:
    clave = os.environ.get("PEXELS_API_KEY")
    if not clave:
        return []
    q = urllib.parse.urlencode({"query": consulta, "orientation": "portrait", "size": "large", "per_page": 20})
    datos = http(f"https://api.pexels.com/v1/search?{q}", headers={"Authorization": clave} | UA)
    return [
        {"url": f["src"]["large2x"], "autor": f["photographer"], "fuente": "Pexels", "id": f"pexels-{f['id']}"}
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


def puntaje(candidata: dict, consulta: str) -> int:
    """Cuántas palabras de la búsqueda aparecen en las etiquetas de la foto."""
    etiquetas = candidata.get("etiquetas", "").lower()
    return sum(1 for p in consulta.lower().split() if len(p) > 2 and p in etiquetas)


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
            minimo = max(1, len([p for p in q.split() if len(p) > 2]) // 2) if "etiquetas" in mejor else 0
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
    por_consulta: dict[str, dict] = {}
    for i, escena in enumerate(episodio["escenas"]):
        consulta = (escena.get("imagen") or escena.get("ambiente") or "dark night").strip().lower()
        # Escenas seguidas con la misma descripción comparten foto, para no marear
        if consulta in por_consulta:
            escena["foto"] = por_consulta[consulta]
            continue
        elegida = buscar(consulta, usadas, episodio.get("escenario", ""))
        if not elegida:
            print(f"  {i:02d}: sin foto para '{consulta}', se usa la anterior")
            if i > 0 and episodio["escenas"][i - 1].get("foto"):
                escena["foto"] = episodio["escenas"][i - 1]["foto"]
            continue
        archivo = carpeta / f"{i:02d}.jpg"
        descargar(elegida["url"], archivo)
        usadas.add(elegida["id"])
        foto = {"archivo": f"imagenes/{archivo.name}", "autor": elegida["autor"], "fuente": elegida["fuente"]}
        por_consulta[consulta] = foto
        escena["foto"] = foto
        print(f"  {i:02d}: '{consulta}' -> {elegida['fuente']} ({elegida['autor']})")

    sin_foto = sum(1 for e in episodio["escenas"] if not e.get("foto"))
    if sin_foto == len(episodio["escenas"]):
        raise SystemExit("No se encontró ninguna foto: revisa PEXELS_API_KEY")
    EPISODIO.write_text(json.dumps(episodio, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{len(usadas)} fotos distintas, {sin_foto} escenas sin foto propia")


if __name__ == "__main__":
    main()
