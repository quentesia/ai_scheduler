from datetime import datetime, timedelta, timezone
from flask import jsonify
from google.oauth2.credentials import Credentials
from auth import get_google_calendar_service   

# Fetch meetings for the next week
def show_upcoming_meetings():

    service = get_google_calendar_service()

    # Calculate the time range
    now = datetime.now()
    one_week_later = now + timedelta(weeks=1)
    
    time_min = now.isoformat()
    time_max = one_week_later

    # Fetch events
    events_result = service.events().list(
        calendarId='primary',
        timeMin=time_min,
        timeMax=time_max,
        singleEvents=True,
        orderBy='startTime'
    ).execute()

    events = events_result.get('items', [])

    # Check if there are any events
    if not events:
        return jsonify({"fulfillmentText": "You have no meetings scheduled for the next week."})

    # Format the response with event details
    meeting_list = []
    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        meeting_list.append(f"{event['summary']} on {start}")

    response_text = "Here are your meetings for the next week:\n" + "\n".join(meeting_list)
    return jsonify({"fulfillmentText": response_text})

# Create a meeting
def create_meeting(parameters):
    date_time = parameters.get('date-time')
    if not date_time:
        return jsonify({"fulfillmentText": "Please provide a date and time for the meeting."})
    
    # Extract date and time
    date, time = date_time.split('T')
    start_time = f"{date}T{time}:00"
    end_time = f"{date}T{int(time.split(':')[0]) + 1}:{time.split(':')[1]}:00"  # Add 1 hour

    service = get_google_calendar_service()
    calendar = service.calendars().get(calendarId='primary').execute()
    time_zone = calendar['timeZone']

    # Create the event
    event = {
        'summary': 'New Meeting',
        'start': {
            'dateTime': start_time,
            'timeZone': time_zone,
        },
        'end': {
            'dateTime': end_time,
            'timeZone': time_zone,
        },
    }
    created_event = service.events().insert(calendarId='primary', body=event).execute()

    return jsonify({
        "fulfillmentText": f"Your meeting has been created. View it here: {created_event['htmlLink']}"
    })

# Cancel a meeting
def cancel_meeting(parameters):
    date_time = parameters.get('date-time')
    if not date_time:
        return jsonify({"fulfillmentText": "Please provide the date and time of the meeting to cancel."})
    
    # Extract date and time
    date, time = date_time.split('T')
    search_start = f"{date}T00:00:00"
    search_end = f"{date}T23:59:59"

    service = get_google_calendar_service()
    calendar = service.calendars().get(calendarId='primary').execute()
    time_zone = calendar['timeZone']

    # Search for the event
    events_result = service.events().list(
        calendarId='primary',
        timeMin=search_start,
        timeMax=search_end,
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    events = events_result.get('items', [])

    for event in events:
        event_start = event['start'].get('dateTime', event['start'].get('date'))
        if date in event_start and time in event_start:
            service.events().delete(calendarId='primary', eventId=event['id']).execute()
            return jsonify({"fulfillmentText": "Your meeting has been canceled."})

    return jsonify({"fulfillmentText": "No meeting found at the specified date and time."})