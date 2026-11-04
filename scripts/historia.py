"""Elige un artículo real de Wikipedia y lo narra con Gemini (o Groq si Gemini no responde)."""

import json
import os
import time
import urllib.error
from datetime import date

from comun import EPISODIO, RAIZ, cargar_env, env, gemini, http, ordenar_hashtags
from fuentes import elegir_articulo

MODELOS_TEXTO = ["gemini-3.5-flash", "gemini-flash-latest", "gemini-3.8-flash", "gemini-3.7-flash"]
MODELOS_GROQ = ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "llama-3.3-70b-versatile", "llama-3.1-8b-instant"]
PUBLICADAS = RAIZ / "data" / "historias_publicadas.json"
AMBIENTES = ["bosque", "casa", "carretera", "mar", "pueblo", "cementerio", "habitacion", "ciudad"]

# Se rota por día para que la página tenga variedad. Todas son historias REALES sacadas de Wikipedia.
TIPOS = [
    (
        "misterio",
        "Es un misterio o caso REAL SIN RESOLVER. Cuenta lo que se sabe, las pistas y las teorías que "
        "recoge el texto, dejando claro qué está comprobado y qué no. Termina con la pregunta que nadie ha respondido.",
    ),
    (
        "crimen",
        "Es un caso criminal REAL (asesinato o crimen famoso, resuelto o sin resolver). Cuenta cómo pasó, cómo se "
        "investigó y qué se descubrió. Sin detalles gráficos de la violencia y con respeto hacia las víctimas; "
        "no nombres a familiares ni a menores de edad.",
    ),
    (
        "paranormal",
        "Es un caso REAL de apariciones o fenómenos paranormales que la gente reportó (casa embrujada, "
        "poltergeist, fantasma famoso). Cuenta lo que dijeron los testigos y lo que se investigó, dejando claro "
        "que no está comprobado y qué explicaciones se han dado.",
    ),
]
# Orden de la semana: más casos sin resolver, asesinatos y apariciones; una leyenda de vez en cuando
ROTACION = ["misterio", "crimen", "paranormal", "misterio", "crimen", "paranormal", "leyenda"]
TIPOS.append(
    (
        "leyenda",
        "Es una leyenda tradicional REAL (existe y la gente la cuenta). Cuéntala como lo recoge el texto "
        "y deja claro que es una leyenda popular, no un hecho comprobado.",
    )
)

