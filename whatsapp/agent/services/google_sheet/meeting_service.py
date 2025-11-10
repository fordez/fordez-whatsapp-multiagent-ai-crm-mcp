from datetime import datetime

from whatsapp.agent.services.google_sheet.gspread_helper import get_gspread_client
from whatsapp.config import config

# Inicializar cliente gspread usando el módulo compartido
gc = get_gspread_client(service_name="MeetingService")

# Variables de configuración desde config
SPREADSHEET_ID = config.spreadsheet_id_services
SHEET_NAME_MEETINGS = config.sheet_name_meetings
TIMEZONE = config.timezone


class MeetingService:
    @staticmethod
    def create_meeting(
        event_id: str,
        asunto: str,
        fecha_inicio: str,
        id_cliente: str,
        detalles: str = None,
        meet_link: str = None,
        calendar_link: str = None,
        estado: str = "Programada",
    ) -> dict:
        try:
            if not event_id or not asunto or not fecha_inicio or not id_cliente:
                return {
                    "success": False,
                    "error": "Campos requeridos: event_id, asunto, fecha_inicio e id_cliente",
                }

            sh = gc.open_by_key(SPREADSHEET_ID)
            worksheet = sh.worksheet(SHEET_NAME_MEETINGS)
            all_records = worksheet.get_all_records()
            next_row = len(all_records) + 2

            tz = TIMEZONE
            fecha_creada = datetime.now(tz).strftime("%d/%m/%Y %H:%M")

            # Convertir fecha_inicio y forzar zona horaria
            try:
                fecha_inicio_dt = datetime.fromisoformat(fecha_inicio)
                if fecha_inicio_dt.tzinfo is None:
                    fecha_inicio_dt = tz.localize(fecha_inicio_dt)
            except ValueError:
                fecha_inicio_dt = datetime.strptime(fecha_inicio, "%Y-%m-%d %H:%M:%S")
                fecha_inicio_dt = tz.localize(fecha_inicio_dt)

            fecha_inicio_formatted = fecha_inicio_dt.strftime("%d/%m/%Y %H:%M")

            worksheet.update_cell(next_row, 1, event_id)
            worksheet.update_cell(next_row, 2, asunto)
            worksheet.update_cell(next_row, 3, detalles or "")
            worksheet.update_cell(next_row, 4, fecha_inicio_formatted)
            worksheet.update_cell(next_row, 5, meet_link or "")
            worksheet.update_cell(next_row, 6, calendar_link or "")
            worksheet.update_cell(next_row, 7, estado)
            worksheet.update_cell(next_row, 8, fecha_creada)
            worksheet.update_cell(next_row, 9, id_cliente)

            return {
                "success": True,
                "event_id": event_id,
                "asunto": asunto,
                "fecha_inicio": fecha_inicio_formatted,
                "id_cliente": id_cliente,
                "detalles": detalles,
                "meet_link": meet_link,
                "calendar_link": calendar_link,
                "estado": estado,
                "fecha_creada": fecha_creada,
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def get_meeting_by_id(calendar_id: str) -> dict:
        try:
            if not calendar_id:
                return {"success": False, "error": "calendar_id requerido"}

            sh = gc.open_by_key(SPREADSHEET_ID)
            worksheet = sh.worksheet(SHEET_NAME_MEETINGS)
            all_records = worksheet.get_all_records()

            for row in all_records:
                if str(row.get("Id")) == str(calendar_id):
                    return {"success": True, "meeting": row}

            return {
                "success": False,
                "error": f"No se encontró reunión con ID '{calendar_id}'",
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def get_meetings_by_client(id_cliente: str) -> dict:
        try:
            if not id_cliente:
                return {"success": False, "error": "id_cliente requerido"}

            sh = gc.open_by_key(SPREADSHEET_ID)
            worksheet = sh.worksheet(SHEET_NAME_MEETINGS)
            all_records = worksheet.get_all_records()

            meetings = [
                row
                for row in all_records
                if str(row.get("Id Cliente")) == str(id_cliente)
            ]
            return {"success": True, "count": len(meetings), "meetings": meetings}

        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def get_meetings_by_date(fecha_inicio: str) -> dict:
        try:
            if not fecha_inicio:
                return {"success": False, "error": "fecha_inicio requerida"}

            sh = gc.open_by_key(SPREADSHEET_ID)
            worksheet = sh.worksheet(SHEET_NAME_MEETINGS)
            all_records = worksheet.get_all_records()

            fecha_busqueda = fecha_inicio[:10]
            meetings = [
                row
                for row in all_records
                if str(row.get("Fecha Inicio"))[:10] == fecha_busqueda
            ]

            return {
                "success": True,
                "fecha": fecha_busqueda,
                "count": len(meetings),
                "meetings": meetings,
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def update_meeting(calendar_id: str, fields: dict) -> dict:
        if not calendar_id:
            return {"success": False, "error": "calendar_id requerido"}
        if not fields:
            return {"success": False, "error": "No se proporcionaron campos"}

        try:
            sh = gc.open_by_key(SPREADSHEET_ID)
            worksheet = sh.worksheet(SHEET_NAME_MEETINGS)
            all_records = worksheet.get_all_records()

            col_map = {
                "Id": 1,
                "Asunto": 2,
                "Detalles": 3,
                "Fecha Inicio": 4,
                "Meet_Link": 5,
                "Calendar_Link": 6,
                "Estado": 7,
                "Fecha Creada": 8,
                "Id Cliente": 9,
            }

            for idx, row in enumerate(all_records, start=2):
                if str(row.get("Id")) == str(calendar_id):
                    for key, value in fields.items():
                        col = col_map.get(key)
                        if col:
                            worksheet.update_cell(idx, col, value)
                    return {
                        "success": True,
                        "calendar_id": calendar_id,
                        "updated_fields": list(fields.keys()),
                    }

            return {
                "success": False,
                "error": f"No se encontró reunión con ID '{calendar_id}'",
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def delete_meeting(calendar_id: str) -> dict:
        if not calendar_id:
            return {"success": False, "error": "calendar_id requerido"}

        try:
            sh = gc.open_by_key(SPREADSHEET_ID)
            worksheet = sh.worksheet(SHEET_NAME_MEETINGS)
            all_records = worksheet.get_all_records()

            for idx, row in enumerate(all_records, start=2):
                if str(row.get("Id")) == str(calendar_id):
                    worksheet.delete_rows(idx)
                    return {
                        "success": True,
                        "message": f"Reunión '{calendar_id}' eliminada",
                    }

            return {
                "success": False,
                "error": f"No se encontró reunión con ID '{calendar_id}'",
            }

        except Exception as e:
            return {"success": False, "error": str(e)}
