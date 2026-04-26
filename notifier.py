import os
import json
import base64
import urllib.request
from email.message import EmailMessage
from googleapiclient.discovery import build
from auth import authenticate

class NexusNotifier:
    def __init__(self):
        self.webhook_url = os.environ.get('NEXUS_WEBHOOK_URL')

    def send_urgent_webhook(self, payload: dict) -> None:
        """
        POSTs a JSON payload to the configured webhook URL.
        """
        if not self.webhook_url:
            print("NEXUS_WEBHOOK_URL not configured. Skipping urgent webhook.")
            return

        try:
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(self.webhook_url, data=data, headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.getcode() >= 300:
                    print(f"Failed to send webhook: HTTP {response.getcode()}")
        except Exception as e:
            print(f"Error sending urgent webhook: {e}")

    def send_daily_digest(self, email_body: str) -> None:
        """
        Sends an HTML email digest to the authenticated user using the Gmail API.
        """
        try:
            creds = authenticate()
            if not creds or not creds.valid:
                print("Authentication failed. Cannot send daily digest.")
                return

            service = build('gmail', 'v1', credentials=creds)
            profile = service.users().getProfile(userId='me').execute()
            user_email = profile.get('emailAddress')

            message = EmailMessage()
            message.set_content("Please enable HTML to view this message.")
            message.add_alternative(email_body, subtype='html')
            message['To'] = user_email
            message['From'] = user_email
            message['Subject'] = "Nexus Hub: Daily Digest & Quarantine Report"

            encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            create_message = {'raw': encoded_message}

            service.users().messages().send(userId='me', body=create_message).execute()
            print("Daily digest sent successfully.")
        except Exception as e:
            print(f"Error sending daily digest: {e}")
