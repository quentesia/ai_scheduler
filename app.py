from flask import Flask, request, jsonify, render_template
from googleapiclient.discovery import build
from datetime import datetime
from auth import authorize, oauth2callback, get_authenticated_service
from intent_handling import create_meeting, cancel_meeting, show_upcoming_meetings
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
        elif intent == 'ShowMeetings':
            return show_upcoming_meetings()
        else:
            return jsonify({"fulfillmentText": "Sorry, I didn't understand that intent."})



    except requests.exceptions.RequestException as e:
        # Handle errors during the API request
        print(f"Error making Dialogflow API call: {e}")
        return jsonify({"fulfillmentText": "An error occurred while processing your request."}), 500

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Route not found"}), 404

@app.errorhandler(500)
def server_error(error):
    return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    app.run(debug=True)