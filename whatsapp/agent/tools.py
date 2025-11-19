"""
Herramientas para agente de servicio al cliente.
Scope limitado por seguridad - solo operaciones esenciales.
Todas las tools pasan el contexto local mediante RunContextWrapper.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict

import pytz
from agents import RunContextWrapper, function_tool

from whatsapp.agent.models import (
    CalendarCheckAvailabilityInput,
    CalendarCreateMeetInput,
    CalendarGetEventDetailsInput,
    CalendarUpdateMeetInput,
    CreateClientInput,
    GetMeetingsByClientInput,
    GetServiceByNameInput,
    UpdateClientInput,
    UpdateClientNoteInput,
    UpdateClientStatusInput,
    UpdateMeetingStatusInput,
    VerifyClientInput,
)
from whatsapp.agent.services.google_calendar_meet.calendar_service import (
    CalendarService,
)
from whatsapp.agent.services.google_sheet.catalog_service import CatalogService
from whatsapp.agent.services.google_sheet.crm_service import CRMService
from whatsapp.agent.services.google_sheet.meeting_service import MeetingService
from whatsapp.config import config

# 🔧 Logger
logger = logging.getLogger("whatsapp.tools")

# Zona horaria del sistema
TZ = config.timezone


# =============================
# 🔧 Helpers
# =============================
def _parse_iso_to_tz(dt_str):
    """
    Recibe ISO string o datetime, retorna tz-aware datetime en TZ.
    Admite formatos con 'Z' o sin zona.
    """
    from datetime import datetime as _dt

    tz = TZ
    if isinstance(dt_str, _dt):
        d = dt_str
    else:
        # Permite: "2025-11-17 10:00:00", "2025-11-17T10:00:00Z", etc.
        dt_str = str(dt_str).replace("Z", "+00:00").replace(" ", "T")
        d = _dt.fromisoformat(dt_str)

    # Asegurar timezone
    if d.tzinfo is None:
        d = tz.localize(d)
    else:
        d = d.astimezone(tz)

    return d


# =============================
# 🧩 TOOLS DE CLIENTES
# =============================
@function_tool
def verify_client(
    wrapper: RunContextWrapper, input: VerifyClientInput
) -> Dict[str, Any]:
    logger.info(f"🔍 [TOOL] verify_client llamada")
    ctx = wrapper.context
    return CRMService.verify_client(
        telefono=input.telefono, correo=input.correo, usuario=input.usuario, ctx=ctx
    )


@function_tool
def create_client(
    wrapper: RunContextWrapper, input: CreateClientInput
) -> Dict[str, Any]:
    ctx = wrapper.context
    result = CRMService.create_client_service(
        nombre=input.nombre,
        canal=input.canal,
        telefono=input.telefono,
        correo=input.correo,
        nota=input.nota,
        usuario=input.usuario,
        ctx=ctx,
    )
    return {"success": True, "data": result}


@function_tool
def update_client(
    wrapper: RunContextWrapper, input: UpdateClientInput
) -> Dict[str, Any]:
    ctx = wrapper.context
    fields = {}

    if input.nombre:
        fields["Nombre"] = input.nombre
    if input.correo:
        fields["Correo"] = input.correo
    if input.usuario:
        fields["Usuario"] = input.usuario

    if not fields:
        return {"success": False, "error": "No hay campos para actualizar"}

    return CRMService.update_client_dynamic(
        client_id=input.client_id, fields=fields, ctx=ctx
    )


@function_tool
def update_client_note(wrapper: RunContextWrapper, input: UpdateClientNoteInput):
    ctx = wrapper.context
    return CRMService.update_client_dynamic(
        client_id=input.client_id, fields={"Nota": input.nota}, ctx=ctx
    )


@function_tool
def update_client_status(wrapper: RunContextWrapper, input: UpdateClientStatusInput):
    ctx = wrapper.context
    return CRMService.update_client_dynamic(
        client_id=input.client_id, fields={"Estado": input.estado}, ctx=ctx
    )


# =============================
# 🧩 SERVICIOS
# =============================
@function_tool
def get_all_services(wrapper: RunContextWrapper):
    ctx = wrapper.context
    return CatalogService.get_all_services(ctx=ctx)


@function_tool
def get_service_by_name(wrapper: RunContextWrapper, input: GetServiceByNameInput):
    ctx = wrapper.context
    return CatalogService.get_service_by_name(input.service_name, ctx=ctx)


# =============================
# 🗓️ DISPONIBILIDAD
# =============================
@function_tool
def calendar_check_availability(
    wrapper: RunContextWrapper, input: CalendarCheckAvailabilityInput
) -> Dict[str, Any]:
    logger.info("📅 [TOOL] calendar_check_availability llamada")
    ctx = wrapper.context

    days = input.days_ahead
    logger.info(f"📅 Consultando disponibilidad para los próximos {days} días")

    try:
        # NO pasar ctx, solo days_ahead
        result = CalendarService.check_availability(days_ahead=days)
    except Exception as e:
        logger.error(f"❌ [TOOL] Error consultando disponibilidad: {e}")
        return {"success": False, "error": str(e), "data": []}

    if not result:
        logger.info("⚠️ [TOOL] Sin disponibilidad encontrada")
        return {
            "success": True,
            "message": "No hay disponibilidad en los próximos días hábiles.",
            "data": [],
        }

    logger.info(f"✅ [TOOL] {len(result)} slots disponibles encontrados")
    return {"success": True, "data": result}


# =============================
# 🗓️ CREAR EVENTO
# =============================
@function_tool
def calendar_create_meet(wrapper: RunContextWrapper, input: CalendarCreateMeetInput):
    ctx = wrapper.context

    start_dt = _parse_iso_to_tz(input.start_time)
    end_dt = _parse_iso_to_tz(input.end_time)

    # Crear evento Calendar
    event = CalendarService.create_meet_event(
        summary=input.summary,
        start_time=start_dt,
        end_time=end_dt,
        attendees=input.attendees,
        description=input.description,
    )
    if not event.get("success"):
        return {"success": False, "error": event.get("error")}

    # Registrar en Sheets
    sheet = MeetingService.create_meeting(
        event_id=event["event_id"],
        asunto=event["summary"],
        fecha_inicio=event["start_time"],
        id_cliente=input.id_cliente,
        detalles=event.get("description"),
        meet_link=event.get("meet_link"),
        calendar_link=event.get("calendar_link"),
        estado="Programada",
        ctx=ctx,
    )

    return {"success": True, "calendar": event, "sheet": sheet}


# =============================
# 🗓️ ACTUALIZAR EVENTO
# =============================
@function_tool
def calendar_update_meet(wrapper: RunContextWrapper, input: CalendarUpdateMeetInput):
    ctx = wrapper.context

    meeting = MeetingService.get_meeting_by_id(input.event_id, ctx=ctx)
    if not meeting.get("success"):
        return {"success": False, "error": "Reunión no existe en Sheets"}

    start_dt = _parse_iso_to_tz(input.start_time)
    end_dt = _parse_iso_to_tz(input.end_time)

    updated = CalendarService.update_meet_event(
        event_id=input.event_id,
        summary=input.summary,
        start_time=start_dt,
        end_time=end_dt,
        attendees=input.attendees,
        description=input.description,
    )
    if not updated.get("success"):
        return {"success": False, "error": updated.get("error")}

    sheet = MeetingService.update_meeting(
        event_id=input.event_id,
        fields={
            "Asunto": input.summary,
            "Fecha Inicio": updated.get("start_time"),
            "Detalles": input.description,
            "Meet_Link": updated.get("meet_link"),
            "Calendar_Link": updated.get("calendar_link"),
            "Estado": "Reagendada",
        },
        ctx=ctx,
    )

    return {"success": True, "calendar": updated, "sheet": sheet}


# =============================
# 🗓️ DETALLES EVENTO
# =============================
@function_tool
def calendar_get_event_details(
    wrapper: RunContextWrapper, input: CalendarGetEventDetailsInput
):
    result = CalendarService.get_event_details(input.event_id)
    return {"success": True, "data": result}


# =============================
# 🗂️ SHEETS - REUNIONES
# =============================
@function_tool
def get_meetings_by_client(wrapper: RunContextWrapper, input: GetMeetingsByClientInput):
    ctx = wrapper.context
    return MeetingService.get_meetings_by_client(input.id_cliente, ctx=ctx)


@function_tool
def update_meeting_status(wrapper: RunContextWrapper, input: UpdateMeetingStatusInput):
    ctx = wrapper.context
    return MeetingService.update_meeting(
        event_id=input.meeting_id, fields={"Estado": input.estado}, ctx=ctx
    )


# =============================
# 📦 EXPORT
# =============================
ALL_TOOLS = [
    verify_client,
    create_client,
    update_client,
    update_client_note,
    update_client_status,
    get_all_services,
    get_service_by_name,
    calendar_check_availability,
    calendar_create_meet,
    calendar_update_meet,
    calendar_get_event_details,
    get_meetings_by_client,
    update_meeting_status,
]
