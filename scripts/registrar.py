"""Tras publicar: guarda la fecha de hoy y el título de la historia en el repo con la API de GitHub.

Se usa la API (no git) porque a esa altura public/episodio.json está modificado y
un git pull --rebase fallaría.
"""

import base64
import json
import os
import subprocess
from datetime import datetime
from zoneinfo import ZoneInfo

from comun import EPISODIO, RAIZ

REPO = os.environ["GITHUB_REPOSITORY"]


def api(*args: str) -> str:
    return subprocess.run(["gh", "api", *args], check=True, capture_output=True, text=True).stdout.strip()


def guardar(ruta: str, contenido: str, mensaje: str) -> None:
    try:
        sha = api(f"repos/{REPO}/contents/{ruta}?ref=main", "--jq", ".sha")
    except subprocess.CalledProcessError:
        sha = ""
    args = [
        "-X", "PUT", f"repos/{REPO}/contents/{ruta}",
        "-f", f"message={mensaje}", "-f", "branch=main",
        "-f", f"content={base64.b64encode(contenido.encode()).decode()}",
    ]
    if sha:
        args += ["-f", f"sha={sha}"]
    print(ruta, "->", api(*args, "--jq", ".commit.sha"))


def main() -> None:
    hoy = datetime.now(ZoneInfo("America/Santo_Domingo")).date().isoformat()
    episodio = json.loads(EPISODIO.read_text(encoding="utf-8"))
    # Se guarda el artículo de Wikipedia usado, para no contar dos veces la misma historia
    titulo = episodio.get("fuente", {}).get("titulo") or episodio["titulo"]
    guardar("data/episodio_publicado.json", json.dumps({"fecha": hoy}) + "\n", "Historia publicada")
    lista = RAIZ / "data" / "historias_publicadas.json"
    titulos = json.loads(lista.read_text(encoding="utf-8")) if lista.exists() else []
    if titulo not in titulos:
        titulos.append(titulo)
    guardar(
        "data/historias_publicadas.json",
        json.dumps(titulos, ensure_ascii=False, indent=1) + "\n",
        f"Historia publicada: {titulo}",
    )


if __name__ == "__main__":
    main()
