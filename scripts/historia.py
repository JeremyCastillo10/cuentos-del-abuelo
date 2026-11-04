"""Escribe la historia del día con Gemini (o Groq si Gemini no responde)."""

import json
import os
import urllib.error
from datetime import date

from comun import EPISODIO, RAIZ, cargar_env, env, gemini, http, ordenar_hashtags

MODELOS_TEXTO = ["gemini-3.5-flash", "gemini-flash-latest", "gemini-3.8-flash", "gemini-3.7-flash"]
MODELOS_GROQ = ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "llama-3.3-70b-versatile", "llama-3.1-8b-instant"]
PUBLICADAS = RAIZ / "data" / "historias_publicadas.json"
AMBIENTES = ["bosque", "casa", "carretera", "mar", "pueblo", "cementerio", "habitacion", "ciudad"]

# Se rota por día para que la página tenga variedad
TIPOS = [
    (
        "ficcion",
        "Historia de terror o suspenso ORIGINAL, inventada por ti desde cero. No copies ni adaptes "
        "cuentos, películas, series ni creepypastas conocidas. Personajes con nombres inventados.",
    ),
    (
        "leyenda",
        "Leyenda tradicional latinoamericana o caribeña (por ejemplo dominicanas como la Ciguapa, "
        "el Bacá o el Galipote, o de otros países) contada con tus propias palabras. "
        "Deja claro que es una leyenda popular, no un hecho comprobado.",
    ),
    (
        "misterio",
        "Misterio o suceso inexplicado REAL y muy documentado (de conocimiento público, con al menos "
        "décadas de antigüedad). Usa solo hechos ampliamente conocidos; no inventes datos, nombres ni "
        "fechas. Nada sobre crímenes de personas privadas ni víctimas recientes.",
    ),
    (
        "crimen",
        "Caso criminal REAL, famoso y muy documentado, de hace al menos 20 años y ya resuelto por la justicia "
        "(con culpable juzgado). Cuenta cómo se investigó y cómo se descubrió la verdad. Usa SOLO hechos "
        "ampliamente publicados: no inventes nombres, fechas, cifras ni diálogos. Sin detalles gráficos de la "
        "violencia, con respeto hacia las víctimas; no nombres a familiares ni a testigos menores de edad.",
    ),
]

INSTRUCCIONES = """Eres el narrador de "Cuentos del Abuelo", una página de historias narradas en video vertical
(Reels de Instagram y Facebook) para público latino. Narras como un locutor profesional de historias de misterio:
voz grave, ritmo pausado, frases que crean atmósfera. De vez en cuando puedes abrir con algo como
"Esto me lo contó mi abuelo..." o "En mi pueblo todavía lo cuentan...", sin abusar. Escribe UNA historia.

Reglas:
1. {tipo}
2. Dura entre 5 y 8 minutos narrada: entre {min_palabras} y {max_palabras} palabras en total. Usa ese
   espacio para desarrollar bien la historia: contexto, personajes, pistas, tensión que crece y desenlace.
3. Divide el texto en escenas: cada escena es una o dos frases (máx 30 palabras), fáciles de narrar.
4. La PRIMERA escena es el gancho: una frase que obligue a seguir viendo (nada de saludos ni
   "hoy les traigo"). Ej.: "En mi pueblo nadie abría la puerta después de las doce. Esa noche, alguien tocó."
5. Construye tensión y termina con un giro o un final abierto que deje pensando.
6. Nada de violencia gráfica, gore, suicidio ni contenido sexual. Apto para mayores de 13 años.
7. Cada escena lleva "ambiente": uno de {ambientes} (el lugar donde ocurre esa parte).
   Y lleva "imagen": búsqueda EN INGLÉS de 3 a 6 palabras para encontrar una FOTO REAL de banco de imágenes
   que muestre lo que se narra (lugar, objeto, clima, hora), por ejemplo "abandoned wooden house night fog",
   "old rural road dark trees", "candle on table dark room". Sin nombres propios ni personas reales
   identificables: en casos reales describe el lugar o un objeto, nunca a la víctima ni al culpable.
   Escenas seguidas que pasan en el mismo sitio pueden repetir la misma búsqueda.
8. "titulo": corto y llamativo (máx 40 caracteres), sin comillas.
9. "caption" para Instagram y Facebook:
   - Primera línea: el gancho resumido (máx 110 caracteres).
   - Segunda línea: "{etiqueta}".
   - Tercera línea: una pregunta para que la gente comente.
   - Al final 4 hashtags en español, sin tildes, según el tipo (ej. #terror #leyendas #misterio
     #casosreales #truecrime #historiasdeterror).
10. No repitas estas historias ya publicadas: {publicadas}

Responde SOLO con JSON:
{{"titulo": "...", "escenas": [{{"texto": "...", "ambiente": "...", "imagen": "..."}}], "caption": "..."}}"""

ETIQUETAS = {
    "ficcion": "📖 Historia de ficción original.",
    "leyenda": "🌙 Leyenda popular: cuenta lo que dice la tradición, no un hecho comprobado.",
    "misterio": "🔎 Caso real sin resolver, contado con lo que se sabe.",
    "crimen": "⚖️ Caso real, basado en información pública del caso.",
}


