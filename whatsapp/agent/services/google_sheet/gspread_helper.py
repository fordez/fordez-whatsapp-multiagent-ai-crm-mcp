"""
Módulo compartido para inicializar clientes de gspread.
Evita duplicación de código entre servicios.
"""

import os

import gspread
from google.oauth2.service_account import Credentials

from whatsapp.config import config  # Importamos la configuración unificada


def get_gspread_client(service_name: str = "Service") -> gspread.Client:
    """
    Inicializa un cliente de gspread con credenciales desde archivo o JSON.
    Determina automáticamente si está en desarrollo o producción.

    Args:
        service_name: Nombre del servicio (para logging)

    Returns:
        gspread.Client: Cliente autenticado de gspread

    Raises:
        ValueError: Si las credenciales no son válidas
        FileNotFoundError: Si el archivo no existe
    """
    try:
        # ====================================================
        # Determinar credenciales según ambiente
        # ====================================================
        if config.is_prod:
            # Producción: JSON ya cargado
            service_account_info = config.service_account_json
            creds = Credentials.from_service_account_info(
                service_account_info, scopes=config.scopes
            )
        else:
            # Desarrollo: archivo local
            service_account_file = config.get_service_account_file_path()
            if not os.path.isfile(service_account_file):
                raise FileNotFoundError(
                    f"No se encontró el archivo de Service Account: {service_account_file}"
                )
            creds = Credentials.from_service_account_file(
                service_account_file, scopes=config.scopes
            )

        # ====================================================
        # Inicializar cliente gspread
        # ====================================================
        gc = gspread.authorize(creds)
        return gc

    except Exception as e:
        raise
