# whatsapp/webhook/utilis/user_verify.py
import uuid
from datetime import datetime

import gspread
from oauth2client.service_account import ServiceAccountCredentials

from whatsapp.config import SERVICE_ACCOUNT_FILE, SHEET_NAME_LEAD, TIMEZONE, logger


def normalize_number(number: str) -> str:
    """Elimina todo excepto dígitos"""
    if not number:
        return ""
    return "".join(filter(str.isdigit, str(number)))


def get_sheet(spreadsheet_id: str):
    """Carga la hoja Lead de un spreadsheet específico"""
    scope = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(
        SERVICE_ACCOUNT_FILE, scope
    )
    client = gspread.authorize(creds)
    sheet = client.open_by_key(spreadsheet_id).worksheet(SHEET_NAME_LEAD)
    return sheet


async def load_user(phone_number: str, spreadsheet_id: str) -> dict:
    """
    Verifica si existe un usuario, retorna los datos completos o None.
    Incluye el índice de la fila para actualizaciones posteriores.
    """
    key = normalize_number(phone_number)

    try:
        sheet = get_sheet(spreadsheet_id)
        rows = sheet.get_all_records()

        for idx, row in enumerate(rows, start=2):  # start=2 porque fila 1 son headers
            if normalize_number(row.get("Telefono")) == key:
                logger.info(f"🟦 Sheet - Usuario {phone_number} encontrado: {row}")
                # Agregar índice de fila para actualizaciones
                row["_row_index"] = idx
                return row

        logger.warning(f"⚠️ Usuario {phone_number} no encontrado en Sheets")
        return None
    except Exception as e:
        logger.error(f"❌ Error cargando usuario {phone_number} desde Sheets: {e}")
        return None


async def update_user_fields(
    phone_number: str, spreadsheet_id: str, updates: dict
) -> dict:
    """
    Actualiza campos específicos de un usuario existente.
    Solo actualiza los campos que tienen valores no vacíos.
    """
    try:
        user = await load_user(phone_number, spreadsheet_id)
        if not user:
            logger.warning(
                f"⚠️ No se puede actualizar, usuario {phone_number} no existe"
            )
            return None

        row_index = user.get("_row_index")
        if not row_index:
            logger.error(f"❌ No se pudo obtener el índice de fila para {phone_number}")
            return None

        sheet = get_sheet(spreadsheet_id)
        headers = sheet.row_values(1)

        # Actualizar solo los campos especificados que tengan valor
        updated_fields = []
        for field, value in updates.items():
            if field in headers and value:  # Solo actualizar si hay valor
                col_index = headers.index(field) + 1  # +1 porque gspread usa 1-indexed
                sheet.update_cell(row_index, col_index, value)
                updated_fields.append(field)
                logger.info(
                    f"✅ Campo '{field}' actualizado a '{value}' para {phone_number}"
                )

        if updated_fields:
            logger.info(f"📝 Campos actualizados: {', '.join(updated_fields)}")

        # Retornar usuario actualizado
        return await load_user(phone_number, spreadsheet_id)

    except Exception as e:
        logger.error(f"❌ Error actualizando usuario {phone_number}: {e}")
        return None


async def create_user(
    phone_number: str, spreadsheet_id: str, defaults: dict = None
) -> dict:
    """Crea un usuario en la hoja Lead si no existe"""
    defaults = defaults or {}

    # Evitar duplicados: revisamos antes
    existing_user = await load_user(phone_number, spreadsheet_id)
    if existing_user:
        logger.info(f"🟢 Usuario {phone_number} ya existe, no se creará duplicado")
        return existing_user

    try:
        sheet = get_sheet(spreadsheet_id)
        timestamp = datetime.now(TIMEZONE).strftime("%d/%m/%Y %H:%M:%S")
        short_id = str(uuid.uuid4())[:8]  # Short UUID

        new_row = {
            "Id": short_id,
            "Nombre": defaults.get("Nombre", ""),
            "Telefono": phone_number,
            "Correo": defaults.get("Correo", ""),
            "Tipo": defaults.get("Tipo", "Lead"),
            "Estado": defaults.get("Estado", "Nuevo"),
            "Nota": defaults.get("Nota", ""),
            "Usuario": defaults.get("Usuario", ""),
            "Canal": defaults.get("Canal", ""),
            "Fecha Adquisicion": timestamp,
            "Fecha Conversion": defaults.get("Fecha Conversion", ""),
            "Thread_Id": defaults.get("Thread_Id", ""),
        }

        sheet.append_row(list(new_row.values()))
        logger.info(f"🟦 Sheet - Usuario {phone_number} creado con éxito")
        logger.info(
            f"📋 Datos: Canal={new_row['Canal']}, Usuario={new_row['Usuario']}, Nombre={new_row['Nombre']}"
        )
        return new_row

    except Exception as e:
        logger.error(f"❌ Error creando usuario {phone_number}: {e}")
        return None


async def get_or_create_user(
    phone_number: str, spreadsheet_id: str, defaults: dict = None
) -> dict:
    """
    Intenta cargar el usuario y si no existe, lo crea.
    Si existe, actualiza campos relevantes que hayan cambiado.
    """
    defaults = defaults or {}
    user = await load_user(phone_number, spreadsheet_id)

    if user:
        # Usuario existe, verificar si hay campos que actualizar
        updates = {}

        # Actualizar Canal si es diferente
        current_canal = user.get("Canal", "")
        new_canal = defaults.get("Canal", "")
        if new_canal and current_canal != new_canal:
            updates["Canal"] = new_canal
            logger.info(f"🔄 Canal cambiado de '{current_canal}' a '{new_canal}'")

        # Actualizar Usuario si es diferente
        current_usuario = user.get("Usuario", "")
        new_usuario = defaults.get("Usuario", "")
        if new_usuario and current_usuario != new_usuario:
            updates["Usuario"] = new_usuario
            logger.info(f"🔄 Usuario cambiado de '{current_usuario}' a '{new_usuario}'")

        # Actualizar Nombre si viene vacío y ahora tiene valor
        current_nombre = user.get("Nombre", "").strip()
        new_nombre = defaults.get("Nombre", "").strip()
        if new_nombre and not current_nombre:
            updates["Nombre"] = new_nombre
            logger.info(f"🔄 Nombre agregado: '{new_nombre}'")

        # Si hay actualizaciones, aplicarlas
        if updates:
            user = await update_user_fields(phone_number, spreadsheet_id, updates)

        return user

    # Usuario no existe, crear uno nuevo
    return await create_user(phone_number, spreadsheet_id, defaults)
