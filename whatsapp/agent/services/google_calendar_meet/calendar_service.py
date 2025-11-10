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
    def update_meet_event(
        event_id,
        summary=None,
        start_time=None,
        end_time=None,
        attendees=None,
        description=None,
    ):
        """Actualiza un evento existente en Google Calendar."""
        service = CalendarService.get_service()
        tz = TIMEZONE

        try:
            # Obtener evento existente
            event = (
                service.events().get(calendarId="primary", eventId=event_id).execute()
            )

            def parse(dt):
                if isinstance(dt, datetime):
                    return dt if dt.tzinfo else tz.localize(dt)
                return tz.localize(datetime.fromisoformat(dt))

            # Actualizar solo los campos proporcionados
            if summary is not None:
                event["summary"] = summary
            if description is not None:
                event["description"] = description
            if start_time is not None:
                start_dt = parse(start_time)
                event["start"] = {
                    "dateTime": start_dt.isoformat(),
                    "timeZone": str(TIMEZONE),
                }
            if end_time is not None:
                end_dt = parse(end_time)
                event["end"] = {
                    "dateTime": end_dt.isoformat(),
                    "timeZone": str(TIMEZONE),
                }
            if attendees is not None:
                event["attendees"] = [{"email": e} for e in attendees]

            # Verificar disponibilidad si se cambian las fechas
            if start_time is not None and end_time is not None:
                start_dt = parse(start_time)
                end_dt = parse(end_time)

                freebusy_result = (
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
                busy_slots = freebusy_result["calendars"]["primary"].get("busy", [])
                # Filtrar el evento actual de los slots ocupados
                busy_slots = [s for s in busy_slots if s.get("id") != event_id]
                if busy_slots:
                    return {
                        "success": False,
                        "error": "Horario no disponible",
                        "busy_slots": busy_slots,
                    }

            # Actualizar evento
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