def groq_texto(sistema: str, usuario: str) -> str:
    """Respaldo con Groq: prueba varios modelos y devuelve el JSON como texto."""
    errores = []
    for modelo in env("GROQ_MODELOS", ",".join(MODELOS_GROQ)).split(","):
        for modo_json in (True, False):
            cuerpo = {
                "model": modelo,
                "messages": [{"role": "system", "content": sistema}, {"role": "user", "content": usuario}],
                "temperature": 1.0,
            }
            if modo_json:
                cuerpo["response_format"] = {"type": "json_object"}
            try:
                r = http(
                    "https://api.groq.com/openai/v1/chat/completions",
                    cuerpo,
                    {"Authorization": f"Bearer {env('GROQ_API_KEY')}"},
                )
                texto = r["choices"][0]["message"]["content"]
                inicio, fin = texto.find("{"), texto.rfind("}")
                json.loads(texto[inicio : fin + 1])
                print(f"Historia escrita con Groq ({modelo})")
                return texto[inicio : fin + 1]
            except urllib.error.HTTPError as e:
                detalle = e.read().decode(errors="ignore")[:300]
                errores.append(f"{modelo} {e.code}: {detalle}")
                print(f"Groq {modelo} respondió {e.code}: {detalle}")
                if e.code != 400:
                    break
            except (ValueError, KeyError) as e:
                errores.append(f"{modelo}: respuesta no válida ({e})")
    raise RuntimeError("Ningún modelo de Groq respondió: " + " | ".join(errores))


def escribir(sistema: str, usuario: str) -> str:
    """JSON de la historia como texto: Gemini y, si no responde, Groq."""
    cuerpo = {
        "systemInstruction": {"parts": [{"text": sistema}]},
        "contents": [{"parts": [{"text": usuario}]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 1.0, "maxOutputTokens": 16000},
    }
    for modelo in env("GEMINI_MODELOS_TEXTO", ",".join(MODELOS_TEXTO)).split(","):
        try:
            print("Escribiendo historia con", modelo)
            r = gemini(modelo, cuerpo, reintentos=2)
            return r["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            print(f"{modelo} no disponible ({e})")
    if os.environ.get("GROQ_API_KEY"):
        print("Gemini no respondió; escribiendo la historia con Groq")
        return groq_texto(sistema, usuario)
    raise SystemExit("Ningún modelo de texto respondió (Gemini ni Groq)")


def cargar_publicadas() -> list[str]:
    return json.loads(PUBLICADAS.read_text(encoding="utf-8")) if PUBLICADAS.exists() else []


def validar(historia: dict) -> dict:
    escenas = [
        {
            "texto": e["texto"].strip(),
            "ambiente": e.get("ambiente") if e.get("ambiente") in AMBIENTES else "casa",
            "imagen": (e.get("imagen") or "").strip(),
        }
        for e in historia["escenas"]
        if e.get("texto", "").strip()
    ]
    if len(escenas) < 6:
        raise ValueError(f"La historia tiene solo {len(escenas)} escenas")
    return {"titulo": historia["titulo"].strip(), "escenas": escenas, "caption": historia.get("caption", "")}


def main() -> None:
    cargar_env()
    hoy = date.today()
    clave, descripcion = TIPOS[hoy.toordinal() % len(TIPOS)]
    publicadas = cargar_publicadas()
    sistema = INSTRUCCIONES.format(
        tipo=descripcion,
        ambientes=", ".join(AMBIENTES),
        etiqueta=ETIQUETAS[clave],
        publicadas="; ".join(publicadas[-60:]) or "(ninguna)",
        # Narrando a unas 145 palabras por minuto: 5 min ≈ 730 palabras, 8 min ≈ 1150
        min_palabras=env("MIN_PALABRAS", "730"),
        max_palabras=env("MAX_PALABRAS", "1150"),
    )
    usuario = f"Fecha: {hoy.isoformat()}. Escribe la historia de hoy (tipo: {clave})."

    minimo = int(env("MIN_PALABRAS", "730"))
    mejor, palabras = None, 0
    pedido = usuario
    for intento in range(3):
        historia = validar(json.loads(escribir(sistema, pedido)))
        n = sum(len(e["texto"].split()) for e in historia["escenas"])
        print(f"Intento {intento + 1}: {n} palabras")
        if n > palabras:
            mejor, palabras = historia, n
        if n >= minimo * 0.92:
            break
        # Se quedó corta: se pide de nuevo, más larga y desarrollada
        pedido = (
            f"{usuario}\nLa versión anterior tenía solo {n} palabras y debe tener al menos {minimo}. "
            "Escríbela completa otra vez, más desarrollada: más contexto, más detalles del lugar y de los "
            "personajes, más momentos de tensión antes del desenlace."
        )
    historia = mejor
    episodio = {
        "fecha": hoy.isoformat(),
        "tipo": clave,
        "titulo": historia["titulo"],
        "escenas": historia["escenas"],
        "caption": ordenar_hashtags(historia["caption"]),
    }
    EPISODIO.write_text(json.dumps(episodio, ensure_ascii=False, indent=2), encoding="utf-8")
    palabras = sum(len(e["texto"].split()) for e in episodio["escenas"])
    print(f"{episodio['titulo']} ({clave}, {len(episodio['escenas'])} escenas, {palabras} palabras)")
    for e in episodio["escenas"]:
        print(f"  [{e['ambiente']}] {e['texto']}")


if __name__ == "__main__":
    main()
