"""Elige un artículo real de Wikipedia y lo narra con Gemini (o Groq si Gemini no responde)."""

import json
import os
import re
import time
import urllib.error
from datetime import date

from comun import EPISODIO, RAIZ, cargar_env, env, gemini, http, ordenar_hashtags
from fuentes import elegir_caso

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
# Orden de los días: variedad de misterios (no solo terror). Se repite cada 10 días.
ROTACION = ["misterio", "enigma", "crimen", "ovni", "paranormal", "enigma", "misterio", "ovni", "crimen", "leyenda"]
TIPOS.append(
    (
        "enigma",
        "Es un ENIGMA REAL de la historia o la arqueología (cómo se construyó algo, una civilización perdida, un "
        "objeto o lugar inexplicable). Cuenta lo que se sabe de verdad, los datos asombrosos y las teorías de los "
        "expertos, separando bien lo comprobado de las especulaciones. Que dé asombro y curiosidad.",
    )
)
TIPOS.append(
    (
        "ovni",
        "Es un caso OVNI REAL muy conocido (avistamiento o encuentro reportado y documentado). Cuenta lo que dijeron "
        "los testigos, lo que investigaron las autoridades o los expertos y las explicaciones que se han dado, "
        "dejando claro qué está comprobado y qué no. Sin afirmar que fueron extraterrestres.",
    )
)
TIPOS.append(
    (
        "leyenda",
        "Es una leyenda tradicional REAL (existe y la gente la cuenta). Cuéntala como lo recoge el texto "
        "y deja claro que es una leyenda popular, no un hecho comprobado.",
    )
)

