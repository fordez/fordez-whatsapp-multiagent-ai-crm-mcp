from whatsapp.agent.services.google_sheet.gspread_helper import (
    get_gspread_client,
    get_spreadsheet_id_from_context,
)
from whatsapp.config import config

# Inicializamos el cliente gspread usando el módulo compartido
gc = get_gspread_client(service_name="CatalogService")

# Usamos directamente las variables de config
SHEET_NAME = config.sheet_name_catalog


class CatalogService:
    @staticmethod
    def get_all_services(ctx=None) -> dict:
        """
        Obtiene todos los servicios del catálogo desde Google Sheets.
        """
        try:
            spreadsheet_id = get_spreadsheet_id_from_context(ctx)
            sh = gc.open_by_key(spreadsheet_id)
            worksheet = sh.worksheet(SHEET_NAME)
            all_records = worksheet.get_all_records()
            return {"success": True, "services": all_records}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def get_service_by_name(service_name: str, ctx=None) -> dict:
        """
        Busca un servicio por su nombre dentro del catálogo.
        """
        try:
            spreadsheet_id = get_spreadsheet_id_from_context(ctx)
            sh = gc.open_by_key(spreadsheet_id)
            worksheet = sh.worksheet(SHEET_NAME)
            all_records = worksheet.get_all_records()

            for row in all_records:
                if str(row.get("Nombre")).strip().lower() == service_name.lower():
                    return {"success": True, "service": row}

            return {"success": False, "error": "Servicio no encontrado"}
        except Exception as e:
            return {"success": False, "error": str(e)}
