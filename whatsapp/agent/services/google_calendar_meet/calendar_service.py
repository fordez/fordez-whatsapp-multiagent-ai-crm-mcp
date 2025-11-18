import json
import logging
import os
from datetime import datetime, timedelta

import pytz
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from whatsapp.config import config

# 🔧 Logger
logger = logging.getLogger("whatsapp.calendar")

# 🕒 Asegurar timezone válido
TIMEZONE = config.timezone
if not isinstance(TIMEZONE, pytz.BaseTzInfo):
    TIMEZONE = pytz.timezone(str(TIMEZONE))

SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/calendar.readonly",
]

WORK_HOUR_START = 8
WORK_HOUR_END = 17


class CalendarService:
    _service = None

    @staticmethod
    def get_credentials():
        creds_data = config.token_json
        creds = Credentials.from_authorized_user_info(creds_data, SCOPES)

        if creds.expired and creds.refresh_token:
            try:
                logger.info("🔄 Refrescando token de Google Calendar...")
                creds.refresh(Request())
                token_file = getattr(
                    config,
                    "token_file",
                    os.getenv("TOKEN_FILE", "secrets/token-dev.json"),
                )
                os.makedirs(os.path.dirname(token_file), exist_ok=True)
                with open(token_file, "w") as f:
                    json.dump(
                        {
                            "token": creds.token,
                            "refresh_token": creds.refresh_token,
                            "token_uri": creds.token_uri,
                            "client_id": creds.client_id,
                            "client_secret": creds.client_secret,
                            "scopes": list(creds.scopes),
                        },
                        f,
                        indent=2,
                    )
                config.token_json = {
                    "token": creds.token,
                    "refresh_token": creds.refresh_token,
                    "token_uri": creds.token_uri,
                    "client_id": creds.client_id,
                    "client_secret": creds.client_secret,
                    "scopes": list(creds.scopes),
                }
                logger.info("✅ Token de Google Calendar refrescado correctamente")
            except Exception as e:
                logger.error(f"❌ Error refrescando token: {e}")
                raise

        return creds

    @staticmethod
    def get_service():
        if CalendarService._service is None:
            creds = CalendarService.get_credentials()
            CalendarService._service = build("calendar", "v3", credentials=creds)
            logger.info("✅ Servicio de Google Calendar inicializado")
        return CalendarService._service

    @staticmethod
    def _ensure_dt(dt):
        """Convierte ISO string o datetime a datetime timezone-aware."""
        tz = TIMEZONE
        if isinstance(dt, datetime):
            d = dt
        else:
            d = datetime.fromisoformat(str(dt).replace("Z", "+00:00"))
        if d.tzinfo is None:
            d = tz.localize(d)
        else:
            d = d.astimezone(tz)
        return d

    @staticmethod
    def _format_datetime_readable(dt):
        """Convierte datetime a formato legible: 'Lunes 17 de Noviembre, 2025 a las 14:30'"""
        dt = CalendarService._ensure_dt(dt)
        days = [
            "Lunes",
            "Martes",
            "Miércoles",
            "Jueves",
            "Viernes",
            "Sábado",
            "Domingo",
        ]
        months = [
            "Enero",
            "Febrero",
            "Marzo",
            "Abril",
            "Mayo",
            "Junio",
            "Julio",
            "Agosto",
            "Septiembre",
            "Octubre",
            "Noviembre",
            "Diciembre",
        ]

        day_name = days[dt.weekday()]
        month_name = months[dt.month - 1]
        return f"{day_name} {dt.day} de {month_name}, {dt.year} a las {dt.strftime('%H:%M')}"

    @staticmethod
    def check_availability(days_ahead=7):
        try:
            logger.info("🔍 Verificando disponibilidad en calendario...")
            service = CalendarService.get_service()
            tz = TIMEZONE
            now = datetime.now(tz)
            time_min = now
            time_max = now + timedelta(days=days_ahead)

            fb = (
                service.freebusy()
                .query(
                    body={
                        "timeMin": time_min.isoformat(),
                        "timeMax": time_max.isoformat(),
                        "items": [{"id": "primary"}],
                    }
                )
                .execute()
            )

            busy_slots = fb["calendars"]["primary"].get("busy", [])
            available_slots = []

            current_day = time_min.replace(
                hour=WORK_HOUR_START, minute=0, second=0, microsecond=0
            )

            while current_day < time_max:
                if current_day.weekday() < 5:
                    for hour in range(WORK_HOUR_START, WORK_HOUR_END):
                        slot_start = current_day.replace(hour=hour)
                        slot_end = slot_start + timedelta(hours=1)

                        if slot_start <= now:
                            continue

                        is_free = True
                        for busy in busy_slots:
                            busy_start = CalendarService._ensure_dt(busy["start"])
                            busy_end = CalendarService._ensure_dt(busy["end"])
                            if slot_start < busy_end and slot_end > busy_start:
                                is_free = False
                                break

                        if is_free:
                            available_slots.append(
                                {
                                    "start": slot_start.isoformat(),
                                    "end": slot_end.isoformat(),
                                    "readable": f"{CalendarService._format_datetime_readable(slot_start)} - {slot_end.strftime('%H:%M')}",
                                }
                            )

                current_day += timedelta(days=1)
                current_day = current_day.replace(
                    hour=WORK_HOUR_START, minute=0, second=0, microsecond=0
                )

            logger.info(f"✅ {len(available_slots)} slots disponibles encontrados")
            return available_slots[:20]

        except Exception as e:
            logger.error(f"❌ Error verificando disponibilidad: {e}")
            return []

    @staticmethod
    def get_event_details(event_id):
        try:
            service = CalendarService.get_service()
            event = (
                service.events().get(calendarId="primary", eventId=event_id).execute()
            )

            start_dt = CalendarService._ensure_dt(event["start"]["dateTime"])
            end_dt = CalendarService._ensure_dt(event["end"]["dateTime"])

            meet_link = (
                event.get("conferenceData", {}).get("entryPoints", [{}])[0].get("uri")
            )

            return {
                "success": True,
                "event_id": event["id"],
                "summary": event.get("summary"),
                "description": event.get("description"),
                "start_time": start_dt.isoformat(),
                "end_time": end_dt.isoformat(),
                "start_readable": CalendarService._format_datetime_readable(start_dt),
                "end_readable": CalendarService._format_datetime_readable(end_dt),
                "attendees": [a.get("email") for a in event.get("attendees", [])],
                "calendar_link": event.get("htmlLink"),
                "meet_link": meet_link,
                "status": event.get("status"),
            }

        except Exception as e:
            logger.error(f"❌ Error obteniendo detalles del evento: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def create_meet_event(
        summary, start_time, end_time, attendees=None, description=None
    ):
        try:
            service = CalendarService.get_service()
            tz = TIMEZONE

            start_time = CalendarService._ensure_dt(start_time)
            end_time = CalendarService._ensure_dt(end_time)
            now = datetime.now(tz)

            if start_time < now - timedelta(minutes=1):
                return {
                    "success": False,
                    "error": "No se puede crear evento en el pasado",
                }

            fb = (
                service.freebusy()
                .query(
                    body={
                        "timeMin": start_time.isoformat(),
                        "timeMax": end_time.isoformat(),
                        "items": [{"id": "primary"}],
                    }
                )
                .execute()
            )
            busy_slots = fb["calendars"]["primary"].get("busy", [])
            if busy_slots:
                return {
                    "success": False,
                    "error": "Horario no disponible",
                    "busy_slots": busy_slots,
                }

            event_body = {
                "summary": summary,
                "description": description or "Evento creado automáticamente con Meet.",
                "start": {"dateTime": start_time.isoformat(), "timeZone": str(tz)},
                "end": {"dateTime": end_time.isoformat(), "timeZone": str(tz)},
                "conferenceData": {
                    "createRequest": {
                        "requestId": f"meet-{os.urandom(4).hex()}",
                        "conferenceSolutionKey": {"type": "hangoutsMeet"},
                    }
                },
                "attendees": [{"email": e} for e in (attendees or [])],
            }

            created_event = (
                service.events()
                .insert(calendarId="primary", body=event_body, conferenceDataVersion=1)
                .execute()
            )

            meet_link = (
                created_event.get("conferenceData", {})
                .get("entryPoints", [{}])[0]
                .get("uri")
            )
            start_final = CalendarService._ensure_dt(created_event["start"]["dateTime"])
            end_final = CalendarService._ensure_dt(created_event["end"]["dateTime"])

            return {
                "success": True,
                "event_id": created_event["id"],
                "summary": created_event.get("summary"),
                "description": created_event.get("description"),
                "start_time": start_final.isoformat(),
                "end_time": end_final.isoformat(),
                "start_readable": CalendarService._format_datetime_readable(
                    start_final
                ),
                "end_readable": CalendarService._format_datetime_readable(end_final),
                "attendees": [
                    a.get("email") for a in created_event.get("attendees", [])
                ],
                "calendar_link": created_event.get("htmlLink"),
                "meet_link": meet_link,
                "estado": "Programada",
            }

        except Exception as e:
            logger.error(f"❌ Error creando evento: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def update_meet_event(
        event_id,
        summary=None,
        start_time=None,
        end_time=None,
        attendees=None,
        description=None,
    ):
        try:
            service = CalendarService.get_service()
            tz = TIMEZONE

            event = (
                service.events().get(calendarId="primary", eventId=event_id).execute()
            )

            if summary is not None:
                event["summary"] = summary
            if description is not None:
                event["description"] = description

            start_dt = CalendarService._ensure_dt(start_time) if start_time else None
            end_dt = CalendarService._ensure_dt(end_time) if end_time else None

            if start_dt:
                event["start"] = {"dateTime": start_dt.isoformat(), "timeZone": str(tz)}
            if end_dt:
                event["end"] = {"dateTime": end_dt.isoformat(), "timeZone": str(tz)}
            if attendees:
                event["attendees"] = [{"email": e} for e in attendees]

            now = datetime.now(tz)
            if start_dt and start_dt < now - timedelta(minutes=1):
                return {
                    "success": False,
                    "error": "No se puede reagendar a una fecha pasada",
                }

            if start_dt and end_dt:
                fb = (
                    service.freebusy()
                    .query(
                        body={
                            "timeMin": start_dt.isoformat(),
                            "timeMax": end_dt.isoformat(),
                            "items": [{"id": "primary"}],
                        }
                    )
                    .execute()
                )
                busy_slots = fb["calendars"]["primary"].get("busy", [])
                busy_slots = [
                    slot
                    for slot in busy_slots
                    if not (
                        CalendarService._ensure_dt(slot["start"]) == start_dt
                        and CalendarService._ensure_dt(slot["end"]) == end_dt
                    )
                ]
                if busy_slots:
                    return {
                        "success": False,
                        "error": "Horario no disponible",
                        "busy_slots": busy_slots,
                    }

            updated_event = (
                service.events()
                .update(calendarId="primary", eventId=event_id, body=event)
                .execute()
            )
            meet_link = (
                updated_event.get("conferenceData", {})
                .get("entryPoints", [{}])[0]
                .get("uri")
            )
            start_final = CalendarService._ensure_dt(updated_event["start"]["dateTime"])
            end_final = CalendarService._ensure_dt(updated_event["end"]["dateTime"])

            return {
                "success": True,
                "event_id": updated_event["id"],
                "summary": updated_event.get("summary"),
                "description": updated_event.get("description"),
                "start_time": start_final.isoformat(),
                "end_time": end_final.isoformat(),
                "start_readable": CalendarService._format_datetime_readable(
                    start_final
                ),
                "end_readable": CalendarService._format_datetime_readable(end_final),
                "attendees": [
                    a.get("email") for a in updated_event.get("attendees", [])
                ],
                "calendar_link": updated_event.get("htmlLink"),
                "meet_link": meet_link,
                "estado": "Reagendada",
            }

        except Exception as e:
            logger.error(f"❌ Error actualizando evento: {e}")
            return {"success": False, "error": str(e)}