INSTRUCCIONES = """Eres el guionista y narrador de "Cuentos del Abuelo", una página de Facebook e Instagram de
historias REALES de misterio, crímenes, apariciones, enigmas de la historia y casos ovni para público latino. Tu trabajo es que la gente NO PUEDA
DEJAR DE VER: cada segundo que alguien sigue mirando es lo que hace crecer la página.

Te paso la información de un caso real. Cuéntalo como un gran narrador de misterio de YouTube: cercano,
intrigante, con suspenso, hablándole directamente a quien escucha.

Reglas de VERDAD (nunca se rompen):
1. {tipo}
2. USA SOLO LOS HECHOS DE LA INFORMACIÓN. No inventes nombres, fechas, lugares, cifras, diálogos ni escenas.
   Puedes ordenar los hechos para crear suspenso, describir el ambiente de forma general y plantear preguntas,
   pero nada que la información no diga. Si las fuentes no coinciden, dilo ("unos dicen... otros...").
3. Responde {{"apto": false, "motivo": "..."}} si el crimen tiene menos de 20 años, si las víctimas eran
   menores de edad, si acusa sin sentencia a una persona con nombre, o si no da para 5 minutos.
4. Nada de violencia gráfica, gore ni contenido sexual. Apto para mayores de 13 años.

Reglas para ATRAPAR (lo más importante después de la verdad):
5. Duración: entre {min_palabras} y {max_palabras} palabras en total (mínimo 5 minutos narrados), en ENTRE 40 Y
   50 ESCENAS de una o dos frases (18 a 28 palabras cada una). NO RESUMAS NI DES SALTOS: cuenta los hechos en
   orden, paso a paso; cada escena avanza UN solo paso de la historia. Si la información trae detalles
   (fechas, lugares, qué dijo cada testigo, qué se encontró), úsalos todos antes de pasar a lo siguiente.
6. Los primeros 3 segundos deciden todo. La PRIMERA escena es un gancho brutal: el dato más impactante,
   extraño o perturbador del caso, dicho de golpe, o una pregunta que nadie puede ignorar. Ejemplos de forma
   (no de contenido): "En 1872 encontraron un barco navegando solo... y la comida todavía estaba caliente."
   / "Diez personas desaparecieron en medio del océano, y nadie ha podido explicar cómo."
   PROHIBIDO empezar con saludos, "hoy les traigo", "bienvenidos", fechas sueltas o contexto aburrido.
7. La SEGUNDA escena promete algo para el final: "Y lo que descubrieron después es todavía más extraño."
8. Bucles abiertos: cada 4 o 5 escenas abre una pregunta o adelanta algo sin contarlo todavía
   ("Pero eso no fue lo más raro...", "Nadie se fijó en un detalle que lo cambiaba todo...").
   Cierra cada bucle más adelante con un dato real.
9. Háblale a quien escucha: "imagina que...", "¿tú qué habrías hecho?", "fíjate en esto". Frases cortas,
   verbos fuertes, detalles concretos que se puedan ver y oír (el frío, el silencio, una puerta, una luz).
   Nada de frases de enciclopedia ni listas de datos sin emoción.
10. Hacia la mitad (escena 15 a 20), una frase corta y natural para retener: "Quédate hasta el final, porque
   lo que encontraron en ... nadie lo esperaba." (con un hecho real que contarás después).
11. Final: cierra con el dato más inquietante que queda, y en la última escena pide la opinión:
   "¿Tú qué crees que pasó? Te leo en los comentarios." Sin despedidas largas.
12. Cada escena lleva "ambiente": uno de {ambientes}.
   Y lleva "imagen": búsqueda EN INGLÉS de 2 a 4 palabras CONCRETAS de lo que se VE en esa escena
   (sirve para buscar fotos y videos de archivo): objeto o lugar físico + (opcional) hora, clima o acción.
   Ejemplos: "sailing ship storm", "old wooden door opening", "police car night", "foggy forest walking",
   "candle flame dark", "rain window night". PROHIBIDO lo abstracto (mystery, fear, crime, death, ghost,
   history), los nombres propios y los niños (nunca "child", "kid", "girl", "boy"). Escenas seguidas en el mismo sitio repiten la misma búsqueda.
   Y lleva "momento": "calma" (contexto), "tension" (algo inquietante se acerca) o "giro" (el dato fuerte,
   la revelación). La primera escena es "giro". Más o menos 1 de cada 5 es "giro"; las 1 o 2 anteriores
   a un giro, "tension". En las escenas "giro" (y solo en esas) añade "pantalla": 1 a 4 palabras EN
   MAYÚSCULAS con el dato clave, sacado del texto de la escena ("1872", "NUNCA APARECIERON", "SIN RASTRO").
13. "titulo": corto y llamativo (máx 40 caracteres), sin comillas. Que dé ganas de verlo.
   "escenario": 2 a 4 palabras en inglés del lugar principal de la historia (ej. "old sailing ship ocean").
14. "portada": la frase de la miniatura del video, 2 a 4 palabras EN MAYÚSCULAS que creen curiosidad sin
   contar el final ("NADIE VOLVIÓ", "¿QUIÉN ESTABA AHÍ?", "EL BARCO VACÍO"). Y "portada_imagen": búsqueda
   en inglés de 2 a 4 palabras de la imagen más impactante de la historia para esa miniatura.
15. "titulo_facebook": título del video para Facebook (máx 90 caracteres) con el nombre del caso y gancho,
   pensado para la búsqueda: "El misterio del Mary Celeste: el barco que apareció sin nadie a bordo".
16. "caption" para Facebook e Instagram, en este orden:
   - Línea 1: gancho fuerte de máx 110 caracteres con el nombre del caso o el lugar (es lo que se ve sin
     pulsar "ver más"). Puede empezar con un emoji relacionado.
   - Líneas 2 y 3: dos frases cortas que aumenten la intriga SIN contar el final.
   - Línea 4: "{etiqueta}".
   - Línea 5: una pregunta concreta para que la gente comente (opinión o "¿lo conocías?").
   - Línea 6: "👉 Síguenos para una historia real nueva cada noche."
   - Al final 4 hashtags en español, sin tildes, del tema y del lugar (ej. #casosreales #misterio
     #sinresolver #historiasreales #paranormal #truecrime).

Responde SOLO con JSON:
{{"apto": true, "titulo": "...", "titulo_facebook": "...", "portada": "...", "portada_imagen": "...", "escenario": "...", "escenas": [{{"texto": "...", "ambiente": "...", "imagen": "...", "momento": "giro", "pantalla": "..."}}, {{"texto": "...", "ambiente": "...", "imagen": "...", "momento": "calma"}}, ... (35 a 50 escenas)], "caption": "..."}}"""

