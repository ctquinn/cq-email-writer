from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle
import os

# Scopes for the Gmail API
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def main():
    creds = None
    # Load credentials if they exist
    if os.path.exists("token.pickle"):
        with open("token.pickle", "rb") as token:
            creds = pickle.load(token)
    # If no valid credentials, request login
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for future use
        with open("token.pickle", "wb") as token:
            pickle.dump(creds, token)

    # Build the Gmail service
    service = build("gmail", "v1", credentials=creds)

    # Fetch sent emails
    results = service.users().messages().list(userId="me", q="label:sent").execute()
    messages = results.get("messages", [])

    if not messages:
        print("No sent messages found.")
    else:
        print("Messages:")
        for msg in messages[:5]:  # Fetch and display first 5 messages
            message = (
                service.users().messages().get(userId="me", id=msg["id"]).execute()
            )
            print(message["snippet"])


if __name__ == "__main__":
    main()
