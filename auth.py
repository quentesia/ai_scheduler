from flask import Flask, redirect, url_for, session, request
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import os

# Set up Google OAuth2
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'  # Allow HTTP for local testing
client_secrets_file = 'credentials.json'

def get_google_auth_flow():
    """Create and return the Google OAuth2 flow."""
    return Flow.from_client_secrets_file(
        client_secrets_file,
        scopes=['https://www.googleapis.com/auth/calendar'],
        redirect_uri=url_for('oauth2callback', _external=True)
    )

def authorize():
    """Redirect user to Google for authorization."""
    flow = get_google_auth_flow()
    authorization_url, state = flow.authorization_url()
    session['state'] = state
    return redirect(authorization_url)

def oauth2callback():
    """Handle the callback from Google and store credentials."""
    state = session['state']
    flow = get_google_auth_flow()
    flow.fetch_token(authorization_response=request.url)
    credentials = flow.credentials
    session['credentials'] = credentials_to_dict(credentials)
    return redirect(url_for('home'))

def credentials_to_dict(credentials):
    """Convert Google credentials to a dictionary for session storage."""
    return {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    }

def get_authenticated_service():
    """Get an authenticated Google Calendar API service."""
    if 'credentials' not in session:
        raise Exception("User not authenticated.")
    credentials = Credentials(**session['credentials'])
    return build('calendar', 'v3', credentials=credentials)