ETIQUETAS = {
    "leyenda": "🌙 Leyenda popular real: cuenta lo que dice la tradición, no un hecho comprobado.",
    "misterio": "🔎 Caso real sin resolver, contado con lo que se sabe.",
    "crimen": "⚖️ Caso real, contado con información pública.",
    "paranormal": "👻 Caso paranormal reportado: cuenta lo que dijeron los testigos, no está comprobado.",
    "enigma": "🏛️ Enigma real de la historia: lo que se sabe y lo que todavía no tiene respuesta.",
    "ovni": "🛸 Caso ovni reportado y documentado: lo que dijeron los testigos y lo que se investigó.",
}


def groq_texto(sistema: str, usuario: str, esperas: int = 0) -> str:
    """Respaldo con Groq: prueba varios modelos y devuelve el JSON como texto."""
    errores = []
    # Groq gratis tiene un límite de ~8000 tokens por minuto (entrada + salida): recortar la información
    usuario = usuario[:7000]
    for modelo in env("GROQ_MODELOS", ",".join(MODELOS_GROQ)).split(","):
        for modo_json in (True, False):
            cuerpo = {
                "model": modelo,
                "messages": [{"role": "system", "content": sistema}, {"role": "user", "content": usuario}],
                "temperature": 1.0,
                # Poco razonamiento y salida acotada: así la petición cabe en el límite por minuto
                "reasoning_effort": "low",
                "max_completion_tokens": 3800,
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
                # JSON mal formado: antes de reintentar sin modo JSON, esperar a que se libere el límite por minuto
                time.sleep(65)
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
            r = gemini(modelo, cuerpo, reintentos=4)
            return r["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            print(f"{modelo} no disponible ({e})")
    if os.environ.get("GROQ_API_KEY"):
        print("Gemini no respondió; escribiendo la historia con Groq")
        return groq_texto(sistema, usuario)
    raise SystemExit("Ningún modelo de texto respondió (Gemini ni Groq)")


class NoApto(Exception):
    """El caso no sirve según las reglas (reciente, víctimas menores, poca información...)."""


PARTE1 = """EN ESTA RESPUESTA ESCRIBE SOLO LA PRIMERA MITAD DE LA HISTORIA: de 20 a 25 escenas, entre {min} y {max}
palabras en total. Incluye el gancho, la promesa, el contexto (época, lugar, personas) y el desarrollo de los
hechos EN ORDEN y con detalle hasta más o menos la mitad del caso, y termina esta mitad en un momento de
suspenso. NO cuentes todavía el desenlace. Incluye también titulo, titulo_facebook, portada, portada_imagen,
escenario y caption con el formato de las reglas. {aviso}"""

PARTE2 = """La PRIMERA MITAD de la historia ya está narrada (abajo). ESCRIBE SOLO LA SEGUNDA MITAD: de 20 a 25
escenas nuevas, entre {min} y {max} palabras, que continúen JUSTO donde terminó la primera, sin repetir nada.
Cuenta el resto de los hechos EN ORDEN y con detalle (investigación, pistas, teorías, giros, cómo terminó, qué
sigue sin respuesta), incluye la frase de retención de la regla 10 al principio de esta mitad y termina con la
pregunta final de la regla 11. Cada escena con texto, ambiente, imagen y momento (y pantalla en los giros).
Responde SOLO con JSON: {{"escenas": [...]}} {aviso}

PRIMERA MITAD (no la repitas):
{primera}"""


def escribir_en_dos_partes(sistema: str, usuario: str, minimo: int, maximo: int, aviso: str = "") -> dict:
    """La historia en dos mitades: cada respuesta es más corta (cabe en los límites gratis) y más detallada."""
    mitad = {"min": minimo // 2, "max": maximo // 2, "aviso": aviso}
    # Las instrucciones van antes de la información: si hay que recortar para Groq, se recorta la información
    r1 = json.loads(escribir(sistema, PARTE1.format(**mitad) + "\n\n" + usuario))
    if r1.get("apto") is False:
        raise NoApto(r1.get("motivo", ""))
    escenas1 = [e for e in r1.get("escenas", []) if e.get("texto", "").strip()]
    primera = "\n".join(e["texto"].strip() for e in escenas1)
    print(f"  Primera mitad: {len(primera.split())} palabras, {len(escenas1)} escenas")
    r2 = json.loads(escribir(sistema, PARTE2.format(**mitad, primera=primera) + "\n\n" + usuario))
    escenas2 = [e for e in r2.get("escenas", []) if e.get("texto", "").strip()]
    print(f"  Segunda mitad: {sum(len(e['texto'].split()) for e in escenas2)} palabras, {len(escenas2)} escenas")
    r1["escenas"] = escenas1 + escenas2
    return validar(r1)


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


NINOS = re.compile(r"\bniñ[oa]s?\b|\bmenores?\b|\bbeb[ée]s?\b|\binfant(?:es|il)\b|\bhijos pequeños\b|\bcriaturas\b", re.I)


def victimas_menores(historia: dict, tipo: str) -> bool:
    """En crímenes y desapariciones, rechaza las historias que hablan de niños (posibles víctimas menores)."""
    if tipo not in ("crimen", "misterio"):
        return False
    texto = " ".join(e["texto"] for e in historia["escenas"])
    menciones = NINOS.findall(texto)
    return len(menciones) >= 2


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
        "titulo_facebook": (historia.get("titulo_facebook") or historia["titulo"]).strip()[:95],
        "portada": " ".join(str(historia.get("portada") or historia["titulo"]).split()[:5]).upper(),
        "portada_imagen": (historia.get("portada_imagen") or historia.get("escenario") or "").strip(),
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
        min_palabras=env("MIN_PALABRAS", "800"),
        max_palabras=env("MAX_PALABRAS", "1150"),
    )
    minimo = int(env("MIN_PALABRAS", "800"))
    maximo = int(env("MAX_PALABRAS", "1150"))
    usados = set(publicadas)
    descartados: set[str] = set()
    historia, articulo = None, None
    for _ in range(4):  # hasta 4 artículos distintos si alguno no sirve
        articulo = elegir_caso(clave, usados, descartados)
        print(f"Artículo: {articulo['titulo']} ({len(articulo['texto'])} caracteres)")
        usuario = f"INFORMACIÓN DEL CASO: «{articulo['titulo']}»\n\n{articulo['texto']}"
        mejor, palabras, aviso = None, 0, ""
        for intento in range(2):
            try:
                candidata = escribir_en_dos_partes(sistema, usuario, minimo, maximo, aviso)
            except NoApto as e:
                print(f"  No sirve: {e}")
                break
            if victimas_menores(candidata, clave):
                print("  No sirve: la historia habla de niños (posibles víctimas menores)")
                break
            n = sum(len(e["texto"].split()) for e in candidata["escenas"])
            print(f"  Intento {intento + 1}: {n} palabras, {len(candidata['escenas'])} escenas")
            if n > palabras:
                mejor, palabras = candidata, n
            if n >= minimo:
                break
            # Corta: se pide más desarrollo, pero SIEMPRE con datos de la información
            aviso = (
                f"La versión anterior quedó corta ({n} palabras en total). Esta vez CADA MITAD debe tener al menos "
                f"{minimo // 2 + 30} palabras: cuenta más hechos de la información, paso a paso, sin resumir."
            )
        if mejor and palabras >= minimo * 0.85:
            historia = mejor
            break
        descartados.add(articulo["titulo"])
    if not historia:
        raise SystemExit("Ningún artículo dio para una historia real de 5 minutos hoy")

    fuentes = articulo.get("fuentes") or ["Wikipedia"]
    caption = f"{historia['caption'].strip()}\n📚 Caso real. Fuentes: {', '.join(fuentes[:5])}"
    episodio = {
        "fecha": hoy.isoformat(),
        "tipo": clave,
        "titulo": historia["titulo"],
        "fuente": {"titulo": articulo["titulo"], "url": articulo["url"], "fuentes": fuentes},
        "titulo_facebook": historia["titulo_facebook"],
        "portada": historia["portada"],
        "portada_imagen": historia["portada_imagen"],
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
