"""
Modelos Pydantic para las herramientas del agente.
Cada modelo define el schema estricto requerido por OpenAI Agent SDK.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

# ====================================================
# 🔧 CRM MODELS
# ====================================================


class VerifyClientInput(BaseModel):
    """Input para verificar si un cliente existe."""

    telefono: Optional[str] = Field(None, description="Número de teléfono del cliente")
    correo: Optional[str] = Field(None, description="Email del cliente")
    usuario: Optional[str] = Field(None, description="Usuario del cliente")


class CreateClientInput(BaseModel):
    """Input para crear un nuevo cliente."""

    nombre: str = Field(..., description="Nombre completo del cliente (requerido)")
    canal: str = Field(
        ..., description="Canal de origen: WhatsApp, Email, Web, etc. (requerido)"
    )
    telefono: Optional[str] = Field(None, description="Número de teléfono del cliente")
    correo: Optional[str] = Field(None, description="Email del cliente")
    nota: Optional[str] = Field(None, description="Nota inicial sobre el cliente")
    usuario: Optional[str] = Field(None, description="Usuario asociado al cliente")


class UpdateClientInput(BaseModel):
    """Input para actualizar un cliente."""

    client_id: str = Field(
        ..., description="ID del cliente (UUID) o número de teléfono"
    )
    nombre: Optional[str] = Field(None, description="Nuevo nombre del cliente")
    telefono: Optional[str] = Field(None, description="Nuevo teléfono")
    correo: Optional[str] = Field(None, description="Nuevo correo")
    tipo: Optional[str] = Field(None, description="Nuevo tipo de cliente")
    estado: Optional[str] = Field(None, description="Nuevo estado del cliente")
    nota: Optional[str] = Field(None, description="Nueva nota")
    usuario: Optional[str] = Field(None, description="Nuevo usuario")
    canal: Optional[str] = Field(None, description="Nuevo canal")
    fecha_creacion: Optional[str] = Field(None, description="Fecha de creación")
    fecha_conversion: Optional[str] = Field(None, description="Fecha de conversión")
    thread_id: Optional[str] = Field(None, description="Thread ID")


class UpdateClientNoteInput(BaseModel):
    """Input para actualizar la nota de un cliente."""

    client_id: str = Field(
        ..., description="ID del cliente (UUID) o número de teléfono"
    )
    nota: str = Field(..., description="Nueva nota para el cliente")


class UpdateClientStatusInput(BaseModel):
    """Input para actualizar el estado de un cliente."""

    client_id: str = Field(
        ..., description="ID del cliente (UUID) o número de teléfono"
    )
    estado: str = Field(..., description="Nuevo estado: Nuevo, Activo, Inactivo, etc.")


# ====================================================
# 📚 CATALOG MODELS
# ====================================================


class GetServiceByNameInput(BaseModel):
    """Input para buscar un servicio por nombre."""

    service_name: str = Field(..., description="Nombre del servicio a buscar")


# ====================================================
# 📅 CALENDAR MODELS
# ====================================================


class CalendarCreateMeetInput(BaseModel):
    """Input para crear un evento de calendario con Google Meet."""

    summary: str = Field(..., description="Título de la reunión (requerido)")
    start_time: str = Field(
        ..., description="Fecha/hora de inicio en formato ISO (YYYY-MM-DD HH:MM:SS)"
    )
    end_time: str = Field(
        ..., description="Fecha/hora de fin en formato ISO (YYYY-MM-DD HH:MM:SS)"
    )
    id_cliente: str = Field(..., description="ID del cliente asociado (requerido)")
    attendees: Optional[List[str]] = Field(
        None, description="Lista de emails de participantes"
    )
    description: Optional[str] = Field(None, description="Descripción de la reunión")


class CalendarGetEventDetailsInput(BaseModel):
    """Input para obtener detalles de un evento."""

    event_id: str = Field(..., description="ID único del evento en Google Calendar")


# ====================================================
# 📊 MEETINGS MODELS
# ====================================================


class GetMeetingByIdInput(BaseModel):
    """Input para consultar una reunión por ID."""

    meeting_id: str = Field(..., description="ID único de la reunión")


class GetMeetingsByClientInput(BaseModel):
    """Input para consultar reuniones de un cliente."""

    id_cliente: str = Field(..., description="ID del cliente")


class GetMeetingsByDateInput(BaseModel):
    """Input para consultar reuniones por fecha."""

    fecha_inicio: str = Field(..., description="Fecha en formato YYYY-MM-DD")


class UpdateMeetingInput(BaseModel):
    """Input para actualizar una reunión."""

    meeting_id: str = Field(..., description="ID de la reunión")
    asunto: Optional[str] = Field(None, description="Nuevo asunto de la reunión")
    detalles: Optional[str] = Field(None, description="Nuevos detalles")
    fecha_inicio: Optional[str] = Field(None, description="Nueva fecha de inicio")
    meet_link: Optional[str] = Field(None, description="Nuevo link de Meet")
    calendar_link: Optional[str] = Field(None, description="Nuevo link de Calendar")
    estado: Optional[str] = Field(
        None, description="Nuevo estado: Programada, Completada, Cancelada"
    )
    id_cliente: Optional[str] = Field(None, description="Nuevo ID de cliente")


class DeleteMeetingInput(BaseModel):
    """Input para eliminar una reunión."""

    meeting_id: str = Field(..., description="ID de la reunión a eliminar")


# ====================================================
# 📁 PROJECTS MODELS
# ====================================================


class CreateProjectInput(BaseModel):
    """Input para crear un nuevo proyecto."""

    nombre: str = Field(..., description="Nombre del proyecto (requerido)")
    id_cliente: str = Field(..., description="ID del cliente asociado (requerido)")
    servicio: Optional[str] = Field(None, description="Servicio relacionado")
    descripcion: Optional[str] = Field(None, description="Descripción del proyecto")
    fecha_inicio: Optional[str] = Field(
        None, description="Fecha de inicio (YYYY-MM-DD HH:MM:SS)"
    )
    fecha_fin: Optional[str] = Field(None, description="Fecha estimada de finalización")
    estado: Optional[str] = Field(
        "En Progreso", description="Estado inicial del proyecto"
    )
    nota: Optional[str] = Field(None, description="Notas adicionales")


class GetProjectByIdInput(BaseModel):
    """Input para consultar un proyecto por ID."""

    project_id: str = Field(..., description="ID único del proyecto")


class GetProjectsByClientInput(BaseModel):
    """Input para consultar proyectos de un cliente."""

    id_cliente: str = Field(..., description="ID del cliente")


class GetProjectsByDateInput(BaseModel):
    """Input para consultar proyectos por fecha."""

    fecha_inicio: str = Field(..., description="Fecha en formato YYYY-MM-DD")


class UpdateProjectInput(BaseModel):
    """Input para actualizar un proyecto."""

    project_id: str = Field(..., description="ID del proyecto")
    nombre: Optional[str] = Field(None, description="Nuevo nombre del proyecto")
    descripcion: Optional[str] = Field(None, description="Nueva descripción")
    servicio: Optional[str] = Field(None, description="Nuevo servicio")
    estado: Optional[str] = Field(None, description="Nuevo estado")
    nota: Optional[str] = Field(None, description="Nueva nota")
    fecha_inicio: Optional[str] = Field(None, description="Nueva fecha de inicio")
    fecha_fin: Optional[str] = Field(None, description="Nueva fecha de fin")
    id_cliente: Optional[str] = Field(None, description="Nuevo ID de cliente")


class UpdateProjectNoteByClientInput(BaseModel):
    """Input para actualizar notas de proyectos de un cliente."""

    id_cliente: str = Field(..., description="ID del cliente")
    nota: str = Field(
        ..., description="Nueva nota para todos los proyectos del cliente"
    )


class DeleteProjectInput(BaseModel):
    """Input para eliminar un proyecto."""

    project_id: str = Field(..., description="ID del proyecto a eliminar")
