"""Busca en Wikipedia en español un artículo real (caso, misterio o leyenda) para contar.

La historia se narra solo con los hechos de ese artículo, y se cita en el post.
"""

import random
import urllib.parse

from comun import http

API = "https://es.wikipedia.org/w/api.php"
UA = {"User-Agent": "cuentos-del-abuelo/1.0 (historias narradas; contacto via GitHub)"}

# Búsquedas por tipo; cada día se prueba una al azar hasta encontrar un artículo largo y nuevo
BUSQUEDAS = {
    "crimen": [
        "asesinato caso famoso investigación condenado",
        "crimen célebre juicio culpable siglo XX",
        "asesino en serie condenado investigación policial",
        "caso criminal resuelto décadas después",
        "secuestro famoso caso resuelto juicio",
        "envenenamiento caso histórico juicio",
        "crimen América Latina caso famoso condena",
    ],
    "misterio": [
        "desaparición misteriosa sin resolver",
        "misterio sin resolver caso famoso",
        "barco fantasma tripulación desaparecida",
        "suceso inexplicable investigación sin resolver",
        "avión desaparecido misterio búsqueda",
        "muerte misteriosa caso sin resolver",
    ],
    "leyenda": [
        "leyenda dominicana",
        "leyenda urbana latinoamericana",
        "mito folclore caribeño",
        "leyenda colonial fantasma",
        "folclore mexicano leyenda aparición",
        "leyenda de terror tradición oral",
        "criatura folclore latinoamericano",
    ],
}

MIN_CARACTERES = 6000  # artículos cortos no dan para 5 minutos sin inventar


def _buscar_titulos(consulta: str) -> list[dict]:
    q = urllib.parse.urlencode(
        {"action": "query", "list": "search", "srsearch": consulta, "srlimit": 50, "srnamespace": 0, "format": "json"}
    )
    return http(f"{API}?{q}", headers=UA).get("query", {}).get("search", [])


def _texto(titulo: str) -> str:
    q = urllib.parse.urlencode(
        {"action": "query", "prop": "extracts", "explaintext": 1, "titles": titulo, "redirects": 1, "format": "json"}
    )
    paginas = http(f"{API}?{q}", headers=UA).get("query", {}).get("pages", {})
    return next(iter(paginas.values()), {}).get("extract", "")


def elegir_articulo(tipo: str, usados: set[str], descartados: set[str]) -> dict:
    consultas = BUSQUEDAS[tipo][:]
    random.shuffle(consultas)
    for consulta in consultas:
        try:
            resultados = _buscar_titulos(consulta)
        except Exception as e:
            print(f"Wikipedia falló con '{consulta}': {e}")
            continue
        candidatos = [
            r for r in resultados
            if r.get("size", 0) > MIN_CARACTERES * 1.5 and r["title"] not in usados and r["title"] not in descartados
            and not r["title"].startswith(("Anexo:", "Lista de"))
        ]
        random.shuffle(candidatos)
        for r in candidatos[:6]:
            texto = _texto(r["title"])
            if len(texto) >= MIN_CARACTERES:
                return {
                    "titulo": r["title"],
                    "texto": texto[:30000],
                    "url": "https://es.wikipedia.org/wiki/" + urllib.parse.quote(r["title"].replace(" ", "_")),
                }
    raise SystemExit(f"No se encontró en Wikipedia un artículo nuevo y largo para el tipo '{tipo}'")
