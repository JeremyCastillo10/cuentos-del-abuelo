"""Convierte un token temporal de usuario en un token de página que no vence y lo guarda en .env.

Antes de correrlo pon en .env: FB_APP_ID, FB_APP_SECRET y FB_USER_TOKEN (del Explorador de la API Graph).
Uso: python scripts/token_facebook.py
"""

import re
import urllib.parse

from comun import RAIZ, cargar_env, env, http

API = "https://graph.facebook.com/v21.0"


def guardar_en_env(valores: dict) -> None:
    archivo = RAIZ / ".env"
    texto = archivo.read_text(encoding="utf-8") if archivo.exists() else ""
    for k, v in valores.items():
        if re.search(rf"^{k}=.*$", texto, re.M):
            texto = re.sub(rf"^{k}=.*$", f"{k}={v}", texto, flags=re.M)
        else:
            texto += f"\n{k}={v}"
    archivo.write_text(texto.strip() + "\n", encoding="utf-8")


def main() -> None:
    cargar_env()
    # 1. Token de usuario de corta duración -> larga duración (60 días)
    q = urllib.parse.urlencode(
        {
            "grant_type": "fb_exchange_token",
            "client_id": env("FB_APP_ID"),
            "client_secret": env("FB_APP_SECRET"),
            "fb_exchange_token": env("FB_USER_TOKEN"),
        }
    )
    largo = http(f"{API}/oauth/access_token?{q}")["access_token"]

    # 2. Con el token largo, el token de cada página que administras no vence
    paginas = http(f"{API}/me/accounts?fields=id,name,access_token&access_token={largo}")["data"]
    if not paginas:
        raise SystemExit("No se encontró ninguna página: revisa que el token tenga pages_show_list y que elegiste la página")
    for i, p in enumerate(paginas):
        print(f"{i}: {p['name']} ({p['id']})")
    buscar = env("FB_PAGE_NOMBRE", "abuela").lower()
    elegida = next((p for p in paginas if buscar in p["name"].lower()), paginas[0])

    guardar_en_env({"FB_PAGE_ID": elegida["id"], "FB_PAGE_TOKEN": elegida["access_token"], "FB_USER_TOKEN": ""})
    print(f"Listo: guardado en .env el token de la página '{elegida['name']}' (no vence)")


if __name__ == "__main__":
    main()
