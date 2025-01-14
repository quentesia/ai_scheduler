from flask import Flask, request, jsonify
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

app = Flask(__name__)

# Authenticate with Google Calendar API
def get_google_calendar_service():
    creds = Credentials.from_authorized_user_file('token.json', ['https://www.googleapis.com/auth/calendar'])
    service = build('calendar', 'v3', credentials=creds)
    return service

# Home route
@app.route('/')
def home():
    return "Welcome to the AI-Powered Global Meeting Scheduler!"

# Webhook route
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    intent = data.get('queryResult', {}).get('intent', {}).get('displayName')
    parameters = data.get('queryResult', {}).get('parameters', {})

    if intent == 'CreateMeeting':
        return create_meeting(parameters)
    elif intent == 'CancelMeeting':
        return cancel_meeting(parameters)
    else:
        return jsonify({"fulfillmentText": "Sorry, I didn't understand that intent."})

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

    # Create the event
    event = {
        'summary': 'New Meeting',
        'start': {
            'dateTime': start_time,
            'timeZone': 'America/Chicago',
        },
        'end': {
            'dateTime': end_time,
            'timeZone': 'America/Chicago',
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

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Route not found"}), 404

@app.errorhandler(500)
def server_error(error):
    return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    app.run(debug=True)