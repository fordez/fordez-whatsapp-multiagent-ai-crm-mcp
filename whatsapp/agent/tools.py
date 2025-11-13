"""
Herramientas para agente de servicio al cliente.
Scope limitado por seguridad - solo operaciones esenciales.
Todas las tools pasan el contexto local mediante RunContextWrapper.
"""

from datetime import datetime
from typing import Any, Dict

import pytz
from agents import RunContextWrapper, function_tool

from whatsapp.agent.models import (
    CalendarCreateMeetInput,
    CalendarGetEventDetailsInput,
    CalendarUpdateMeetInput,
    CreateClientInput,
    GetMeetingsByClientInput,
    GetProjectsByClientInput,
    GetServiceByNameInput,
    UpdateClientInput,
    UpdateClientNoteInput,
    UpdateClientStatusInput,
    UpdateMeetingStatusInput,
    UpdateProjectNoteByClientInput,
    VerifyClientInput,
)
from whatsapp.agent.services.google_calendar_meet.calendar_service import (
    CalendarService,
)
from whatsapp.agent.services.google_sheet.catalog_service import CatalogService
from whatsapp.agent.services.google_sheet.crm_service import CRMService
from whatsapp.agent.services.google_sheet.meeting_service import MeetingService
from whatsapp.agent.services.google_sheet.project_service import ProjectService
from whatsapp.config import config

# ====================================================
# 🔧 CRM TOOLS
# ====================================================


@function_tool
def verify_client(
    wrapper: RunContextWrapper, input: VerifyClientInput
) -> Dict[str, Any]:
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
    return {
        "success": result.get("success", False),
        "created": result.get("created", False),
        "data": result,
    }


@function_tool
def update_client(
    wrapper: RunContextWrapper, input: UpdateClientInput
) -> Dict[str, Any]:
    ctx = wrapper.context
    fields = {
        k: v
        for k, v in [
            ("Nombre", input.nombre),
            ("Correo", input.correo),
            ("Usuario", input.usuario),
        ]
        if v is not None
    }

    if not fields:
        return {
            "success": False,
            "error": "No se proporcionaron campos para actualizar",
        }

    result = CRMService.update_client_dynamic(
        client_id=input.client_id, fields=fields, ctx=ctx
    )
    return {"success": True, "data": result}


@function_tool
def update_client_note(
    wrapper: RunContextWrapper, input: UpdateClientNoteInput
) -> Dict[str, Any]:
    ctx = wrapper.context
    result = CRMService.update_client_dynamic(
        client_id=input.client_id, fields={"Nota": input.nota}, ctx=ctx
    )
    return {"success": True, "data": result}


@function_tool
def update_client_status(
    wrapper: RunContextWrapper, input: UpdateClientStatusInput
) -> Dict[str, Any]:
    ctx = wrapper.context
    result = CRMService.update_client_dynamic(
        client_id=input.client_id, fields={"Estado": input.estado}, ctx=ctx
    )
    return {"success": True, "data": result}


# ====================================================
# 📚 CATALOG TOOLS
# ====================================================


@function_tool
def get_all_services(wrapper: RunContextWrapper) -> Dict[str, Any]:
    ctx = wrapper.context
    return CatalogService.get_all_services(ctx=ctx)


@function_tool
def get_service_by_name(
    wrapper: RunContextWrapper, input: GetServiceByNameInput
) -> Dict[str, Any]:
    ctx = wrapper.context
    return CatalogService.get_service_by_name(input.service_name, ctx=ctx)


# ====================================================
# 📅 CALENDAR TOOLS
# ====================================================


@function_tool
def calendar_check_availability(wrapper: RunContextWrapper) -> Dict[str, Any]:
    result = CalendarService.check_availability()
    if not result:
        return {
            "success": True,
            "message": "No hay disponibilidad en los próximos días hábiles.",
            "data": [],
        }
    return {"success": True, "data": result}


# 🆕 Crear nueva reunión
@function_tool
def calendar_create_meet(
    wrapper: RunContextWrapper, input: CalendarCreateMeetInput
) -> Dict[str, Any]:
    ctx = wrapper.context
    tz = pytz.timezone(config.timezone)

    start_dt = datetime.fromisoformat(input.start_time)
    end_dt = datetime.fromisoformat(input.end_time)
    if start_dt.tzinfo is None:
        start_dt = tz.localize(start_dt)
    if end_dt.tzinfo is None:
        end_dt = tz.localize(end_dt)

    try:
        event = CalendarService.create_meet_event(
            summary=input.summary,
            start_time=start_dt,
            end_time=end_dt,
            attendees=input.attendees,
            description=input.description,
        )
    except Exception as e:
        return {"success": False, "error": f"Error creando evento en Calendar: {e}"}

    if not event.get("success"):
        return {"success": False, "error": event.get("error")}

    # 🧾 Crear fila en Google Sheet
    sheet_result = MeetingService.create_meeting(
        event_id=event["event_id"],
        asunto=event["summary"],
        fecha_inicio=event["start_time"],
        id_cliente=input.id_cliente,
        detalles=event.get("description"),
        meet_link=event.get("meet_link"),
        calendar_link=event.get("calendar_link"),
        estado="Agendada",
        ctx=ctx,
    )

    return {
        "success": True,
        "data": {
            "calendar": event,
            "sheet": sheet_result,
            "message": "Reunión creada correctamente",
        },
    }


