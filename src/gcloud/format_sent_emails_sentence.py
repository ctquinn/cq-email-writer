import json
import re
from tqdm import tqdm


def clean_text(text):
    """Clean and sanitize email text."""
    # Replace \r\n\r\n with \n
    text = re.sub(r"\r\n\r\n", "\n", text)
    # Replace multiple spaces with a single space
    text = re.sub(r"\s+", " ", text)
    # Remove hyperlinks
    text = re.sub(r"https?://\S+|www\.\S+", "", text)
    # Normalize Unicode apostrophes to standard apostrophe
    text = text.replace("’", "'")
    # Remove unusual special characters but keep common ones
    text = re.sub(r"[^\w\s,.;:?!'\"-]", "", text)
    # Remove date-like patterns
    text = remove_dates_and_metadata(text)
    return text.strip()


def remove_dates_and_metadata(text):
    """
    Remove date-like substrings and metadata from text.

    Parameters:
    - text: The text to clean.

    Returns:
    - Text with dates and metadata removed.
    """
    # Patterns to match common date formats and metadata
    patterns = [
        r"\b(Mon|Tue|Wed|Thu|Fri|Sat|Sun),?\s+\w+\s+\d{1,2},\s+\d{4}\b",  # Full date with day
        r"\b\d{1,2}/\d{1,2}/\d{2,4}\b",  # Slash-separated dates (e.g., 11/17/2024)
        r"\b\d{1,2}-\d{1,2}-\d{2,4}\b",  # Hyphen-separated dates (e.g., 11-17-2024)
        r"\b\d{1,2}:\d{2}\s*(AM|PM|am|pm)?\b",  # Times (e.g., 2:20 PM)
        r"\b\w+\s+\d{1,2}-\d{1,2}\b",  # Month with date range (e.g., November 11-17)
        r"\b\w+\s+\d{1,2},?\s+\d{4}\b",  # Month Day, Year (e.g., November 11, 2024)
        r"<.*?>",  # Email addresses in angle brackets (e.g., <sisson@telosrunning.com>)
        r"On .* at .* wrote:",  # Quoted reply indicators
        r"On .* wrote:",  # Alternate quoted reply indicators
    ]

    for pattern in patterns:
        text = re.sub(pattern, "", text)

    # Remove multiple spaces left behind
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def clean_email_body(body):
    """
    Remove quoted replies, forwarded content, metadata, and standalone date markers from an email body.

    Parameters:
    - body: The full email body as a string.

    Returns:
    - Cleaned email body with quoted content and metadata removed.
    """
    # Split lines for processing
    lines = body.splitlines()
    cleaned_lines = []
    is_quoted_reply = False

    for line in lines:
        # Detect and break on Gmail-style quoted replies
        if re.match(r"^On .* at .* wrote:$", line):
            is_quoted_reply = True
            break
        if re.match(r"^On .* wrote:$", line):
            is_quoted_reply = True
            break
        if re.match(r"^>+ ", line):  # Quoted lines in plain text emails
            is_quoted_reply = True
            break
        if line.startswith("---- Original Message ----"):
            is_quoted_reply = True
            break

        # Remove metadata patterns (email addresses, timestamps)
        if re.search(r"<.*?>", line):  # Email addresses in angle brackets
            continue
        if re.search(r"On .* at .* wrote:", line):  # Quoted reply
            continue
        if re.search(r"On .* wrote:", line):  # Quoted reply (alternate form)
            continue

        # Skip empty or whitespace-only lines
        if line.strip() == "":
            continue

        # Include lines before quoted reply begins
        if not is_quoted_reply:
            cleaned_lines.append(line)

    # Rejoin the cleaned lines
    cleaned_body = "\n".join(cleaned_lines)
    return remove_dates_and_metadata(cleaned_body)


def split_into_sentences(text):
    """
    Split text into sentences based on end-of-sentence punctuation.

    Parameters:
    - text: Full text to split.

    Returns:
    - List of sentences.
    """
    sentences = re.split(r"(?<=[.!?;:])\s+", text)
    return [s.strip() for s in sentences if s.strip()]


def create_sentence_completion_entries(subject, body):
    """
    Create input-output pairs for sentence completion.

    Parameters:
    - subject: Email subject line.
    - body: Full email body.

    Returns:
    - A list of input-output pairs for sentence completion.
    """
    sentences = split_into_sentences(body)
    entries = []

    for sentence in sentences:
        tokens = sentence.split()
        for i in range(len(tokens)):
            # Split the sentence into "so far" and "completion"
            text_so_far = " ".join(tokens[:i])
            completion = " ".join(tokens[i:])
            if text_so_far and completion:
                input_text = f"[SUBJECT] {subject}\n[TEXT SO FAR] {text_so_far}"
                entries.append({"input": input_text, "output": completion})

    return entries


def format_emails_for_sentence_completion(input_file, output_file, min_tokens=25):
    """
    Format threads.json into input-output pairs for sentence completion.

    Parameters:
    - input_file: Path to the input JSON file containing initial emails.
    - output_file: Path to save the formatted dataset.
    - min_tokens: Minimum number of tokens required in the email body.
    """
    with open(input_file, "r", encoding="utf-8") as file:
        threads = json.load(file)

    formatted_data = []
    for thread in tqdm(threads, desc="Formatting Emails"):
        subject = thread.get("subject", "").strip()
        body = thread.get("body", "").strip()

        if not subject or not body:
            continue

        # Clean text for subject and body
        subject = clean_text(subject)
        body = clean_email_body(body)

        # Include only emails with sufficient tokens in the body
        if len(body.split()) <= min_tokens:
            continue

        # Generate sentence completion entries
        completion_entries = create_sentence_completion_entries(subject, body)
        formatted_data.extend(completion_entries)

    # Save formatted data to a JSON file
    with open(output_file, "w", encoding="utf-8") as file:
        json.dump(formatted_data, file, ensure_ascii=False, indent=4)

    print(f"Formatted dataset saved to {output_file}")


# Run the formatter
format_emails_for_sentence_completion(
    "threads.json", "fine_tune_sentence_completion.json", min_tokens=25
)
