"""
Herramientas migradas desde MCP Server a OpenAI Agent SDK.
Todas las funciones usan modelos Pydantic para schemas estrictos.
"""

from datetime import datetime
from typing import Any, Dict

from agents import function_tool

from whatsapp.agent.services.google_calendar_meet.calendar_service import (
    CalendarService,
)
from whatsapp.agent.services.google_sheet.catalog_service import CatalogService
from whatsapp.agent.services.google_sheet.crm_service import CRMService
from whatsapp.agent.services.google_sheet.meeting_service import MeetingService
from whatsapp.agent.services.google_sheet.project_service import ProjectService

# Importar modelos
from whatsapp.agent.models import (
    # CRM
    VerifyClientInput,
    CreateClientInput,
    UpdateClientInput,
    UpdateClientNoteInput,
    UpdateClientStatusInput,
    # Catalog
    GetServiceByNameInput,
    # Calendar
    CalendarCreateMeetInput,
    CalendarGetEventDetailsInput,
    # Meetings
    GetMeetingByIdInput,
    GetMeetingsByClientInput,
    GetMeetingsByDateInput,
    UpdateMeetingInput,
    DeleteMeetingInput,
    # Projects
    CreateProjectInput,
    GetProjectByIdInput,
    GetProjectsByClientInput,
    GetProjectsByDateInput,
    UpdateProjectInput,
    UpdateProjectNoteByClientInput,
    DeleteProjectInput,
)


# ====================================================
# 🔧 CRM TOOLS
# ====================================================


@function_tool
def verify_client(input: VerifyClientInput) -> Dict[str, Any]:
    """Verifica si un cliente existe en el CRM usando teléfono, correo o usuario.

    Retorna información completa del cliente si existe, incluyendo ID, datos de contacto y fechas.
    """
    return CRMService.verify_client(
        telefono=input.telefono, correo=input.correo, usuario=input.usuario
    )


@function_tool
def create_client(input: CreateClientInput) -> Dict[str, Any]:
    """Crea un nuevo cliente en el CRM.

    Retorna el resultado de la creación con success, client_id y datos del cliente.
    """
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
    """Actualiza cualquier campo de un cliente existente.

    Retorna el resultado de la actualización con campos modificados.
    """
    # Construir diccionario de campos solo con valores no None
    fields = {}
    if input.nombre is not None:
        fields["Nombre"] = input.nombre
    if input.telefono is not None:
        fields["Telefono"] = input.telefono
    if input.correo is not None:
        fields["Correo"] = input.correo
    if input.tipo is not None:
        fields["Tipo"] = input.tipo
    if input.estado is not None:
        fields["Estado"] = input.estado
    if input.nota is not None:
        fields["Nota"] = input.nota
    if input.usuario is not None:
        fields["Usuario"] = input.usuario
    if input.canal is not None:
        fields["Canal"] = input.canal
    if input.fecha_creacion is not None:
        fields["Fecha Creacion"] = input.fecha_creacion
    if input.fecha_conversion is not None:
        fields["Fecha Conversion"] = input.fecha_conversion
    if input.thread_id is not None:
        fields["Thread_Id"] = input.thread_id

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
    """Crea un evento de Google Calendar con Google Meet incluido."""
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
def calendar_get_event_details(input: CalendarGetEventDetailsInput) -> Dict[str, Any]:
    """Obtiene los detalles completos de un evento de calendario."""
    result = CalendarService.get_event_details(input.event_id)
    return {"success": True, "data": result}


# ====================================================
# 📊 MEETINGS TOOLS
# ====================================================


@function_tool
def get_meeting_by_id(input: GetMeetingByIdInput) -> Dict[str, Any]:
    """Consulta una reunión específica por su ID."""
    return MeetingService.get_meeting_by_id(input.meeting_id)


@function_tool
def get_meetings_by_client(input: GetMeetingsByClientInput) -> Dict[str, Any]:
    """Consulta todas las reuniones de un cliente."""
    return MeetingService.get_meetings_by_client(input.id_cliente)


@function_tool
def get_meetings_by_date(input: GetMeetingsByDateInput) -> Dict[str, Any]:
    """Consulta reuniones programadas para una fecha específica."""
    return MeetingService.get_meetings_by_date(input.fecha_inicio)


