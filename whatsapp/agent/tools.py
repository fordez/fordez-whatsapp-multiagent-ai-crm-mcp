"""
Herramientas para agente de servicio al cliente.
Scope limitado por seguridad - solo operaciones esenciales.
"""

from datetime import datetime
from typing import Any, Dict

from agents import function_tool

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
def verify_client(input: VerifyClientInput) -> Dict[str, Any]:
    """Verifica si un cliente existe en el CRM usando teléfono, correo o usuario."""
    return CRMService.verify_client(
        telefono=input.telefono, correo=input.correo, usuario=input.usuario
    )


@function_tool
def create_client(input: CreateClientInput) -> Dict[str, Any]:
    """Crea un nuevo cliente en el CRM."""
    result = CRMService.create_client_service(
        nombre=input.nombre,
        canal=input.canal,
        telefono=input.telefono,
        correo=input.correo,
        nota=input.nota,
        usuario=input.usuario,
    )
    return {
        "success": result.get("success", False),
        "created": result.get("created", False),
        "data": result,
    }


@function_tool
def update_client(input: UpdateClientInput) -> Dict[str, Any]:
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

    result = CRMService.update_client_dynamic(client_id=input.client_id, fields=fields)
    return {"success": True, "data": result}


@function_tool
def update_client_note(input: UpdateClientNoteInput) -> Dict[str, Any]:
    """Actualiza la nota de un cliente existente."""
    result = CRMService.update_client_dynamic(
        client_id=input.client_id, fields={"Nota": input.nota}
    )
    return {"success": True, "data": result}


@function_tool
def update_client_status(input: UpdateClientStatusInput) -> Dict[str, Any]:
    """Actualiza el estado de un cliente."""
    result = CRMService.update_client_dynamic(
        client_id=input.client_id, fields={"Estado": input.estado}
    )
    return {"success": True, "data": result}


# ====================================================
# 📚 CATALOG TOOLS
# ====================================================


@function_tool
def get_all_services() -> Dict[str, Any]:
    """Retorna todos los servicios disponibles en el catálogo."""
    return CatalogService.get_all_services()


@function_tool
def get_service_by_name(input: GetServiceByNameInput) -> Dict[str, Any]:
    """Busca un servicio específico por su nombre."""
    return CatalogService.get_service_by_name(input.service_name)


# ====================================================
# 📅 CALENDAR TOOLS
# ====================================================


@function_tool
def calendar_check_availability() -> Dict[str, Any]:
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
def calendar_create_meet(input: CalendarCreateMeetInput) -> Dict[str, Any]:
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
    )

    return {"success": sheet_result["success"], "data": sheet_result}


@function_tool
def calendar_update_meet(input: CalendarUpdateMeetInput) -> Dict[str, Any]:
    """Actualiza un evento de Google Calendar (fecha/hora) y crea nuevo registro en Google Sheet."""
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

    # Crear nuevo registro en Sheets (mantiene historial)
    sheet_result = MeetingService.create_meeting(
        event_id=event_data["event_id"],
        asunto=event_data["summary"],
        fecha_inicio=event_data["start_time"],
        id_cliente=input.id_cliente,
        detalles=event_data.get("description"),
        meet_link=event_data.get("meet_link"),
        calendar_link=event_data.get("calendar_link"),
        estado="Reagendada",
    )

    return {"success": sheet_result["success"], "data": sheet_result}


@function_tool
def calendar_get_event_details(input: CalendarGetEventDetailsInput) -> Dict[str, Any]:
    """Obtiene los detalles completos de un evento de calendario."""
    result = CalendarService.get_event_details(input.event_id)
    return {"success": True, "data": result}


# ====================================================
# 📊 MEETINGS TOOLS
# ====================================================


@function_tool
def get_meetings_by_client(input: GetMeetingsByClientInput) -> Dict[str, Any]:
    """Consulta todas las reuniones de un cliente."""
    return MeetingService.get_meetings_by_client(input.id_cliente)


@function_tool
def update_meeting_status(input: UpdateMeetingStatusInput) -> Dict[str, Any]:
    """Actualiza el estado de una reunión en Google Sheet."""
    return MeetingService.update_meeting(
        meeting_id=input.meeting_id, fields={"Estado": input.estado}
    )


# ====================================================
# 📁 PROJECTS TOOLS
# ====================================================


@function_tool
def get_projects_by_client(input: GetProjectsByClientInput) -> Dict[str, Any]:
    """Consulta todos los proyectos de un cliente."""
    return ProjectService.get_projects_by_client(input.id_cliente)


@function_tool
def update_project_note_by_client(
    input: UpdateProjectNoteByClientInput,
) -> Dict[str, Any]:
    """Actualiza la nota de todos los proyectos de un cliente."""
    return ProjectService.update_project_note_by_client(
        id_cliente=input.id_cliente, nota=input.nota
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
