import json
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle
import os
import re
from tqdm import tqdm

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def extract_email_body(payload):
    """Extract the plain text body from the email payload."""
    if "parts" in payload:
        for part in payload["parts"]:
            if part["mimeType"] == "text/plain" and "body" in part:
                data = part["body"].get("data", "")
                return decode_base64(data)
            elif "parts" in part:
                return extract_email_body(part)  # Recursively handle nested parts
    elif "body" in payload:
        data = payload["body"].get("data", "")
        return decode_base64(data)
    return ""


def clean_email_body(body):
    """
    Remove quoted replies, forwarded content, and metadata from an email body.

    Parameters:
    - body: The full email body as a string.

    Returns:
    - Cleaned email body with quoted content removed.
    """
    # Split lines for processing
    lines = body.splitlines()
    cleaned_lines = []
    is_quoted_reply = False

    for line in lines:
        # Detect and break on Gmail-style quoted replies
        if re.match(
            r"^On .* at .* wrote:$", line
        ):  # Matches "On Tue, Sep 10, 2024 at 12:18 PM wrote:"
            is_quoted_reply = True
            break
        if re.match(r"^.* wrote:$", line):  # Matches "<Sender> wrote:"
            is_quoted_reply = True
            break
        if re.match(r"^>+ ", line):  # Quoted lines in plain text emails
            is_quoted_reply = True
            break
        if line.startswith("---- Original Message ----"):  # Common forward separator
            is_quoted_reply = True
            break
        if re.match(
            r"From: .*@.*", line
        ):  # Matches lines starting with "From: <email>"
            is_quoted_reply = True
            break
        if re.match(r"Sent: .*", line):  # Matches lines starting with "Sent: <date>"
            is_quoted_reply = True
            break
        if re.match(r"To: .*@.*", line):  # Matches lines starting with "To: <email>"
            is_quoted_reply = True
            break
        if re.match(r"Cc: .*@.*", line):  # Matches lines starting with "Cc: <email>"
            is_quoted_reply = True
            break
        if re.match(r"Date: .*", line):  # Matches lines starting with "Date: <date>"
            is_quoted_reply = True
            break

        # Skip empty or whitespace-only lines
        if line.strip() == "":
            continue

        # Include lines before quoted reply begins
        if not is_quoted_reply:
            cleaned_lines.append(line)

    # Rejoin the cleaned lines
    return "\n".join(cleaned_lines)


def decode_base64(data):
    """Decode base64-encoded email content."""
    import base64

    return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")


from tqdm import tqdm


from tqdm import tqdm
import json


def fetch_initial_emails(service, output_file, max_pages=50):
    """
    Fetch the first email in each thread where you sent the initial message.

    Parameters:
    - service: Gmail API service instance.
    - output_file: File to save the fetched emails.
    - max_pages: Maximum number of pages to fetch (each page fetches up to 100 emails).
    """
    all_emails = []
    seen_threads = set()
    page_token = None  # For pagination
    emails_fetched = 0

    with tqdm(total=max_pages, desc="Fetching Email Pages") as pbar:
        for page_number in range(max_pages):
            try:
                # Fetch the next page of results
                response = (
                    service.users()
                    .messages()
                    .list(
                        userId="me",
                        q="label:sent",
                        maxResults=100,  # Fetch up to 100 emails per request
                        pageToken=page_token,
                    )
                    .execute()
                )

                messages = response.get("messages", [])
                if not messages:
                    print("No more messages to fetch.")
                    break  # Stop if no messages are returned

                for msg in messages:
                    try:
                        message = (
                            service.users()
                            .messages()
                            .get(userId="me", id=msg["id"])
                            .execute()
                        )
                        thread_id = message.get("threadId")

                        # Skip if we've already processed this thread
                        if thread_id in seen_threads:
                            continue
                        seen_threads.add(thread_id)

                        # Extract headers and payload
                        payload = message.get("payload", {})
                        headers = {
                            h["name"]: h["value"] for h in payload.get("headers", [])
                        }
                        subject = headers.get("Subject", "No Subject")
                        body = extract_email_body(payload).strip()

                        # Exclude messages with "Fwd" in the subject
                        if "Fwd" in subject:
                            continue

                        # Skip emails with empty bodies
                        if not body:
                            continue

                        # Clean the body to remove quoted replies/forwards
                        body = clean_email_body(body)

                        # Skip if the cleaned body is empty
                        if not body.strip():
                            continue

                        all_emails.append(
                            {"thread_id": thread_id, "subject": subject, "body": body}
                        )
                        emails_fetched += 1

                    except Exception as e:
                        print(f"Error processing email {msg['id']}: {e}")
                        continue  # Skip to the next email

                # Save progress after each page
                with open(output_file, "w", encoding="utf-8") as file:
                    json.dump(all_emails, file, ensure_ascii=False, indent=4)

                # Check if there is another page
                page_token = response.get("nextPageToken")
                if not page_token:
                    print("No more pages to fetch.")
                    break  # Stop if no more pages

            except Exception as e:
                print(f"Error processing page {page_number + 1}: {e}")
                continue  # Skip to the next page

            # Update progress bar
            pbar.update(1)

    print(f"Fetched {len(all_emails)} emails saved to {output_file}")


def main():
    creds = None
    if os.path.exists("token.pickle"):
        with open("token.pickle", "rb") as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.pickle", "wb") as token:
            pickle.dump(creds, token)

    service = build("gmail", "v1", credentials=creds)
    fetch_initial_emails(service, "threads.json")


if __name__ == "__main__":
    main()
