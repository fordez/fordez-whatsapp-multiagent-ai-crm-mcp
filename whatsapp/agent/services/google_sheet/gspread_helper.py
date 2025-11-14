"""
Módulo compartido para inicializar clientes de gspread.
Evita duplicación de código entre servicios.
Ahora soporta uso del sheet_crm_id desde contexto.
"""

import gspread
from agents import RunContextWrapper
from google.oauth2.service_account import Credentials

from whatsapp.config import config


def get_gspread_client(service_name: str = "Service") -> gspread.Client:
    """
    Inicializa un cliente de gspread con credenciales desde JSON cargado en Config.
    Funciona tanto en desarrollo como en producción.

    Args:
        service_name: Nombre del servicio (para logging)

    Returns:
        gspread.Client: Cliente autenticado de gspread
    """
    try:
        creds = Credentials.from_service_account_info(
            config.service_account_json,
            scopes=config.scopes,
        )
        return gspread.authorize(creds)
    except Exception as e:
        raise RuntimeError(f"Error inicializando cliente gspread ({service_name}): {e}")


def get_spreadsheet_id_from_context(ctx: RunContextWrapper = None) -> str:
    """
    Obtiene el sheet_crm_id desde el contexto.

    Args:
        ctx: Contexto del agente (opcional)

    Returns:
        str: ID de la hoja de cálculo a usar

    Raises:
        ValueError: Si no hay ID disponible ni en contexto
    """
    if ctx and hasattr(ctx, "sheet_crm_id") and ctx.sheet_crm_id:
        return ctx.sheet_crm_id

    # Si no se encuentra en el contexto, lanzar error explícito
    raise ValueError(
        "No se encontró 'sheet_crm_id' en el contexto. "
        "Debe proporcionarse explícitamente en el contexto del agente."
    )
