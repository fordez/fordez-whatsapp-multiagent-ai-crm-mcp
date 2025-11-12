"""
Herramientas para agente de servicio al cliente.
Scope limitado por seguridad - solo operaciones esenciales.
Ahora todas las tools usan RunContextWrapper para manejar el contexto.
"""

from datetime import datetime
from typing import Any, Dict

from agents import RunContextWrapper, function_tool

# Importar modelos
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

# Importar servicios
from whatsapp.agent.services.google_calendar_meet.calendar_service import (
    CalendarService,
)
from whatsapp.agent.services.google_sheet.catalog_service import CatalogService
from whatsapp.agent.services.google_sheet.crm_service import CRMService
from whatsapp.agent.services.google_sheet.meeting_service import MeetingService
from whatsapp.agent.services.google_sheet.project_service import ProjectService

# ====================================================
# 🔧 CRM TOOLS
# ====================================================


@function_tool
def verify_client(ctx: RunContextWrapper, input: VerifyClientInput) -> Dict[str, Any]:
    """Verifica si un cliente existe en el CRM usando teléfono, correo o usuario."""
    return CRMService.verify_client(
        telefono=input.telefono,
        correo=input.correo,
        usuario=input.usuario,
        ctx=ctx.context,
    )


@function_tool
def create_client(ctx: RunContextWrapper, input: CreateClientInput) -> Dict[str, Any]:
    """Crea un nuevo cliente en el CRM."""
    result = CRMService.create_client_service(
        nombre=input.nombre,
        canal=input.canal,
        telefono=input.telefono,
        correo=input.correo,
        nota=input.nota,
        usuario=input.usuario,
        ctx=ctx.context,
    )
    return {
        "success": result.get("success", False),
        "created": result.get("created", False),
        "data": result,
    }


@function_tool
def update_client(ctx: RunContextWrapper, input: UpdateClientInput) -> Dict[str, Any]:
    """Actualiza información básica de un cliente (solo nombre, correo o usuario)."""
    fields = {}
    if input.nombre is not None:
        fields["Nombre"] = input.nombre
    if input.correo is not None:
        fields["Correo"] = input.correo
    if input.usuario is not None:
        fields["Usuario"] = input.usuario

    if not fields:
        return {
            "success": False,
            "error": "No se proporcionaron campos para actualizar",
        }

    result = CRMService.update_client_dynamic(
        client_id=input.client_id, fields=fields, ctx=ctx.context
    )
    return {"success": True, "data": result}


@function_tool
def update_client_note(
    ctx: RunContextWrapper, input: UpdateClientNoteInput
) -> Dict[str, Any]:
    """Actualiza la nota de un cliente existente."""
    result = CRMService.update_client_dynamic(
        client_id=input.client_id,
        fields={"Nota": input.nota},
        ctx=ctx.context,
    )
    return {"success": True, "data": result}


@function_tool
def update_client_status(
    ctx: RunContextWrapper, input: UpdateClientStatusInput
) -> Dict[str, Any]:
    """Actualiza el estado de un cliente."""
    result = CRMService.update_client_dynamic(
        client_id=input.client_id,
        fields={"Estado": input.estado},
        ctx=ctx.context,
    )
    return {"success": True, "data": result}


# ====================================================
# 📚 CATALOG TOOLS
# ====================================================


@function_tool
def get_all_services(ctx: RunContextWrapper) -> Dict[str, Any]:
    """Retorna todos los servicios disponibles en el catálogo."""
    return CatalogService.get_all_services(ctx=ctx.context)


@function_tool
def get_service_by_name(
    ctx: RunContextWrapper, input: GetServiceByNameInput
) -> Dict[str, Any]:
    """Busca un servicio específico por su nombre."""
    return CatalogService.get_service_by_name(input.service_name, ctx=ctx.context)


# ====================================================
# 📅 CALENDAR TOOLS
# ====================================================


@function_tool
def calendar_check_availability(ctx: RunContextWrapper) -> Dict[str, Any]:
    """Consulta disponibilidad de calendario para los próximos días hábiles."""
    result = CalendarService.check_availability()

    if not result:
        return {
            "success": True,
            "message": "No hay disponibilidad en los próximos días hábiles.",
            "data": [],
        }

    return {"success": True, "data": result}