# 🔁 Actualizar reunión existente
@function_tool
def calendar_update_meet(
    wrapper: RunContextWrapper, input: CalendarUpdateMeetInput
) -> Dict[str, Any]:
    """
    Actualiza una reunión existente en Calendar y Google Sheet.
    Si la fecha cambia, libera la anterior y actualiza el mismo registro.
    """
    ctx = wrapper.context
    if not getattr(input, "event_id", None):
        return {"success": False, "error": "event_id es requerido para actualizar"}

    tz = pytz.timezone(config.timezone)
    start_dt = datetime.fromisoformat(input.start_time)
    end_dt = datetime.fromisoformat(input.end_time)
    if start_dt.tzinfo is None:
        start_dt = tz.localize(start_dt)
    if end_dt.tzinfo is None:
        end_dt = tz.localize(end_dt)

    try:
        updated_event = CalendarService.update_meet_event(
            event_id=input.event_id,
            summary=input.summary,
            start_time=start_dt,
            end_time=end_dt,
            attendees=input.attendees,
            description=input.description,
        )
    except Exception as e:
        return {
            "success": False,
            "error": f"Error actualizando evento en Calendar: {e}",
        }

    if not updated_event.get("success"):
        return {"success": False, "error": updated_event.get("error")}

    # 🔄 Actualiza en Google Sheet (no crea nueva fila)
    sheet_result = MeetingService.update_meeting(
        event_id=input.event_id,
        fields={
            "Asunto": input.summary,
            "Fecha Inicio": updated_event.get("start_time"),
            "Detalles": input.description,
            "Meet_Link": updated_event.get("meet_link"),
            "Calendar_Link": updated_event.get("calendar_link"),
            "Estado": "Reagendada",
        },
        ctx=ctx,
    )

    return {
        "success": True,
        "data": {
            "calendar": updated_event,
            "sheet": sheet_result,
            "message": "Reunión actualizada correctamente",
        },
    }


@function_tool
def calendar_get_event_details(
    wrapper: RunContextWrapper, input: CalendarGetEventDetailsInput
) -> Dict[str, Any]:
    result = CalendarService.get_event_details(input.event_id)
    return {"success": True, "data": result}


# ====================================================
# 📊 MEETINGS TOOLS
# ====================================================


@function_tool
def get_meetings_by_client(
    wrapper: RunContextWrapper, input: GetMeetingsByClientInput
) -> Dict[str, Any]:
    ctx = wrapper.context
    return MeetingService.get_meetings_by_client(input.id_cliente, ctx=ctx)


@function_tool
def update_meeting_status(
    wrapper: RunContextWrapper, input: UpdateMeetingStatusInput
) -> Dict[str, Any]:
    ctx = wrapper.context
    return MeetingService.update_meeting(
        event_id=input.meeting_id, fields={"Estado": input.estado}, ctx=ctx
    )


# ====================================================
# 📁 PROJECTS TOOLS
# ====================================================


@function_tool
def get_projects_by_client(
    wrapper: RunContextWrapper, input: GetProjectsByClientInput
) -> Dict[str, Any]:
    ctx = wrapper.context
    return ProjectService.get_projects_by_client(input.id_cliente, ctx=ctx)


@function_tool
def update_project_note_by_client(
    wrapper: RunContextWrapper, input: UpdateProjectNoteByClientInput
) -> Dict[str, Any]:
    ctx = wrapper.context
    return ProjectService.update_project_note_by_client(
        id_cliente=input.id_cliente, nota=input.nota, ctx=ctx
    )


# ====================================================
# 📋 LISTA DE TODAS LAS HERRAMIENTAS
# ====================================================

ALL_TOOLS = [
    # CRM
    verify_client,
    create_client,
    update_client,
    update_client_note,
    update_client_status,
    # Catalog
    get_all_services,
    get_service_by_name,
    # Calendar
    calendar_check_availability,
    calendar_create_meet,
    calendar_update_meet,
    calendar_get_event_details,
    # Meetings
    get_meetings_by_client,
    update_meeting_status,
    # Projects
    get_projects_by_client,
    update_project_note_by_client,
]
