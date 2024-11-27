import json
import re
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle
import os
from tqdm import tqdm  # Import TQDM for the progress bar

# Scopes for the Gmail API
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

# Set maximum number of emails to fetch
MAX_EMAILS = 100


def clean_text(text):
    """Clean and sanitize email text."""
    # Replace \r\n\r\n with \n
    text = re.sub(r"\r\n\r\n", "\n", text)
    # Remove hyperlinks
    text = re.sub(r"https?://\S+|www\.\S+", "", text)
    # Remove unusual special characters, keep common ones
    text = re.sub(r"[^\w\s,.;:?!]", "", text)
    return text


def extract_email_body(payload):
    """Extract the full email body from the payload."""
    if "parts" in payload:
        for part in payload["parts"]:
            if part["mimeType"] == "text/plain" and "body" in part:
                data = part["body"].get("data", "")
                return clean_text(decode_base64(data))
            elif "parts" in part:
                return extract_email_body(part)  # Recursively handle nested parts
    elif "body" in payload:
        data = payload["body"].get("data", "")
        return clean_text(decode_base64(data))
    return "No body found."


def decode_base64(data):
    """Decode base64 encoded data."""
    import base64

    return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")


def tokenize(text):
    """Split text into tokens based on whitespace."""
    return text.split()


def save_emails_to_json(emails, filename="sent_emails.json"):
    """Save emails to a JSON file."""
    with open(filename, "w", encoding="utf-8") as file:
        json.dump(emails, file, ensure_ascii=False, indent=4)
    print(f"Saved {len(emails)} emails to {filename}")


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
    print(f"Fetching up to {MAX_EMAILS} sent emails...")
    results = (
        service.users()
        .messages()
        .list(userId="me", q="label:sent", maxResults=MAX_EMAILS)
        .execute()
    )
    messages = results.get("messages", [])

    if not messages:
        print("No sent messages found.")
    else:
        emails = []
        print("Fetching emails...")
        for msg in tqdm(messages, desc="Fetching Emails", unit="email"):
            message = (
                service.users().messages().get(userId="me", id=msg["id"]).execute()
            )
            email_data = {
                "id": message["id"],
                "snippet": message.get("snippet", ""),
                "subject": "",
                "body": "",
                "to": "",
                "from": "",
            }
            # Extract payload information
            payload = message.get("payload", {})
            headers = payload.get("headers", [])

            # Extract headers (e.g., Subject, From, To)
            for header in headers:
                if header["name"].lower() == "subject":
                    email_data["subject"] = clean_text(header["value"])
                elif header["name"].lower() == "to":
                    email_data["to"] = header["value"]
                elif header["name"].lower() == "from":
                    email_data["from"] = header["value"]

            # Skip emails where the "To" address contains "unsubscribe"
            if "unsubscribe" in email_data["to"].lower():
                continue

            # Extract and clean email body
            email_data["body"] = extract_email_body(payload)

            # Skip emails with body length <= 25 tokens
            if len(tokenize(email_data["body"])) <= 25:
                continue

            emails.append(email_data)

        # Save emails to a JSON file
        save_emails_to_json(emails)


if __name__ == "__main__":
    main()