@function_tool
def update_meeting(input: UpdateMeetingInput) -> Dict[str, Any]:
    """Actualiza campos de una reunión existente."""
    # Construir diccionario de campos solo con valores no None
    fields = {}
    if input.asunto is not None:
        fields["Asunto"] = input.asunto
    if input.detalles is not None:
        fields["Detalles"] = input.detalles
    if input.fecha_inicio is not None:
        fields["Fecha Inicio"] = input.fecha_inicio
    if input.meet_link is not None:
        fields["Meet_Link"] = input.meet_link
    if input.calendar_link is not None:
        fields["Calendar_Link"] = input.calendar_link
    if input.estado is not None:
        fields["Estado"] = input.estado
    if input.id_cliente is not None:
        fields["Id Cliente"] = input.id_cliente

    if not fields:
        return {
            "success": False,
            "error": "No se proporcionaron campos para actualizar",
        }

    return MeetingService.update_meeting(meeting_id=input.meeting_id, fields=fields)


@function_tool
def delete_meeting(input: DeleteMeetingInput) -> Dict[str, Any]:
    """Elimina una reunión de la base de datos."""
    return MeetingService.delete_meeting(input.meeting_id)


# ====================================================
# 📁 PROJECTS TOOLS
# ====================================================


@function_tool
def create_project(input: CreateProjectInput) -> Dict[str, Any]:
    """Crea un nuevo proyecto en el sistema."""
    return ProjectService.create_project(
        nombre=input.nombre,
        id_cliente=input.id_cliente,
        servicio=input.servicio,
        descripcion=input.descripcion,
        fecha_inicio=input.fecha_inicio,
        fecha_fin=input.fecha_fin,
        estado=input.estado,
        nota=input.nota,
    )


@function_tool
def get_project_by_id(input: GetProjectByIdInput) -> Dict[str, Any]:
    """Consulta un proyecto específico por su ID."""
    return ProjectService.get_project_by_id(input.project_id)


@function_tool
def get_projects_by_client(input: GetProjectsByClientInput) -> Dict[str, Any]:
    """Consulta todos los proyectos de un cliente."""
    return ProjectService.get_projects_by_client(input.id_cliente)


@function_tool
def get_projects_by_date(input: GetProjectsByDateInput) -> Dict[str, Any]:
    """Consulta proyectos que inician en una fecha específica."""
    return ProjectService.get_projects_by_date(input.fecha_inicio)


@function_tool
def update_project(input: UpdateProjectInput) -> Dict[str, Any]:
    """Actualiza campos de un proyecto existente."""
    # Construir diccionario de campos solo con valores no None
    fields = {}
    if input.nombre is not None:
        fields["Nombre"] = input.nombre
    if input.descripcion is not None:
        fields["Descripcion"] = input.descripcion
    if input.servicio is not None:
        fields["Servicio"] = input.servicio
    if input.estado is not None:
        fields["Estado"] = input.estado
    if input.nota is not None:
        fields["Nota"] = input.nota
    if input.fecha_inicio is not None:
        fields["Fecha_Inicio"] = input.fecha_inicio
    if input.fecha_fin is not None:
        fields["Fecha_Fin"] = input.fecha_fin
    if input.id_cliente is not None:
        fields["Id_Cliente"] = input.id_cliente

    if not fields:
        return {
            "success": False,
            "error": "No se proporcionaron campos para actualizar",
        }

    return ProjectService.update_project(project_id=input.project_id, fields=fields)


@function_tool
def update_project_note_by_client(
    input: UpdateProjectNoteByClientInput,
) -> Dict[str, Any]:
    """Actualiza la nota de todos los proyectos de un cliente."""
    return ProjectService.update_project_note_by_client(
        id_cliente=input.id_cliente, nota=input.nota
    )


@function_tool
def delete_project(input: DeleteProjectInput) -> Dict[str, Any]:
    """Elimina un proyecto del sistema."""
    return ProjectService.delete_project(input.project_id)


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
    calendar_get_event_details,
    # Meetings
    get_meeting_by_id,
    get_meetings_by_client,
    get_meetings_by_date,
    update_meeting,
    delete_meeting,
    # Projects
    create_project,
    get_project_by_id,
    get_projects_by_client,
    get_projects_by_date,
    update_project,
    update_project_note_by_client,
    delete_project,
]
