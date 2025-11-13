from datetime import datetime

from whatsapp.agent.services.google_sheet.gspread_helper import (
    get_gspread_client,
    get_spreadsheet_id_from_context,
)
from whatsapp.config import config

# Inicializar cliente gspread
gc = get_gspread_client(service_name="MeetingService")

# Variables de configuración
SHEET_NAME_MEETINGS = config.sheet_name_meetings
TIMEZONE = config.timezone


def get_key_case_insensitive(row: dict, key_name: str):
    """Devuelve el valor de una columna sin importar mayúsculas/minúsculas."""
    for k in row.keys():
        if k.strip().lower() == key_name.lower():
            return row[k]
    return None


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
        estado: str = "Agendada",
        ctx=None,
    ) -> dict:
        """Crea o actualiza una reunión en la hoja 'Meetings'."""
        try:
            if not event_id or not asunto or not fecha_inicio or not id_cliente:
                return {
                    "success": False,
                    "error": "Campos requeridos: event_id, asunto, fecha_inicio e id_cliente",
                }

            spreadsheet_id = get_spreadsheet_id_from_context(ctx)
            sh = gc.open_by_key(spreadsheet_id)
            worksheet = sh.worksheet(SHEET_NAME_MEETINGS)
            all_records = worksheet.get_all_records()

            # 🧠 Verificar si ya existe la reunión (actualizar en lugar de crear)
            for idx, row in enumerate(all_records, start=2):
                existing_id = get_key_case_insensitive(row, "Id")
                if str(existing_id) == str(event_id):
                    # Ya existe → actualiza
                    return MeetingService.update_meeting(
                        event_id,
                        {
                            "Asunto": asunto,
                            "Detalles": detalles or "",
                            "Fecha Inicio": fecha_inicio,
                            "Meet_Link": meet_link or "",
                            "Calendar_Link": calendar_link or "",
                            "Estado": "Reagendada",
                        },
                        ctx=ctx,
                    )

            # 🆕 Crear nuevo registro
            next_row = len(all_records) + 2
            tz = TIMEZONE
            fecha_creada = datetime.now(tz).strftime("%d/%m/%Y %H:%M")

            # Convertir fecha_inicio a timezone local
            try:
                fecha_inicio_dt = datetime.fromisoformat(fecha_inicio)
                if fecha_inicio_dt.tzinfo is None:
                    fecha_inicio_dt = tz.localize(fecha_inicio_dt)
                else:
                    fecha_inicio_dt = fecha_inicio_dt.astimezone(tz)
            except Exception:
                # fallback para formatos simples
                fecha_inicio_dt = datetime.strptime(fecha_inicio, "%Y-%m-%d %H:%M:%S")
                fecha_inicio_dt = tz.localize(fecha_inicio_dt)

            fecha_inicio_formatted = fecha_inicio_dt.strftime("%d/%m/%Y %H:%M")

            # Insertar fila
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

    # 🔍 Obtener reunión por ID
    @staticmethod
    def get_meeting_by_id(event_id: str, ctx=None) -> dict:
        try:
            if not event_id:
                return {"success": False, "error": "event_id requerido"}

            spreadsheet_id = get_spreadsheet_id_from_context(ctx)
            sh = gc.open_by_key(spreadsheet_id)
            worksheet = sh.worksheet(SHEET_NAME_MEETINGS)
            all_records = worksheet.get_all_records()

            for idx, row in enumerate(all_records, start=2):
                existing_id = get_key_case_insensitive(row, "Id")
                if str(existing_id) == str(event_id):
                    return {"success": True, "meeting": row, "row_index": idx}

            return {
                "success": False,
                "error": f"No se encontró reunión con ID '{event_id}'",
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    # 🔍 Obtener reuniones por cliente
    @staticmethod
    def get_meetings_by_client(id_cliente: str, ctx=None) -> dict:
        try:
            if not id_cliente:
                return {"success": False, "error": "id_cliente requerido"}

            spreadsheet_id = get_spreadsheet_id_from_context(ctx)
            sh = gc.open_by_key(spreadsheet_id)
            worksheet = sh.worksheet(SHEET_NAME_MEETINGS)
            all_records = worksheet.get_all_records()

            meetings = [
                row
                for row in all_records
                if str(get_key_case_insensitive(row, "Id Cliente")) == str(id_cliente)
            ]
            return {"success": True, "count": len(meetings), "meetings": meetings}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ✏️ Actualizar reunión existente
    @staticmethod
    def update_meeting(event_id: str, fields: dict, ctx=None) -> dict:
        """Actualiza una reunión existente sin crear duplicado."""
        if not event_id:
            return {"success": False, "error": "event_id requerido"}
        if not fields:
            return {"success": False, "error": "No se proporcionaron campos"}

        try:
            spreadsheet_id = get_spreadsheet_id_from_context(ctx)
            sh = gc.open_by_key(spreadsheet_id)
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

            tz = TIMEZONE

            for idx, row in enumerate(all_records, start=2):
                existing_id = get_key_case_insensitive(row, "Id")
                if str(existing_id) == str(event_id):
                    for key, value in fields.items():
                        col = col_map.get(key)
                        if not col:
                            continue

                        # 🕓 Si es fecha, aplicar timezone y formato
                        if key == "Fecha Inicio" and value:
                            try:
                                fecha_dt = datetime.fromisoformat(value)
                                if fecha_dt.tzinfo is None:
                                    fecha_dt = tz.localize(fecha_dt)
                                else:
                                    fecha_dt = fecha_dt.astimezone(tz)
                                value = fecha_dt.strftime("%d/%m/%Y %H:%M")
                            except Exception:
                                pass

                        worksheet.update_cell(idx, col, value)

                    # Asegurar estado correcto al reagendar
                    if "Estado" not in fields:
                        worksheet.update_cell(idx, 7, "Reagendada")

                    return {
                        "success": True,
                        "event_id": event_id,
                        "updated_fields": list(fields.keys()),
                        "estado": fields.get("Estado", "Reagendada"),
                    }

            return {
                "success": False,
                "error": f"No se encontró reunión con ID '{event_id}'",
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    # 🗑️ Eliminar reunión
    @staticmethod
    def delete_meeting(event_id: str, ctx=None) -> dict:
        if not event_id:
            return {"success": False, "error": "event_id requerido"}

        try:
            spreadsheet_id = get_spreadsheet_id_from_context(ctx)
            sh = gc.open_by_key(spreadsheet_id)
            worksheet = sh.worksheet(SHEET_NAME_MEETINGS)
            all_records = worksheet.get_all_records()

            for idx, row in enumerate(all_records, start=2):
                existing_id = get_key_case_insensitive(row, "Id")
                if str(existing_id) == str(event_id):
                    worksheet.delete_rows(idx)
                    return {
                        "success": True,
                        "message": f"Reunión '{event_id}' eliminada",
                    }

            return {
                "success": False,
                "error": f"No se encontró reunión con ID '{event_id}'",
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
