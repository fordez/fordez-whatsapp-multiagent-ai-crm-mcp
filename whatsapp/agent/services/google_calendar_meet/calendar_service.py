# whatsapp/agent/services/google_calendar_meet/calendar_service.py

import json
import os
from datetime import datetime, time, timedelta

import pytz
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from whatsapp.config import config

# ===============================
# ⚙️ CONFIGURACIÓN
# ===============================
TIMEZONE = config.timezone
SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/calendar.readonly",
]


class CalendarService:
    _service = None

    # ====================================================
    # 🔐 AUTENTICACIÓN
    # ====================================================
    @staticmethod
    def get_credentials():
        """Obtiene credenciales OAuth2 desde config y refresca automáticamente si es necesario."""
        creds_data = config.token_json
        creds = Credentials.from_authorized_user_info(creds_data, SCOPES)

        # Refrescar token si ha expirado
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
                            "scopes": creds.scopes,
                        },
                        f,
                        indent=2,
                    )

                # Actualizar también en config en memoria
                config.token_json = {
                    "token": creds.token,
                    "refresh_token": creds.refresh_token,
                    "token_uri": creds.token_uri,
                    "client_id": creds.client_id,
                    "client_secret": creds.client_secret,
                    "scopes": creds.scopes,
                }

                print("✅ Token de Google Calendar refrescado y guardado correctamente")
            except Exception as e:
                print(f"⚠️ Error refrescando token: {e}")

        return creds

    @staticmethod
    def get_service():
        """Singleton del servicio autenticado."""
        if CalendarService._service is None:
            creds = CalendarService.get_credentials()
            CalendarService._service = build("calendar", "v3", credentials=creds)
        return CalendarService._service

    # ====================================================
    # 🆕 CREAR EVENTO
    # ====================================================
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

        # Convertir fechas al timezone definido
        start_time = parse(start_time)
        end_time = parse(end_time)

        # Verificar disponibilidad antes de crear
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
            "estado": "Agendada",
        }

    # ====================================================
    # 🔁 ACTUALIZAR EVENTO
    # ====================================================
    @staticmethod
    def update_meet_event(
        event_id,
        summary=None,
        start_time=None,
        end_time=None,
        attendees=None,
        description=None,
    ):
        """Actualiza un evento existente en Google Calendar y devuelve la nueva información."""
        service = CalendarService.get_service()
        tz = TIMEZONE

        try:
            event = (
                service.events().get(calendarId="primary", eventId=event_id).execute()
            )

            def parse(dt):
                if isinstance(dt, datetime):
                    return dt if dt.tzinfo else tz.localize(dt)
                return tz.localize(datetime.fromisoformat(dt))

            # Actualizar campos
            if summary:
                event["summary"] = summary
            if description:
                event["description"] = description

            start_dt = (
                parse(start_time)
                if start_time
                else datetime.fromisoformat(event["start"]["dateTime"]).astimezone(tz)
            )
            end_dt = (
                parse(end_time)
                if end_time
                else datetime.fromisoformat(event["end"]["dateTime"]).astimezone(tz)
            )

            event["start"] = {"dateTime": start_dt.isoformat(), "timeZone": str(tz)}
            event["end"] = {"dateTime": end_dt.isoformat(), "timeZone": str(tz)}

            if attendees is not None:
                event["attendees"] = [{"email": e} for e in attendees]

            # Verificar disponibilidad (evita doble booking)
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
            busy_slots = [s for s in busy_slots if s.get("id") != event_id]
            if busy_slots:
                return {
                    "success": False,
                    "error": "Horario no disponible para reagendar",
                    "busy_slots": busy_slots,
                }

            # Actualizar evento
            updated_event = (
                service.events()
                .update(
                    calendarId="primary",
                    eventId=event_id,
                    body=event,
                    conferenceDataVersion=1,
                )
                .execute()
            )

            meet_link = (
                updated_event.get("conferenceData", {})
                .get("entryPoints", [{}])[0]
                .get("uri")
            )

            # Fechas finales convertidas al timezone local
            start_final = datetime.fromisoformat(
                updated_event["start"]["dateTime"]
            ).astimezone(tz)
            end_final = datetime.fromisoformat(
                updated_event["end"]["dateTime"]
            ).astimezone(tz)

            return {
                "success": True,
                "event_id": updated_event["id"],
                "summary": updated_event.get("summary"),
                "description": updated_event.get("description"),
                "start_time": start_final.isoformat(),
                "end_time": end_final.isoformat(),
                "attendees": [
                    a.get("email") for a in updated_event.get("attendees", [])
                ],
                "calendar_link": updated_event.get("htmlLink"),
                "meet_link": meet_link,
                "estado": "Reagendada",  # ✅ Aquí se fija explícitamente
            }

        except Exception as e:
            return {"success": False, "error": f"Error al actualizar: {e}"}

    # ====================================================
    # 📅 DISPONIBILIDAD
    # ====================================================
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

    # ====================================================
    # 🔍 DETALLES DE EVENTO
    # ====================================================
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
