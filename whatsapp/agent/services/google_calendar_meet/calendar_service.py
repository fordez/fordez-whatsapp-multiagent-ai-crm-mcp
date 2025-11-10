# whatsapp/agent/services/calendar_service.py
import os
from datetime import datetime, time, timedelta

import pytz
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from whatsapp.config import config

TIMEZONE = config.timezone
SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/calendar.readonly",
]


class CalendarService:
    _service = None

    @staticmethod
    def get_credentials():
        """Obtiene credenciales OAuth2 desde config."""
        creds_data = config.token_json
        creds = Credentials.from_authorized_user_info(creds_data, SCOPES)
        return creds

    @staticmethod
    def get_service():
        """Singleton del servicio autenticado."""
        if CalendarService._service is None:
            creds = CalendarService.get_credentials()
            CalendarService._service = build("calendar", "v3", credentials=creds)
        return CalendarService._service

    @staticmethod
    def create_meet_event(
        summary, start_time, end_time, attendees=None, description=None
    ):
        service = CalendarService.get_service()
        tz = TIMEZONE

        def parse(dt):
            if isinstance(dt, datetime):
                return dt if dt.tzinfo else tz.localize(dt)
            return tz.localize(datetime.fromisoformat(dt))

        start_time = parse(start_time)
        end_time = parse(end_time)

        freebusy_result = (
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
        busy_slots = freebusy_result["calendars"]["primary"].get("busy", [])
        if busy_slots:
            return {
                "success": False,
                "error": "Horario no disponible",
                "busy_slots": busy_slots,
            }

        event_body = {
            "summary": summary,
            "description": description or "Evento creado automáticamente con Meet.",
            "start": {"dateTime": start_time.isoformat(), "timeZone": str(TIMEZONE)},
            "end": {"dateTime": end_time.isoformat(), "timeZone": str(TIMEZONE)},
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
    def check_availability(days_ahead=3, start_hour=8, end_hour=17):
        service = CalendarService.get_service()
        tz = TIMEZONE
        now = datetime.now(tz)

        disponibilidad = []
        offset, dias = 0, 0

        while dias < days_ahead:
            date = now.date() + timedelta(days=offset)
            if date.weekday() >= 5:
                offset += 1
                continue

            start = tz.localize(datetime.combine(date, time(start_hour)))
            end = tz.localize(datetime.combine(date, time(end_hour)))

            result = (
                service.freebusy()
                .query(
                    body={
                        "timeMin": start.isoformat(),
                        "timeMax": end.isoformat(),
                        "items": [{"id": "primary"}],
                    }
                )
                .execute()
            )

            busy = result["calendars"]["primary"].get("busy", [])
            free_slots = []
            current = start

            for slot in busy:
                s = datetime.fromisoformat(slot["start"]).astimezone(tz)
                e = datetime.fromisoformat(slot["end"]).astimezone(tz)
                if current < s:
                    free_slots.append((current, s))
                current = max(current, e)
            if current < end:
                free_slots.append((current, end))

            slots = [
                {"inicio": s.isoformat(), "fin": e.isoformat()}
                for s, e in free_slots
                if (e - s).total_seconds() >= 900
            ]

            if slots:
                disponibilidad.append(
                    {"dia": date.isoformat(), "espacios_libres": slots}
                )
                dias += 1

            offset += 1

        return disponibilidad

    @staticmethod
    def get_event_details(event_id: str):
        service = CalendarService.get_service()
        tz = TIMEZONE

        try:
            event = (
                service.events().get(calendarId="primary", eventId=event_id).execute()
            )
            start = datetime.fromisoformat(event["start"]["dateTime"]).astimezone(tz)
            end = datetime.fromisoformat(event["end"]["dateTime"]).astimezone(tz)
            meet_link = (
                event.get("conferenceData", {}).get("entryPoints", [{}])[0].get("uri")
            )

            return {
                "success": True,
                "event_id": event["id"],
                "summary": event.get("summary"),
                "description": event.get("description"),
                "start": start.isoformat(),
                "end": end.isoformat(),
                "attendees": [a.get("email") for a in event.get("attendees", [])],
                "calendar_link": event.get("htmlLink"),
                "meet_link": meet_link,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
