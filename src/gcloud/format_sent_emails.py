import json


def format_emails_for_finetuning(input_file, output_file):
    """
    Formats sent_emails.json into input-output pairs for fine-tuning.

    Parameters:
    - input_file: Path to the input JSON file containing sent emails.
    - output_file: Path to save the formatted dataset.
    """
    with open(input_file, "r", encoding="utf-8") as file:
        emails = json.load(file)

    formatted_data = []
    for email in emails:
        email_body = email.get("body", "").strip()
        if len(email_body.split()) > 25:  # Ensure sufficient length
            formatted_data.append(
                {
                    "input": f"Generate a response to this email:\n{email_body}",
                    "output": "Write your ideal response here",  # Replace with curated response
                }
            )

    # Save the formatted dataset
    with open(output_file, "w", encoding="utf-8") as file:
        json.dump(formatted_data, file, ensure_ascii=False, indent=4)

    print(f"Formatted dataset saved to {output_file}")


# Run the formatting script
format_emails_for_finetuning("sent_emails.json", "fine_tune_dataset.json")
