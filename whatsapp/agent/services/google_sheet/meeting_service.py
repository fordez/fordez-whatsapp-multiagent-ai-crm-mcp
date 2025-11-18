import logging
from datetime import datetime

from whatsapp.agent.services.google_sheet.gspread_helper import (
    get_gspread_client,
    get_spreadsheet_id_from_context,
)
from whatsapp.config import config

# 🔧 Logger
logger = logging.getLogger("whatsapp.meeting")

gc = get_gspread_client(service_name="MeetingService")
SHEET_NAME_MEETINGS = config.sheet_name_meetings
TIMEZONE = config.timezone  # ya es pytz timezone


# Helpers
def _normalize_row(row: dict):
    # Devuelve un nuevo dict con keys strip()
    return {str(k).strip(): v for k, v in (row or {}).items()}


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
        ctx=None,
    ) -> dict:
        try:
            logger.info(f"📝 Creando reunión en Sheet: {event_id} - {asunto}")

            if not event_id or not asunto or not fecha_inicio or not id_cliente:
                logger.error("❌ Campos requeridos faltantes")
                return {
                    "success": False,
                    "error": "Campos requeridos: event_id, asunto, fecha_inicio e id_cliente",
                }

            spreadsheet_id = get_spreadsheet_id_from_context(ctx)
            sh = gc.open_by_key(spreadsheet_id)
            worksheet = sh.worksheet(SHEET_NAME_MEETINGS)
            all_records = worksheet.get_all_records()

            # Normalizar y buscar si ya existe el event_id
            for idx, row in enumerate(all_records, start=2):
                nrow = _normalize_row(row)
                if str(nrow.get("Id")) == str(event_id):
                    logger.warning(
                        f"⚠️ Reunión {event_id} ya existe, actualizando en lugar de crear..."
                    )
                    # Ya existe → actualizar la fila en lugar de crear nueva
                    return MeetingService.update_meeting(
                        event_id,
                        {
                            "Asunto": asunto,
                            "Detalles": detalles or "",
                            "Fecha Inicio": fecha_inicio,
                            "Meet_Link": meet_link or "",
                            "Calendar_Link": calendar_link or "",
                            "Estado": estado,
                        },
                        ctx=ctx,
                    )

            next_row = len(all_records) + 2
            tz = TIMEZONE
            fecha_creada = datetime.now(tz).strftime("%d/%m/%Y %H:%M")

            # Normalizar fecha_inicio a timezone
            try:
                fecha_inicio_dt = datetime.fromisoformat(fecha_inicio)
                if fecha_inicio_dt.tzinfo is None:
                    fecha_inicio_dt = tz.localize(fecha_inicio_dt)
                else:
                    fecha_inicio_dt = fecha_inicio_dt.astimezone(tz)
            except Exception as e:
                logger.error(f"❌ Formato de fecha inválido: {e}")
                return {"success": False, "error": "Formato de fecha_inicio inválido"}

            # Evitar crear evento en el pasado
            if fecha_inicio_dt <= datetime.now(tz):
                logger.warning("⚠️ Intento de crear reunión en el pasado")
                return {
                    "success": False,
                    "error": "No se puede crear reunión en el pasado",
                }

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

            logger.info(f"✅ Reunión creada en Sheet: fila {next_row}")

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
            logger.error(f"❌ Error creando reunión en Sheet: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def get_meeting_by_id(event_id: str, ctx=None) -> dict:
        try:
            logger.info(f"🔍 Buscando reunión: {event_id}")

            if not event_id:
                return {"success": False, "error": "event_id requerido"}

            spreadsheet_id = get_spreadsheet_id_from_context(ctx)
            sh = gc.open_by_key(spreadsheet_id)
            worksheet = sh.worksheet(SHEET_NAME_MEETINGS)
            all_records = worksheet.get_all_records()

            for idx, row in enumerate(all_records, start=2):
                nrow = _normalize_row(row)
                if str(nrow.get("Id")) == str(event_id):
                    logger.info(f"✅ Reunión encontrada: {nrow.get('Asunto')}")
                    return {"success": True, "meeting": nrow, "row_index": idx}

            logger.warning(f"⚠️ Reunión no encontrada: {event_id}")
            return {
                "success": False,
                "error": f"No se encontró reunión con ID '{event_id}'",
            }
        except Exception as e:
            logger.error(f"❌ Error buscando reunión: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def get_meetings_by_client(id_cliente: str, ctx=None) -> dict:
        try:
            logger.info(f"🔍 Buscando reuniones del cliente: {id_cliente}")

            if not id_cliente:
                return {"success": False, "error": "id_cliente requerido"}

            spreadsheet_id = get_spreadsheet_id_from_context(ctx)
            sh = gc.open_by_key(spreadsheet_id)
            worksheet = sh.worksheet(SHEET_NAME_MEETINGS)
            all_records = worksheet.get_all_records()

            meetings = []
            for row in all_records:
                nrow = _normalize_row(row)
                if str(nrow.get("Id Cliente")) == str(id_cliente):
                    meetings.append(nrow)

            logger.info(f"✅ {len(meetings)} reuniones encontradas")
            return {"success": True, "count": len(meetings), "meetings": meetings}
        except Exception as e:
            logger.error(f"❌ Error buscando reuniones: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def get_meetings_by_date(fecha_inicio: str, ctx=None) -> dict:
        try:
            logger.info(f"🔍 Buscando reuniones en fecha: {fecha_inicio}")

            if not fecha_inicio:
                return {"success": False, "error": "fecha_inicio requerida"}

            spreadsheet_id = get_spreadsheet_id_from_context(ctx)
            sh = gc.open_by_key(spreadsheet_id)
            worksheet = sh.worksheet(SHEET_NAME_MEETINGS)
            all_records = worksheet.get_all_records()

            fecha_busqueda = fecha_inicio[:10]
            meetings = []
            for row in all_records:
                nrow = _normalize_row(row)
                if str(nrow.get("Fecha Inicio", ""))[:10] == fecha_busqueda:
                    meetings.append(nrow)

            logger.info(f"✅ {len(meetings)} reuniones encontradas en {fecha_busqueda}")
            return {
                "success": True,
                "fecha": fecha_busqueda,
                "count": len(meetings),
                "meetings": meetings,
            }
        except Exception as e:
            logger.error(f"❌ Error buscando reuniones por fecha: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def update_meeting(event_id: str, fields: dict, ctx=None) -> dict:
        if not event_id:
            return {"success": False, "error": "event_id requerido"}
        if not fields:
            return {"success": False, "error": "No se proporcionaron campos"}

        try:
            logger.info(f"🔄 Actualizando reunión: {event_id}")

            spreadsheet_id = get_spreadsheet_id_from_context(ctx)
            sh = gc.open_by_key(spreadsheet_id)
            worksheet = sh.worksheet(SHEET_NAME_MEETINGS)
            all_records = worksheet.get_all_records()

            # Mapa de columnas (basado en la estructura que mencionaste)
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
                nrow = _normalize_row(row)
                if str(nrow.get("Id")) == str(event_id):
                    logger.info(f"📝 Actualizando fila {idx}")

                    for key, value in fields.items():
                        col = col_map.get(key)
                        if not col:
                            continue

                        if key == "Fecha Inicio" and value:
                            try:
                                fecha_dt = datetime.fromisoformat(value)
                                if fecha_dt.tzinfo is None:
                                    fecha_dt = tz.localize(fecha_dt)
                                else:
                                    fecha_dt = fecha_dt.astimezone(tz)
                                # Evitar asignar fecha en pasado
                                if fecha_dt <= datetime.now(tz):
                                    logger.warning(
                                        "⚠️ Intento de actualizar a fecha pasada"
                                    )
                                    return {
                                        "success": False,
                                        "error": "No se puede actualizar a una fecha pasada",
                                    }
                                value = fecha_dt.strftime("%d/%m/%Y %H:%M")
                            except Exception:
                                # si falla el parseo, usar el value tal cual
                                pass

                        worksheet.update_cell(idx, col, value)
                        logger.info(f"   ✓ {key}: {value}")

                    logger.info(f"✅ Reunión actualizada correctamente")
                    return {
                        "success": True,
                        "event_id": event_id,
                        "updated_fields": list(fields.keys()),
                    }

            logger.warning(f"⚠️ Reunión no encontrada: {event_id}")
            return {
                "success": False,
                "error": f"No se encontró reunión con ID '{event_id}'",
            }
        except Exception as e:
            logger.error(f"❌ Error actualizando reunión: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def delete_meeting(event_id: str, ctx=None) -> dict:
        if not event_id:
            return {"success": False, "error": "event_id requerido"}

        try:
            logger.info(f"🗑️ Eliminando reunión: {event_id}")

            spreadsheet_id = get_spreadsheet_id_from_context(ctx)
            sh = gc.open_by_key(spreadsheet_id)
            worksheet = sh.worksheet(SHEET_NAME_MEETINGS)
            all_records = worksheet.get_all_records()

            for idx, row in enumerate(all_records, start=2):
                nrow = _normalize_row(row)
                if str(nrow.get("Id")) == str(event_id):
                    worksheet.delete_rows(idx)
                    logger.info(f"✅ Reunión eliminada: fila {idx}")
                    return {
                        "success": True,
                        "message": f"Reunión '{event_id}' eliminada",
                    }

            logger.warning(f"⚠️ Reunión no encontrada: {event_id}")
            return {
                "success": False,
                "error": f"No se encontró reunión con ID '{event_id}'",
            }
        except Exception as e:
            logger.error(f"❌ Error eliminando reunión: {e}")
            return {"success": False, "error": str(e)}