INSTRUCCIONES = """Eres el narrador de "Cuentos del Abuelo", una página de historias REALES narradas en video vertical
(Instagram y Facebook) para público latino. Narras como un locutor profesional de historias de misterio:
voz grave, ritmo pausado, frases que crean atmósfera. De vez en cuando puedes abrir con algo como
"Esta historia es real..." o "Todavía hoy nadie sabe qué pasó...", sin abusar.

Te paso un artículo de Wikipedia. Narra la historia que cuenta.

Reglas:
1. {tipo}
2. USA SOLO LOS HECHOS DEL ARTÍCULO. No inventes nombres, fechas, lugares, cifras, diálogos ni escenas.
   Si el artículo no da un dato, no lo pongas. Puedes ordenar los hechos para crear suspenso y describir
   el ambiente de forma general, pero nada que el artículo no diga.
3. NO SIRVE y respondes solo {{"apto": false, "motivo": "..."}} si: el crimen ocurrió hace menos de 20 años,
   las víctimas eran menores de edad, el caso no tiene sentencia y acusa a una persona con nombre,
   o el artículo no da para una historia de al menos 5 minutos.
4. Dura entre 5 y 8 minutos narrada: entre {min_palabras} y {max_palabras} palabras en total. Usa ese
   espacio para desarrollar bien la historia con los datos del artículo: contexto, lugar, época,
   personas implicadas, pistas, giros y desenlace.
5. Divide el texto en ENTRE 35 Y 50 ESCENAS. Cada escena es una o dos frases de 18 a 28 palabras, fáciles
   de narrar. Menos de 35 escenas es demasiado corto: sigue contando con más hechos del artículo.
6. La PRIMERA escena es el gancho: el hecho más impactante o inquietante del caso, contado en una frase
   que obligue a seguir viendo (nada de saludos, presentaciones ni "hoy les traigo").
   RITMO DE HISTORIA QUE ATRAPA: frases cortas y directas; cada 4 o 5 escenas un giro, un dato sorprendente
   o una pregunta que deje intriga ("Pero eso no fue lo más extraño..."); nada de párrafos de relleno.
7. Nada de violencia gráfica, gore ni contenido sexual. Apto para mayores de 13 años.
8. Cada escena lleva "ambiente": uno de {ambientes} (el lugar donde ocurre esa parte).
   Y lleva "imagen": búsqueda EN INGLÉS de 2 a 4 palabras CONCRETAS de lo que se VE en esa escena:
   un objeto o lugar físico + (opcional) hora o clima. Ejemplos buenos: "sailing ship storm",
   "abandoned farmhouse night", "old courthouse", "police car night", "foggy forest", "lighthouse".
   PROHIBIDO usar palabras abstractas (mystery, fear, disappearance, evidence, crime, death, ghost, history):
   no sirven para buscar fotos. Sin nombres propios ni personas reales identificables.
   Escenas seguidas que pasan en el mismo sitio deben repetir la misma búsqueda.
   Y lleva "momento" (para la música y los efectos): "calma" (contexto, presentación), "tension"
   (algo inquietante se acerca) o "giro" (el dato fuerte, la revelación, lo inesperado). La primera
   escena es "giro". Más o menos 1 de cada 5 escenas es "giro"; las 1 o 2 anteriores a un giro, "tension".
   En las escenas "giro" (y solo en esas) añade "pantalla": 1 a 4 palabras EN MAYÚSCULAS con el dato
   clave para mostrar en grande, sacado del texto de la escena (ej. "1872", "NUNCA APARECIÓ",
   "10 TRIPULANTES", "SIN RASTRO").
9. "titulo": corto y llamativo (máx 40 caracteres), sin comillas.
   "escenario": 2 a 4 palabras en inglés del lugar principal de toda la historia (ej. "old sailing ship ocean").
10. "caption" para Instagram y Facebook:
   - Primera línea: el gancho resumido (máx 110 caracteres).
   - Segunda línea: "{etiqueta}".
   - Tercera línea: una pregunta para que la gente comente.
   - Al final 4 hashtags en español, sin tildes, según el tipo (ej. #casosreales #truecrime #misterio
     #paranormal #historiasreales).

Responde SOLO con JSON:
{{"apto": true, "titulo": "...", "escenario": "...", "escenas": [{{"texto": "...", "ambiente": "...", "imagen": "...", "momento": "giro", "pantalla": "..."}}, {{"texto": "...", "ambiente": "...", "imagen": "...", "momento": "calma"}}, ... (35 a 50 escenas)], "caption": "..."}}"""

ETIQUETAS = {
    "leyenda": "🌙 Leyenda popular real: cuenta lo que dice la tradición, no un hecho comprobado.",
    "misterio": "🔎 Caso real sin resolver, contado con lo que se sabe.",
    "crimen": "⚖️ Caso real, contado con información pública.",
    "paranormal": "👻 Caso paranormal reportado: cuenta lo que dijeron los testigos, no está comprobado.",
}


def groq_texto(sistema: str, usuario: str, esperas: int = 0) -> str:
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
                if e.code == 429 and esperas < 2:
                    # Límite de tokens por minuto: esperar y reintentar el mismo modelo
                    esperas += 1
                    print("  esperando 65 s por el límite por minuto de Groq")
                    time.sleep(65)
                    return groq_texto(sistema, usuario, esperas)
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


MOMENTOS = ("calma", "tension", "giro")


