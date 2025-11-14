import json
import os
from datetime import datetime, time, timedelta

import pytz
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from whatsapp.config import config

# 🕒 Asegurar timezone válido
TIMEZONE = config.timezone
if not isinstance(TIMEZONE, pytz.BaseTzInfo):
    TIMEZONE = pytz.timezone(str(TIMEZONE))

SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/calendar.readonly",
]


class CalendarService:
    _service = None

    @staticmethod
    def get_credentials():
        creds_data = config.token_json
        creds = Credentials.from_authorized_user_info(creds_data, SCOPES)

        if creds.expired and creds.refresh_token:
            try:
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
                print("✅ Token de Google Calendar refrescado y guardado correctamente")
            except Exception as e:
                print(f"⚠️ Error refrescando token: {e}")

        return creds

    @staticmethod
    def get_service():
        if CalendarService._service is None:
            creds = CalendarService.get_credentials()
            CalendarService._service = build("calendar", "v3", credentials=creds)
        return CalendarService._service

    @staticmethod
    def _ensure_dt(dt):
        """Convierte ISO string o datetime a datetime timezone-aware."""
        tz = TIMEZONE
        if isinstance(dt, datetime):
            d = dt
        else:
            d = datetime.fromisoformat(str(dt))
        if d.tzinfo is None:
            d = tz.localize(d)
        else:
            d = d.astimezone(tz)
        return d

    @staticmethod
    def create_meet_event(
        summary, start_time, end_time, attendees=None, description=None
    ):
        service = CalendarService.get_service()
        tz = TIMEZONE

        start_time = CalendarService._ensure_dt(start_time)
        end_time = CalendarService._ensure_dt(end_time)

        now = datetime.now(tz)

        # ✅ permitir 1 minuto de tolerancia para diferencias de reloj
        if start_time < now - timedelta(minutes=1):
            return {"success": False, "error": "No se puede crear evento en el pasado"}

        # Verificar disponibilidad
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

        return {
            "success": True,
            "event_id": created_event["id"],
            "summary": created_event.get("summary"),
            "description": created_event.get("description"),
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "attendees": [a.get("email") for a in created_event.get("attendees", [])],
            "calendar_link": created_event.get("htmlLink"),
            "meet_link": meet_link,
            "estado": "Programada",
        }

    @staticmethod
    def update_meet_event(
        event_id,
        summary=None,
        start_time=None,
        end_time=None,
        attendees=None,
        description=None,
    ):
        service = CalendarService.get_service()
        tz = TIMEZONE

        try:
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

            # Comprobar disponibilidad
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

            return {
                "success": True,
                "event_id": updated_event["id"],
                "summary": updated_event.get("summary"),
                "description": updated_event.get("description"),
                "start_time": updated_event["start"]["dateTime"],
                "end_time": updated_event["end"]["dateTime"],
                "attendees": [
                    a.get("email") for a in updated_event.get("attendees", [])
                ],
                "calendar_link": updated_event.get("htmlLink"),
                "meet_link": meet_link,
                "estado": "Reagendada",
            }

        except Exception as e:
            return {"success": False, "error": str(e)}
