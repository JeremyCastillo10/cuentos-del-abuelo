"""Elige un caso real (misterio, crimen, aparición o leyenda) y reúne sus hechos de varias fuentes.

1. Gemini con búsqueda de Google investiga el caso en la web (prensa, sitios especializados,
   archivos) y devuelve un dossier con los hechos y las fuentes consultadas.
2. Si eso no funciona (sin cupo, pocas fuentes), se usa Wikipedia en español o en inglés.
La historia se narra solo con esos hechos y las fuentes se citan en el post.
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
    "paranormal": [
        "poltergeist caso famoso investigación",
        "casa encantada historia fantasmas testigos",
        "aparición fantasma caso famoso",
        "fenómeno paranormal caso investigado",
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

# Casos, misterios y leyendas reales muy conocidos. En "crimen" NO van casos con víctimas menores de edad
# (va contra las normas de la página y Facebook los castiga). (títulos de Wikipedia en español; las
# redirecciones también valen). Se prueban primero, sin repetir; la búsqueda es el último recurso.
SEMILLAS = {
    "crimen": [
        "Jack el Destripador", "Ed Gein",
        "Elizabeth Short", "Lizzie Borden",
        "Bonnie y Clyde", "Al Capone", "Charles Manson",
        "Aileen Wuornos", "Harold Shipman", "Henri Désiré Landru",
                "Juana Barraza", "Robo del tren de Glasgow-Londres",
        "Robo de la Mona Lisa", "D. B. Cooper", "Asesinato de Rasputín",
        "Robo del Banco Central de Fortaleza", "Masacre del día de San Valentín", "Asesinato de Julio César",
        "Juan Vallejo Corona",
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
    "paranormal": [
        "Poltergeist de Enfield", "Casa Winchester", "Caras de Bélmez", "Dama Marrón de Raynham Hall",
        "Bruja de Bell", "Annabelle (muñeca)", "Robert (muñeco)", "Isla de las Muñecas", "Palacio de Linares",
        "Caso Amityville", "Hotel Cecil", "Castillo de Chillingham", "Torre de Londres", "Hospital Waverly Hills",
        "Casa de los Espíritus", "Castillo de Edimburgo", "Mansión Myrtles", "Penitenciaría Estatal del Este",
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


INVESTIGAR = """Investiga a fondo en internet este caso real: «{tema}» ({tipo}).
Busca en VARIAS fuentes fiables y distintas (prensa, revistas, sitios de historia, archivos, libros,
documentales), no solo en Wikipedia. Escribe en español un dossier de hechos de 1500 a 2500 palabras con:
- Contexto: época, lugar, personas implicadas (sin nombrar a menores ni a familiares de víctimas).
- La cronología detallada de lo que pasó, con fechas, cifras y lugares exactos.
- Los detalles más extraños, inquietantes o sorprendentes que recogen las fuentes.
- La investigación, las pistas, las teorías y qué está comprobado y qué no.
- Cómo terminó o en qué quedó, y qué sigue sin respuesta hoy.
Solo hechos que digan las fuentes; si las fuentes no coinciden, dilo. Nada inventado.
Si el caso no es real o casi no hay información fiable, responde solo: NO_HAY_DATOS"""

MODELOS_INVESTIGAR = ["gemini-3.5-flash", "gemini-flash-latest"]


def investigar(tema: str, tipo: str) -> dict | None:
    """Dossier del caso con fuentes de la web (Gemini + búsqueda de Google). None si no se pudo."""
    import os

    from comun import gemini

    if not os.environ.get("GEMINI_API_KEY"):
        return None
    cuerpo = {
        "contents": [{"parts": [{"text": INVESTIGAR.format(tema=tema, tipo=tipo)}]}],
        "tools": [{"google_search": {}}],
        "generationConfig": {"temperature": 0.3, "maxOutputTokens": 8000},
    }
    for modelo in MODELOS_INVESTIGAR:
        try:
            r = gemini(modelo, cuerpo, reintentos=2)
        except Exception as e:
            print(f"Investigación con {modelo} no disponible ({e})")
            continue
        candidato = r["candidates"][0]
        texto = "".join(p.get("text", "") for p in candidato.get("content", {}).get("parts", []))
        trozos = candidato.get("groundingMetadata", {}).get("groundingChunks", [])
        fuentes = []
        for t in trozos:
            web = t.get("web", {})
            nombre = (web.get("title") or "").strip()
            if nombre and nombre.lower() not in (f.lower() for f in fuentes):
                fuentes.append(nombre)
        if "NO_HAY_DATOS" in texto[:50] or len(texto) < 4500:
            print(f"  Investigación de '{tema}' corta ({len(texto)} caracteres): no sirve")
            return None
        if len(fuentes) < 3:
            print(f"  Investigación de '{tema}' con solo {len(fuentes)} fuentes: no sirve")
            return None
        print(f"  Investigado en {len(fuentes)} fuentes: {', '.join(fuentes[:8])}")
        return {"titulo": tema, "texto": texto[:LIMITE_TEXTO], "url": "", "fuentes": fuentes[:8]}
    return None


# ---------- Búsqueda web directa (sin cupo de IA) ----------
EXCLUIR = ("wikipedia.", "wikiwand.", "youtube.", "facebook.", "instagram.", "tiktok.", "pinterest.", "twitter.",
           "x.com", "amazon.", "reddit.", "quora.", "spotify.", "apple.com", "duckduckgo.", "bing.", "microsoft.")
NAVEGADOR = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36",
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
}


def _html(url: str) -> str:
    import urllib.request

    req = urllib.request.Request(url, headers=NAVEGADOR)
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read().decode("utf-8", errors="ignore")


def _resultados(consulta: str) -> list[str]:
    """Enlaces de resultados de búsqueda (DuckDuckGo y, si falla, Bing)."""
    import html as htmllib
    import re

    enlaces: list[str] = []
    try:
        pagina = _html("https://html.duckduckgo.com/html/?" + urllib.parse.urlencode({"q": consulta, "kl": "es-es"}))
        for href in re.findall(r'class="result__a"[^>]*href="([^"]+)"', pagina):
            href = htmllib.unescape(href)
            if "uddg=" in href:
                href = urllib.parse.unquote(urllib.parse.parse_qs(urllib.parse.urlparse(href).query).get("uddg", [""])[0])
            enlaces.append(href)
    except Exception as e:
        print(f"  DuckDuckGo falló: {e}")
    if len(enlaces) < 3:
        try:
            pagina = _html("https://www.bing.com/search?" + urllib.parse.urlencode({"q": consulta, "setlang": "es"}))
            enlaces += [htmllib.unescape(h) for h in re.findall(r'<li class="b_algo".*?<a[^>]+href="(https?://[^"]+)"', pagina, re.S)]
        except Exception as e:
            print(f"  Bing falló: {e}")
    vistos, limpios = set(), []
    for e in enlaces:
        dominio = urllib.parse.urlparse(e).netloc.lower().removeprefix("www.")
        if e.startswith("http") and dominio and dominio not in vistos and not any(x in dominio for x in EXCLUIR):
            vistos.add(dominio)
            limpios.append(e)
    return limpios


def buscar_web(tema: str, tipo: str) -> dict | None:
    """Lee varias páginas sobre el caso (prensa, sitios de historia y misterio) y junta sus textos."""
    try:
        import trafilatura
    except ImportError:
        print("  Falta trafilatura: sin búsqueda web directa")
        return None
    consultas = [f"{tema} caso historia real", f"{tema} history case"]
    textos, fuentes = [], []
    for consulta in consultas:
        for url in _resultados(consulta)[:8]:
            if len(fuentes) >= 4:
                break
            dominio = urllib.parse.urlparse(url).netloc.lower().removeprefix("www.")
            if dominio in fuentes:
                continue
            try:
                texto = trafilatura.extract(_html(url), include_comments=False, include_tables=False) or ""
            except Exception as e:
                print(f"  No se pudo leer {dominio}: {e}")
                continue
            # Solo páginas que de verdad hablan del caso
            palabra = max(tema.split(), key=len).lower()
            if len(texto) < 1500 or palabra not in texto.lower():
                continue
            textos.append(f"FUENTE: {dominio}\n{texto[:4500]}")
            fuentes.append(dominio)
        if len(fuentes) >= 3:
            break
    if len(fuentes) < 2 or sum(len(t) for t in textos) < 4500:
        print(f"  Web: pocas fuentes útiles para '{tema}' ({fuentes})")
        return None
    print(f"  Web: {len(fuentes)} fuentes: {', '.join(fuentes)}")
    return {"titulo": tema, "texto": "\n\n".join(textos)[:LIMITE_TEXTO], "url": "", "fuentes": fuentes}


def elegir_caso(tipo: str, usados: set[str], descartados: set[str]) -> dict:
    """Un caso conocido investigado en varias fuentes de la web; si no se puede, un artículo de Wikipedia."""
    semillas = [t for t in SEMILLAS[tipo] if t not in usados and t not in descartados]
    random.shuffle(semillas)
    for tema in semillas[:3]:
        print(f"Investigando en la web: {tema}")
        caso = buscar_web(tema, tipo) or investigar(tema, tipo)
        if caso:
            return caso
        descartados.add(tema)
    print("Sin investigación web; se usa Wikipedia")
    return elegir_articulo(tipo, usados, descartados)


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