def marcar_momentos(escenas: list[dict], originales: list[dict]) -> None:
    """Copia "momento" y "pantalla" del modelo; si faltan, los reparte con una regla simple."""
    originales = [e for e in originales if e.get("texto", "").strip()]
    for e, o in zip(escenas, originales):
        m = o.get("momento")
        e["momento"] = m if m in MOMENTOS else ""
        pantalla = " ".join(str(o.get("pantalla") or "").split()[:4]).upper()
        if e["momento"] == "giro" and pantalla:
            e["pantalla"] = pantalla[:28]
    giros = sum(e["momento"] == "giro" for e in escenas)
    if giros < max(2, len(escenas) // 8):
        # El modelo no los marcó: gancho al inicio y un giro cada 5 escenas, con tensión antes
        for k, e in enumerate(escenas):
            e["momento"] = "giro" if k == 0 or k % 5 == 4 else ("tension" if k % 5 == 3 else "calma")
    for e in escenas:
        e["momento"] = e["momento"] or "calma"
        if e["momento"] != "giro":
            e.pop("pantalla", None)


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
    marcar_momentos(escenas, historia["escenas"])
    if len(escenas) < 6:
        raise ValueError(f"La historia tiene solo {len(escenas)} escenas")
    return {
        "titulo": historia["titulo"].strip(),
        "escenario": (historia.get("escenario") or "").strip(),
        "escenas": escenas,
        "caption": historia.get("caption", ""),
    }


def main() -> None:
    cargar_env()
    hoy = date.today()
    clave = ROTACION[hoy.toordinal() % len(ROTACION)]
    descripcion = dict(TIPOS)[clave]
    publicadas = cargar_publicadas()
    sistema = INSTRUCCIONES.format(
        tipo=descripcion,
        ambientes=", ".join(AMBIENTES),
        etiqueta=ETIQUETAS[clave],
        # Narrando a unas 145 palabras por minuto: 5 min ≈ 730 palabras, 8 min ≈ 1150
        min_palabras=env("MIN_PALABRAS", "730"),
        max_palabras=env("MAX_PALABRAS", "1150"),
    )
    minimo = int(env("MIN_PALABRAS", "730"))
    usados = set(publicadas)
    descartados: set[str] = set()
    historia, articulo = None, None
    for _ in range(4):  # hasta 4 artículos distintos si alguno no sirve
        articulo = elegir_articulo(clave, usados, descartados)
        print(f"Artículo: {articulo['titulo']} ({len(articulo['texto'])} caracteres)")
        usuario = f"ARTÍCULO DE WIKIPEDIA: «{articulo['titulo']}»\n\n{articulo['texto']}"
        pedido, mejor, palabras = usuario, None, 0
        for intento in range(3):
            respuesta = json.loads(escribir(sistema, pedido))
            if respuesta.get("apto") is False:
                print(f"  No sirve: {respuesta.get('motivo', '')}")
                break
            candidata = validar(respuesta)
            n = sum(len(e["texto"].split()) for e in candidata["escenas"])
            print(f"  Intento {intento + 1}: {n} palabras")
            if n > palabras:
                mejor, palabras = candidata, n
            if n >= minimo * 0.92:
                break
            # Corta: se pide más desarrollo, pero SIEMPRE con datos del artículo
            pedido = (
                f"{usuario}\n\nLa versión anterior tenía solo {n} palabras y debe tener al menos {minimo}. "
                "Escríbela completa otra vez usando MÁS hechos del artículo (contexto, época, lugar, personas, "
                "investigación, consecuencias). No inventes nada."
            )
        if mejor and palabras >= minimo * 0.75:
            historia = mejor
            break
        descartados.add(articulo["titulo"])
    if not historia:
        raise SystemExit("Ningún artículo dio para una historia real de 5 minutos hoy")

    caption = f"{historia['caption'].strip()}\n📚 Basado en: Wikipedia — «{articulo['titulo']}»"
    episodio = {
        "fecha": hoy.isoformat(),
        "tipo": clave,
        "titulo": historia["titulo"],
        "fuente": {"titulo": articulo["titulo"], "url": articulo["url"]},
        "escenario": historia["escenario"],
        "escenas": historia["escenas"],
        "caption": ordenar_hashtags(caption),
    }
    EPISODIO.write_text(json.dumps(episodio, ensure_ascii=False, indent=2), encoding="utf-8")
    palabras = sum(len(e["texto"].split()) for e in episodio["escenas"])
    print(f"{episodio['titulo']} ({clave}, {len(episodio['escenas'])} escenas, {palabras} palabras)")
    for e in episodio["escenas"]:
        print(f"  [{e['ambiente']}] {e['texto']}")


if __name__ == "__main__":
    main()
