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

INSTRUCCIONES = """Eres "el abuelo" de "Cuentos del Abuelo", una página de historias narradas en video vertical
(Reels de Instagram y Facebook) para público latino. El abuelo es un señor dominicano de campo, de voz
grave y pausada, que ha visto y oído de todo y cuenta las historias de noche, en la galería, como se
cuentan cuando se va la luz. Escribe con su voz: cercana, a veces le habla al que escucha ("mira, mijo...",
"y fíjate que...", "eso fue verdad, ¿eh?"), sin exagerar los modismos. Escribe UNA historia.

Reglas:
1. {tipo}
2. Dura entre 60 y 80 segundos narrada: entre 170 y 210 palabras en total.
3. 12 a 16 escenas. Cada escena es una o dos frases cortas (máx 22 palabras), fáciles de narrar.
4. La PRIMERA escena es el gancho: una frase que obligue a seguir viendo (nada de saludos ni
   "hoy les traigo"). Ej.: "En mi pueblo nadie abría la puerta después de las doce. Esa noche, alguien tocó."
5. Construye tensión y termina con un giro o un final abierto que deje pensando.
6. Nada de violencia gráfica, gore, suicidio ni contenido sexual. Apto para mayores de 13 años.
7. Cada escena lleva "ambiente": uno de {ambientes} (el lugar donde ocurre esa parte).
8. "titulo": corto y llamativo (máx 40 caracteres), sin comillas.
9. "caption" para Instagram y Facebook:
   - Primera línea: el gancho resumido (máx 110 caracteres).
   - Segunda línea: "{etiqueta}".
   - Tercera línea: una pregunta para que la gente comente.
   - Al final 4 hashtags en español, sin tildes, según el tipo (ej. #terror #leyendas #misterio
     #casosreales #truecrime #historiasdeterror).
10. No repitas estas historias ya publicadas: {publicadas}

Responde SOLO con JSON:
{{"titulo": "...", "escenas": [{{"texto": "...", "ambiente": "..."}}], "caption": "..."}}"""

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


def cargar_publicadas() -> list[str]:
    return json.loads(PUBLICADAS.read_text(encoding="utf-8")) if PUBLICADAS.exists() else []


def validar(historia: dict) -> dict:
    escenas = [
        {"texto": e["texto"].strip(), "ambiente": e.get("ambiente") if e.get("ambiente") in AMBIENTES else "casa"}
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
    )
    usuario = f"Fecha: {hoy.isoformat()}. Escribe la historia de hoy (tipo: {clave})."

    texto = None
    cuerpo = {
        "systemInstruction": {"parts": [{"text": sistema}]},
        "contents": [{"parts": [{"text": usuario}]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 1.0},
    }
    for modelo in env("GEMINI_MODELOS_TEXTO", ",".join(MODELOS_TEXTO)).split(","):
        try:
            print("Escribiendo historia con", modelo)
            r = gemini(modelo, cuerpo, reintentos=2)
            texto = r["candidates"][0]["content"]["parts"][0]["text"]
            break
        except Exception as e:
            print(f"{modelo} no disponible ({e})")
    if texto is None and os.environ.get("GROQ_API_KEY"):
        print("Gemini no respondió; escribiendo la historia con Groq")
        texto = groq_texto(sistema, usuario)
    if texto is None:
        raise SystemExit("Ningún modelo de texto respondió (Gemini ni Groq)")

    historia = validar(json.loads(texto))
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
