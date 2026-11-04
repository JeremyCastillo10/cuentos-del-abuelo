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

# Casos, misterios y leyendas reales muy conocidos (títulos de Wikipedia en español; las
# redirecciones también valen). Se prueban primero, sin repetir; la búsqueda es el último recurso.
SEMILLAS = {
    "crimen": [
        "Jack el Destripador", "H. H. Holmes", "Ed Gein", "Ted Bundy", "Asesino del Zodiaco",
        "Elizabeth Short", "Albert Fish", "Gregorio Cárdenas", "Las Poquianchis", "Lizzie Borden",
        "Bonnie y Clyde", "Al Capone", "Charles Manson", "Jeffrey Dahmer", "John Wayne Gacy",
        "Richard Ramírez", "Aileen Wuornos", "Harold Shipman", "Peter Sutcliffe", "Henri Désiré Landru",
        "Marcel Petiot", "Enriqueta Martí", "Manuel Blanco Romasanta", "Gilles de Rais", "Isabel Báthory",
        "Asesinatos de la granja de Hinterkaifeck", "Juana Barraza", "Robo del tren de Glasgow-Londres",
        "Robo de la Mona Lisa", "D. B. Cooper", "Asesinato de Lindbergh", "Caso Dominici",
        "Andrés Ortega", "Pedro Alonso López", "Daniel Camargo Barbosa", "Juan Vallejo Corona",
    ],
    "misterio": [
        "Mary Celeste", "Incidente del paso Diatlov", "Colonia de Roanoke", "Triángulo de las Bermudas",
        "Vuelo 19", "Amelia Earhart", "Desaparición de Jimmy Hoffa", "Hombre de Somerton",
        "Manuscrito Voynich", "Mujer de Isdal", "Señal Wow!", "Caso Roswell", "Luces de Marfa",
        "Ourang Medan", "Barco fantasma", "Caso de las caras de Bélmez", "Vuelo 370 de Malaysia Airlines",
        "Desaparición del faro de las islas Flannan", "Perro de Bodmin", "Mapa de Piri Reis",
        "Kaspar Hauser", "Hombre de la máscara de hierro", "Niños verdes de Woolpit", "Muerte de Edgar Allan Poe",
        "Caso Elisa Lam", "Pirámides de Güímar", "Tunguska",
    ],
    "leyenda": [
        "Ciguapa", "Bacá", "Galipote", "La Llorona", "El Silbón", "La Sayona", "Chupacabras",
        "El Cadejo", "La Tunda", "La Patasola", "Mula sin cabeza", "El Coco", "La Santa Compaña",
        "Callejón del Beso", "La Pascualita", "Leyenda de la Mano Peluda", "El Sombrerón", "La Siguanaba",
        "Lobisón", "El Familiar", "Pombero", "Cuco (folclore)", "Bruja", "Duende",
        "Muñecas de la isla de las Muñecas", "El Charro Negro", "La Ciudad Blanca", "El Dorado",
    ],
}

MIN_CARACTERES = 6000  # artículos cortos no dan para 5 minutos sin inventar
# Lo que se le pasa al modelo: da para 8 minutos y cabe en el límite por minuto de Groq
LIMITE_TEXTO = 14000


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


def _articulo(titulo: str) -> dict | None:
    texto = _texto(titulo)
    if len(texto) < MIN_CARACTERES:
        return None
    return {
        "titulo": titulo,
        "texto": texto[:LIMITE_TEXTO],
        "url": "https://es.wikipedia.org/wiki/" + urllib.parse.quote(titulo.replace(" ", "_")),
    }


def elegir_articulo(tipo: str, usados: set[str], descartados: set[str]) -> dict:
    # 1. Lista de historias reales conocidas
    semillas = [t for t in SEMILLAS[tipo] if t not in usados and t not in descartados]
    random.shuffle(semillas)
    for titulo in semillas[:8]:
        try:
            articulo = _articulo(titulo)
        except Exception as e:
            print(f"Wikipedia falló con '{titulo}': {e}")
            continue
        if articulo:
            return articulo
        descartados.add(titulo)  # no existe o es muy corto
    # 2. Búsqueda general (último recurso)
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
                    "texto": texto[:LIMITE_TEXTO],
                    "url": "https://es.wikipedia.org/wiki/" + urllib.parse.quote(r["title"].replace(" ", "_")),
                }
    raise SystemExit(f"No se encontró en Wikipedia un artículo nuevo y largo para el tipo '{tipo}'")
