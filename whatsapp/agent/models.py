"""
Modelos Pydantic para las herramientas del agente.
Cada modelo define el schema estricto requerido por OpenAI Agent SDK.
"""

from typing import List, Optional

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
    """Input para actualizar información básica de un cliente (solo nombre, correo, usuario)."""

    client_id: str = Field(
        ..., description="ID del cliente (UUID) o número de teléfono"
    )
    nombre: Optional[str] = Field(None, description="Nuevo nombre del cliente")
    correo: Optional[str] = Field(None, description="Nuevo correo")
    usuario: Optional[str] = Field(None, description="Nuevo usuario")


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


class CalendarUpdateMeetInput(BaseModel):
    """Input para actualizar un evento de calendario existente."""

    event_id: str = Field(..., description="ID del evento en Google Calendar")
    summary: Optional[str] = Field(None, description="Nuevo título de la reunión")
    start_time: str = Field(
        ...,
        description="Nueva fecha/hora de inicio en formato ISO (YYYY-MM-DD HH:MM:SS)",
    )
    end_time: str = Field(
        ..., description="Nueva fecha/hora de fin en formato ISO (YYYY-MM-DD HH:MM:SS)"
    )
    id_cliente: str = Field(..., description="ID del cliente asociado")
    attendees: Optional[List[str]] = Field(
        None, description="Lista de emails de participantes"
    )
    description: Optional[str] = Field(None, description="Nueva descripción")


class CalendarGetEventDetailsInput(BaseModel):
    """Input para obtener detalles de un evento."""

    event_id: str = Field(..., description="ID único del evento en Google Calendar")


# ====================================================
# 📊 MEETINGS MODELS
# ====================================================


class GetMeetingsByClientInput(BaseModel):
    """Input para consultar reuniones de un cliente."""

    id_cliente: str = Field(..., description="ID del cliente")


class UpdateMeetingStatusInput(BaseModel):
    """Input para actualizar el estado de una reunión."""

    meeting_id: str = Field(..., description="ID de la reunión (event_id)")
    estado: str = Field(
        ...,
        description="Nuevo estado: Programada, Cancelada, Completada, Reagendada",
    )


# ====================================================
# 📁 PROJECTS MODELS
# ====================================================


class GetProjectsByClientInput(BaseModel):
    """Input para consultar proyectos de un cliente."""

    id_cliente: str = Field(..., description="ID del cliente")


class UpdateProjectNoteByClientInput(BaseModel):
    """Input para actualizar notas de proyectos de un cliente."""

    id_cliente: str = Field(..., description="ID del cliente")
    nota: str = Field(
        ..., description="Nueva nota para todos los proyectos del cliente"
    )
