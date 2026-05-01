"""
Module: auth.py
Purpose: Authentication bridge for the Nexus Hub Python VM to access Google Workspace APIs.
Handles headless OAuth 2.0 flow for Gmail and Drive scopes.
"""

import os
import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# If modifying these scopes, delete the file token.json.
SCOPES = [
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/contacts.readonly'
]

CREDENTIALS_FILE = 'credentials.json'
TOKEN_FILE = 'token.json'

def authenticate() -> Credentials:
    """
    Purpose: Authenticates the application with Google Workspace APIs.
             Loads credentials from 'credentials.json' and manages OAuth flow.
    Expected Inputs: None (relies on local files and environment variables).
    Expected Outputs: google.oauth2.credentials.Credentials - The active credentials object.
    """
    creds = None
    
    # Check if token.json exists (contains the user's access and refresh tokens)
    # If the token file is present, load the stored credentials from it.
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        # If credentials exist but are expired, and we have a refresh token, refresh them automatically.
        if creds and creds.expired and creds.refresh_token:
            print("Token expired. Attempting to refresh...")
            creds.refresh(Request())
        # If no credentials exist or they cannot be refreshed, initiate a new login flow.
        else:
            # If the client secrets file is missing, we cannot start the flow.
            if not os.path.exists(CREDENTIALS_FILE):
                print(f"CRITICAL ERROR: '{CREDENTIALS_FILE}' not found.")
                print("You must download your OAuth 2.0 Client IDs JSON from Google Cloud Console")
                print(f"and place it in the root directory as '{CREDENTIALS_FILE}'.")
                raise FileNotFoundError(f"Missing {CREDENTIALS_FILE}")
            
            print("Initiating new OAuth flow...")
            print("NOTE: Because this VM is headless, you must set up an SSH tunnel to port 8080.")
            print("Example: ssh -L 8080:localhost:8080 user@your-vm-ip")
            print("Then complete the authentication flow in your local browser.")
            
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            
            # Using port 8080 and disabling open_browser for headless VM compatibility
            creds = flow.run_local_server(port=8080, open_browser=False)
            
        # Save the credentials for the next run
        # Open the token file to store the newly obtained or refreshed credentials.
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
            print(f"Authentication successful! Token saved to '{TOKEN_FILE}'.")

    return creds

# If this script is run directly, perform a test authentication.
if __name__ == '__main__':
    # Test the authentication flow
    print("Testing Google Workspace Authentication Bridge...")
    credentials = authenticate()
    # If the credentials were successfully obtained and are valid, report success.
    if credentials and credentials.valid:
        print("Success! Credentials are valid and ready to use.")
    # Otherwise, report failure.
    else:
        print("Failed to obtain valid credentials.")
