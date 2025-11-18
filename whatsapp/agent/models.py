"""
Modelos Pydantic para las herramientas del agente.
Cada modelo define el schema estricto requerido por OpenAI Agent SDK.
"""

from datetime import datetime
from typing import List, Optional, Union

from pydantic import BaseModel, Field, root_validator

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
    # Usamos datetime para que pydantic convierta ISO strings automáticamente
    start_time: datetime = Field(
        ..., description="Fecha/hora de inicio (ISO) — p.ej. 2025-11-17T14:00:00-05:00"
    )
    end_time: datetime = Field(
        ..., description="Fecha/hora de fin (ISO) — p.ej. 2025-11-17T15:00:00-05:00"
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
    start_time: datetime = Field(
        ...,
        description="Nueva fecha/hora de inicio (ISO) — p.ej. 2025-11-17T14:00:00-05:00",
    )
    end_time: datetime = Field(
        ...,
        description="Nueva fecha/hora de fin (ISO) — p.ej. 2025-11-17T15:00:00-05:00",
    )
    id_cliente: str = Field(..., description="ID del cliente asociado")
    attendees: Optional[List[str]] = Field(
        None, description="Lista de emails de participantes"
    )
    description: Optional[str] = Field(None, description="Nueva descripción")


class CalendarGetEventDetailsInput(BaseModel):
    """Input para obtener detalles de un evento."""

    event_id: str = Field(..., description="ID único del evento en Google Calendar")


class CalendarCheckAvailabilityInput(BaseModel):
    """Input para checkear disponibilidad."""

    days_ahead: int = Field(
        7, description="Número de días hacia adelante para buscar slots"
    )


# ====================================================
# 📊 MEETINGS MODELS
# ====================================================


class GetMeetingsByClientInput(BaseModel):
    """Input para consultar reuniones de un cliente."""

    id_cliente: str = Field(..., description="ID del cliente")


class UpdateMeetingStatusInput(BaseModel):
    """Input para actualizar el estado de una reunión.

    Se aceptan ambos nombres para evitar incompatibilidades entre
    herramientas: `meeting_id` (usado en algunos lugares) y `event_id`
    (usado en Google Calendar). Al menos uno debe ser provisto.
    """

    meeting_id: Optional[str] = Field(None, description="ID de la reunión (alias)")
    event_id: Optional[str] = Field(
        None, description="ID del evento en Google Calendar"
    )
    estado: str = Field(
        ...,
        description="Nuevo estado: Programada, Cancelada, Completada, Reagendada",
    )

    @root_validator(pre=True)
    def ensure_id_present(cls, values):
        mid = values.get("meeting_id")
        eid = values.get("event_id")
        if not mid and not eid:
            raise ValueError("Se requiere al menos meeting_id o event_id")
        return values

    def resolved_event_id(self) -> str:
        """Obtén el event_id preferido para pasar a las funciones internas."""
        return (
            self.event_id or self.meeting_id
        )  # preferir event_id, si no existe usar meeting_id


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
