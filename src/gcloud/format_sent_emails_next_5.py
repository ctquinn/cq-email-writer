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
        if re.match(
            r"^On .* at .* wrote:$", line
        ):  # Matches "On Tue, Feb 28, 2023 at 4:44 PM wrote:"
            is_quoted_reply = True
            break
        if re.match(r"^On .* wrote:$", line):  # Matches "On Mon, 1 March 2021 wrote:"
            is_quoted_reply = True
            break
        if re.match(r"^>+ ", line):  # Quoted lines in plain text emails
            is_quoted_reply = True
            break
        if line.startswith("---- Original Message ----"):  # Common forward separator
            is_quoted_reply = True
            break

        # Remove standalone dates/timestamps
        if re.match(
            r"^(Mon|Tue|Wed|Thu|Fri|Sat|Sun),?\s+\w+\s+\d{1,2},\s+\d{4}(.*at.*)?", line
        ):
            continue
        if re.match(
            r"^\d{1,2}/\d{1,2}/\d{2,4}(.*at.*)?", line
        ):  # Matches "2/28/2023 at 4:44 PM"
            continue
        if re.match(
            r"^\d{1,2}-\d{1,2}-\d{2,4}(.*at.*)?", line
        ):  # Matches "2-28-2023 at 4:44 PM"
            continue

        # Skip empty or whitespace-only lines
        if line.strip() == "":
            continue

        # Include lines before quoted reply begins
        if not is_quoted_reply:
            cleaned_lines.append(line)

    # Rejoin the cleaned lines
    return "\n".join(cleaned_lines)


def tokenize(text):
    """Split text into tokens based on whitespace."""
    return text.split()


def create_incremental_entries(subject, body, max_words=5):
    """
    Create input-output pairs for incremental prediction using a tag-based format.

    Parameters:
    - subject: Email subject line.
    - body: Full email body.
    - max_words: Maximum number of words to include in the output.

    Returns:
    - A list of input-output pairs for fine-tuning.
    """
    tokens = tokenize(body)
    entries = []
    text_so_far = ""

    for i in range(len(tokens)):
        # Extract up to `max_words` tokens for the output
        next_words = " ".join(tokens[i : i + max_words])

        # Skip if the next words contain unwanted patterns like dates
        if re.match(
            r"^\d{1,2}[/-]\d{1,2}[/-]\d{2,4}(.*at.*)?", next_words
        ):  # Matches "2/28/2023 at 4:44 PM"
            continue
        if re.match(
            r"^(Mon|Tue|Wed|Thu|Fri|Sat|Sun),?\s+\w+\s+\d{1,2},\s+\d{4}(.*at.*)?",
            next_words,
        ):
            continue

        # Format input with structured tags
        input_text = f"[SUBJECT] {subject}\n[TEXT SO FAR] {text_so_far}".strip()
        entries.append({"input": input_text, "output": next_words})

        # Update text_so_far with the next token
        text_so_far = " ".join(tokens[: i + 1])

    return entries


def format_emails_for_finetuning(input_file, output_file, min_tokens=25, max_words=5):
    """
    Format threads.json into input-output pairs for incremental fine-tuning.

    Parameters:
    - input_file: Path to the input JSON file containing initial emails.
    - output_file: Path to save the formatted dataset.
    - min_tokens: Minimum number of tokens required in the email body.
    - max_words: Maximum number of words to include in each output.
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
        if len(tokenize(body)) <= min_tokens:
            continue

        # Generate incremental entries
        incremental_entries = create_incremental_entries(subject, body, max_words)
        formatted_data.extend(incremental_entries)

    # Save formatted data to a JSON file
    with open(output_file, "w", encoding="utf-8") as file:
        json.dump(formatted_data, file, ensure_ascii=False, indent=4)

    print(f"Formatted dataset saved to {output_file}")


# Run the formatter
format_emails_for_finetuning(
    "threads.json", "fine_tune_dataset.json", min_tokens=25, max_words=5
)
