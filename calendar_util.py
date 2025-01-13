from datetime import datetime, timedelta
from auth import get_authenticated_service

def fetch_events_for_next_week():
    service = get_authenticated_service()
    now = datetime.utcnow()
    one_week_later = now + timedelta(days=7)

    events_result = service.events().list(
        calendarId='primary',
        timeMin=now.isoformat() + 'Z',
        timeMax=one_week_later.isoformat() + 'Z',
        singleEvents=True,
        orderBy='startTime'
    ).execute()

    events = events_result.get('items', [])
    return events
