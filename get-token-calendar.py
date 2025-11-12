#!/usr/bin/env python3
"""
Script para obtener token de Google Calendar/Meet manualmente.
Guarda el token en la carpeta actual.
"""

import json
import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# Scopes necesarios para Calendar/Meet
SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/calendar.readonly",
]

# Nombre de archivos locales
TOKEN_FILE = "token.json"  # aquí se guardará el token
CREDENTIALS_FILE = "credentials.json"  # archivo de credenciales OAuth2


def get_token():
    """Obtiene el token de Google usando OAuth2 flow y lo guarda localmente."""
    print(f"\n🔐 Obteniendo token de Google Calendar/Meet")
    print(f"📁 Token se guardará en: {os.path.abspath(TOKEN_FILE)}")
    print(f"📄 Usando credenciales de: {os.path.abspath(CREDENTIALS_FILE)}\n")

    if not os.path.exists(CREDENTIALS_FILE):
        print(
            f"❌ ERROR: No se encontró el archivo de credenciales: {CREDENTIALS_FILE}"
        )
        print(
            "💡 Descarga tus credenciales OAuth2 desde Google Cloud Console y guárdalas como credentials.json"
        )
        return

    creds = None

    # Verificar si ya existe un token
    if os.path.exists(TOKEN_FILE):
        print("⚠️  Ya existe un token en esa ruta.")
        respuesta = input("¿Deseas renovarlo? (s/n): ").strip().lower()
        if respuesta != "s":
            print("❌ Operación cancelada.")
            return
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        except Exception as e:
            print(f"⚠️  Token existente inválido: {e}")

    # Si no hay credenciales válidas, iniciar flujo OAuth
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("🔄 Refrescando token expirado...")
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"⚠️  No se pudo refrescar: {e}")
                creds = None

        if not creds:
            print("🌐 Iniciando flujo OAuth2...")
            print("🔓 Se abrirá tu navegador para autorizar el acceso...\n")
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=8080)

    # Guardar el token en archivo local
    with open(TOKEN_FILE, "w") as token:
        token_data = {
            "token": creds.token,
            "refresh_token": creds.refresh_token,
            "token_uri": creds.token_uri,
            "client_id": creds.client_id,
            "client_secret": creds.client_secret,
            "scopes": creds.scopes,
        }
        json.dump(token_data, token, indent=2)

    print(f"\n✅ Token guardado exitosamente en: {TOKEN_FILE}")
    print("🎉 Ahora puedes usar este token manualmente en tu configuración.\n")


def main():
    """Ejecución directa."""
    get_token()


if __name__ == "__main__":
    main()
