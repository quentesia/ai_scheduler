from flask import Flask, request, jsonify, render_template
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from datetime import datetime, timedelta
from auth import authorize, oauth2callback, get_authenticated_service
from dotenv import load_dotenv
import os
import uuid
import requests

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'fallback_secret_key')  # Fallback if .env is missing
DIALOGFLOW_SESSION_ID = str(uuid.uuid4())
DIALOGFLOW_PROJECT_ID = os.getenv('DIALOGFLOW_PROJECT_ID')
DIALOGFLOW_API_URL = f"https://dialogflow.googleapis.com/v2beta1/projects/{DIALOGFLOW_PROJECT_ID}/agent/sessions/{DIALOGFLOW_SESSION_ID}:detectIntent"
DIALOGFLOW_AUTH_TOKEN = os.getenv("DIALOGFLOW_AUTH_TOKEN")

# Authenticate with Google Calendar API
def get_google_calendar_service():
    creds = Credentials.from_authorized_user_file('token.json', ['https://www.googleapis.com/auth/calendar'])
    service = build('calendar', 'v3', credentials=creds)
    return service

# Home route
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/authorize')
def auth():
    return authorize()

@app.route('/oauth2callback', endpoint='oauth2callback')
def callback():
    return oauth2callback()

@app.route('/calendar')
def calendar():
    try:
        service = get_authenticated_service()
        # Example: List upcoming events
        now = datetime.utcnow().isoformat() + 'Z'
        events_result = service.events().list(
            calendarId='primary', timeMin=now, maxResults=10,
            singleEvents=True, orderBy='startTime').execute()
        events = events_result.get('items', [])
        return jsonify(events)
    except Exception as e:
        return jsonify({"error": str(e)}), 401

# Webhook route
@app.route('/webhook', methods=['POST'])
def webhook():
    body = request.get_json()
    headers = {
        "Authorization": f"Bearer {DIALOGFLOW_AUTH_TOKEN}",
        "Content-Type": "application/json"
    }

    try:
        # Make the API call to Dialogflow
        response = requests.post(DIALOGFLOW_API_URL, json=body, headers=headers)
        response_data = response.json()

        intent = response_data.get('queryResult', {}).get('intent', {}).get('displayName', 'Unknown Intent')
        parameters = response_data.get('queryResult', {}).get('parameters', {})

        print(f"Data: {response_data}")
        print(f"Intent: {intent}")
        print(f"Parameters: {parameters}")

        if intent == 'Default Welcome Intent':
            return jsonify({"fulfillmentText": "Hello! How can I help you today?"})
        elif intent == 'CreateMeeting':
            return create_meeting(parameters)
        elif intent == 'CancelMeeting':
            return cancel_meeting(parameters)
        elif intent == 'ShowUpcomingMeetings':
            return show_upcoming_meetings()
        else:
            return jsonify({"fulfillmentText": "Sorry, I didn't understand that intent."})



    except requests.exceptions.RequestException as e:
        # Handle errors during the API request
        print(f"Error making Dialogflow API call: {e}")
        return jsonify({"fulfillmentText": "An error occurred while processing your request."}), 500
    
# Fetch meetings for the next week
def show_upcoming_meetings():

    service = get_google_calendar_service()

    # Calculate the time range
    now = datetime.now(datetime.timezone.utc)
    one_week_later = now + timedelta(days=7)
    
    time_min = now.isoformat() + 'Z'  # 'Z' indicates UTC time
    time_max = one_week_later.isoformat() + 'Z'

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

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Route not found"}), 404

@app.errorhandler(500)
def server_error(error):
    return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    app.run(debug=True)