from datetime import datetime

import gspread
import pytz
import shortuuid

from whatsapp.agent.services.google_sheet.gspread_helper import get_gspread_client
from whatsapp.config import config

# Inicializamos el cliente gspread usando el módulo compartido
gc = get_gspread_client(service_name="CRMService")

# Variables de config
SPREADSHEET_ID = config.spreadsheet_id_services  # hoja de servicios/CRM
SHEET_NAME = config.sheet_name_lead
TIMEZONE = config.timezone


class CRMService:
    @staticmethod
    def resolve_client_id(client_id_or_phone: str) -> str | None:
        if not client_id_or_phone:
            return None

        sh = gc.open_by_key(SPREADSHEET_ID)
        worksheet = sh.worksheet(SHEET_NAME)
        all_records = worksheet.get_all_records()
        phone_norm = "".join(filter(str.isdigit, str(client_id_or_phone)))

        for row in all_records:
            if str(row.get("Id")) == str(client_id_or_phone):
                return row.get("Id")
            if "".join(filter(str.isdigit, str(row.get("Telefono")))) == phone_norm:
                return row.get("Id")
        return None

    @staticmethod
    def verify_client(telefono=None, correo=None, usuario=None) -> dict:
        if not telefono and not correo and not usuario:
            return {"error": "Debe proporcionar al menos un identificador"}

        try:
            sh = gc.open_by_key(SPREADSHEET_ID)
            worksheet = sh.worksheet(SHEET_NAME)
            all_records = worksheet.get_all_records()
            telefono_norm = (
                "".join(filter(str.isdigit, str(telefono))) if telefono else ""
            )

            for row in all_records:
                matched_by = None
                if (
                    telefono
                    and "".join(filter(str.isdigit, str(row.get("Telefono"))))
                    == telefono_norm
                ):
                    matched_by = "telefono"
                elif correo and str(row.get("Correo")).lower() == str(correo).lower():
                    matched_by = "correo"
                elif usuario and str(row.get("Usuario")) == str(usuario):
                    matched_by = "usuario"

                if matched_by:
                    return {
                        "exists": True,
                        "client_id": row.get("Id"),
                        "nombre": row.get("Nombre"),
                        "telefono": row.get("Telefono"),
                        "correo": row.get("Correo"),
                        "tipo": row.get("Tipo"),
                        "estado": row.get("Estado"),
                        "canal": row.get("Canal"),
                        "nota": row.get("Nota"),
                        "usuario": row.get("Usuario"),
                        "fecha_creacion": row.get("Fecha Creacion"),
                        "fecha_conversion": row.get("Fecha Conversion"),
                        "matched_by": matched_by,
                    }

            return {"exists": False, "client_id": None}

        except Exception as e:
            return {"error": str(e)}

    @staticmethod
    def create_client_service(
        nombre, canal, telefono=None, correo=None, nota=None, usuario=None
    ) -> dict:
        if not nombre or not canal:
            return {
                "success": False,
                "error": "Los campos 'nombre' y 'canal' son requeridos",
            }

        try:
            sh = gc.open_by_key(SPREADSHEET_ID)
            worksheet = sh.worksheet(SHEET_NAME)
            all_records = worksheet.get_all_records()
            fecha_actual = datetime.now(TIMEZONE).strftime("%Y-%m-%d %H:%M:%S")
            client_id = shortuuid.ShortUUID().random(length=6)
            next_row = len(all_records) + 2

            worksheet.update_cell(next_row, 1, client_id)
            worksheet.update_cell(next_row, 2, nombre)
            worksheet.update_cell(next_row, 3, telefono or "")
            worksheet.update_cell(next_row, 4, correo or "")
            worksheet.update_cell(next_row, 5, "Lead")
            worksheet.update_cell(next_row, 6, "Nuevo")
            worksheet.update_cell(next_row, 7, nota or "")
            worksheet.update_cell(next_row, 8, usuario or "")
            worksheet.update_cell(next_row, 9, canal)
            worksheet.update_cell(next_row, 10, fecha_actual)
            worksheet.update_cell(next_row, 11, "")
            worksheet.update_cell(next_row, 12, "")

            return {
                "success": True,
                "created": True,
                "client_id": client_id,
                "nombre": nombre,
                "canal": canal,
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def update_client_dynamic(client_id: str, fields: dict) -> dict:
        if not client_id:
            return {"success": False, "error": "client_id requerido"}
        if not fields:
            return {"success": False, "error": "No se proporcionaron campos"}

        resolved_id = CRMService.resolve_client_id(client_id)
        if not resolved_id:
            return {
                "success": False,
                "error": f"No se encontró cliente con ID o teléfono '{client_id}'",
            }

        try:
            sh = gc.open_by_key(SPREADSHEET_ID)
            worksheet = sh.worksheet(SHEET_NAME)
            all_records = worksheet.get_all_records()
            updated_fields = []

            col_map = {
                "Id": 1,
                "Nombre": 2,
                "Telefono": 3,
                "Correo": 4,
                "Tipo": 5,
                "Estado": 6,
                "Nota": 7,
                "Usuario": 8,
                "Canal": 9,
                "Fecha Creacion": 10,
                "Fecha Conversion": 11,
                "Thread_Id": 12,
            }

            for idx, row in enumerate(all_records, start=2):
                if str(row.get("Id")) == str(resolved_id):
                    for key, value in fields.items():
                        col = col_map.get(key)
                        if col:
                            worksheet.update_cell(idx, col, value)
                            updated_fields.append(key)
                    return {
                        "success": True,
                        "client_id": resolved_id,
                        "updated_fields": updated_fields,
                    }

            return {
                "success": False,
                "error": f"Cliente con ID '{resolved_id}' no encontrado",
            }

        except Exception as e:
            return {"success": False, "error": str(e)}