@function_tool
def calendar_create_meet(
    ctx: RunContextWrapper, input: CalendarCreateMeetInput
) -> Dict[str, Any]:
    """Crea un evento de Google Calendar con Google Meet y lo registra en Google Sheet."""
    start_dt = datetime.fromisoformat(input.start_time)
    end_dt = datetime.fromisoformat(input.end_time)

    event_data = CalendarService.create_meet_event(
        summary=input.summary,
        start_time=start_dt,
        end_time=end_dt,
        attendees=input.attendees,
        description=input.description,
    )

    if not event_data.get("success"):
        return {"success": False, "error": event_data.get("error")}

    # Guardar evento en Sheets
    sheet_result = MeetingService.create_meeting(
        event_id=event_data["event_id"],
        asunto=event_data["summary"],
        fecha_inicio=event_data["start_time"],
        id_cliente=input.id_cliente,
        detalles=event_data.get("description"),
        meet_link=event_data.get("meet_link"),
        calendar_link=event_data.get("calendar_link"),
        estado=event_data.get("estado", "Programada"),
        ctx=ctx.context,
    )

    return {"success": sheet_result["success"], "data": sheet_result}


@function_tool
def calendar_update_meet(
    ctx: RunContextWrapper, input: CalendarUpdateMeetInput
) -> Dict[str, Any]:
    """Actualiza un evento de Google Calendar y actualiza el registro en Google Sheet."""
    start_dt = datetime.fromisoformat(input.start_time)
    end_dt = datetime.fromisoformat(input.end_time)

    # Actualizar evento en Google Calendar
    event_data = CalendarService.update_meet_event(
        event_id=input.event_id,
        summary=input.summary,
        start_time=start_dt,
        end_time=end_dt,
        attendees=input.attendees,
        description=input.description,
    )

    if not event_data.get("success"):
        return {"success": False, "error": event_data.get("error")}

    # Actualizar registro existente en Sheets
    sheet_result = MeetingService.update_meeting(
        event_id=input.event_id,
        fields={
            "Asunto": event_data["summary"],
            "Fecha Inicio": event_data["start_time"],
            "Detalles": event_data.get("description"),
            "Meet_Link": event_data.get("meet_link"),
            "Calendar_Link": event_data.get("calendar_link"),
            "Estado": "Reagendada",
        },
        ctx=ctx.context,
    )

    return {"success": sheet_result["success"], "data": sheet_result}


@function_tool
def calendar_get_event_details(
    ctx: RunContextWrapper, input: CalendarGetEventDetailsInput
) -> Dict[str, Any]:
    """Obtiene los detalles completos de un evento de calendario."""
    result = CalendarService.get_event_details(input.event_id)
    return {"success": True, "data": result}


# ====================================================
# 📊 MEETINGS TOOLS
# ====================================================


@function_tool
def get_meetings_by_client(
    ctx: RunContextWrapper, input: GetMeetingsByClientInput
) -> Dict[str, Any]:
    """Consulta todas las reuniones de un cliente."""
    return MeetingService.get_meetings_by_client(input.id_cliente, ctx=ctx.context)


@function_tool
def update_meeting_status(
    ctx: RunContextWrapper, input: UpdateMeetingStatusInput
) -> Dict[str, Any]:
    """Actualiza el estado de una reunión en Google Sheet."""
    return MeetingService.update_meeting(
        event_id=input.meeting_id, fields={"Estado": input.estado}, ctx=ctx.context
    )


# ====================================================
# 📁 PROJECTS TOOLS
# ====================================================


@function_tool
def get_projects_by_client(
    ctx: RunContextWrapper, input: GetProjectsByClientInput
) -> Dict[str, Any]:
    """Consulta todos los proyectos de un cliente."""
    return ProjectService.get_projects_by_client(input.id_cliente, ctx=ctx.context)


@function_tool
def update_project_note_by_client(
    ctx: RunContextWrapper, input: UpdateProjectNoteByClientInput
) -> Dict[str, Any]:
    """Actualiza la nota de todos los proyectos de un cliente."""
    return ProjectService.update_project_note_by_client(
        id_cliente=input.id_cliente, nota=input.nota, ctx=ctx.context
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
