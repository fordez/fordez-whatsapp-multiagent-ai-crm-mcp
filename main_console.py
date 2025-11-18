if __name__ == "__main__":
    import logging

    from whatsapp.agent.services.google_calendar_meet.calendar_service import (
        CalendarService,
    )

    logging.basicConfig(level=logging.DEBUG)  # ver logs detallados
    res = CalendarService.check_availability(days_ahead=7)
    print("Resultado check_availability:", res)
