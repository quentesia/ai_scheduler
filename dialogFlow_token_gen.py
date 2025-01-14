from google.oauth2 import service_account
from google.auth.transport.requests import Request
import os

# Path to your service account key JSON file
credentials = service_account.Credentials.from_service_account_file(
    "dialogflow.json",
    scopes=["https://www.googleapis.com/auth/cloud-platform"]
)
credentials.refresh(Request())  # Refresh the token

print(credentials.token)  # Print the token to use in the app.py file