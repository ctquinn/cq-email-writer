import keyboard
import os
import readchar
import sys
import time
import threading
import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

# Disable parallelism to avoid warnings
os.environ["TOKENIZERS_PARALLELISM"] = "false"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "../../"))

MODEL_PATH = os.path.join(PROJECT_ROOT, "src/transformers/fine_tuned_model")

# Load the model and tokenizer
print("Loading the fine-tuned model and tokenizer...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_PATH)

autocomplete_suggestion = ""
stop_autocomplete = False
user_input_lock = threading.Lock()
user_input = ""


def generate_completion(subject, text_so_far):
    """Generate auto-completion."""
    input_text = f"[SUBJECT] {subject}\n[TEXT SO FAR] {text_so_far.strip()}"
    inputs = tokenizer(input_text, return_tensors="pt")
    with torch.no_grad():
        output_ids = model.generate(
            inputs.input_ids,
            max_length=50,
            num_beams=5,
            early_stopping=True,
        )
    suggestion = tokenizer.decode(output_ids[0], skip_special_tokens=True)
    return suggestion.strip()


def suggest_autocomplete(subject):
    """Thread to generate suggestions."""
    global autocomplete_suggestion, stop_autocomplete
    while not stop_autocomplete:
        time.sleep(1)  # Check every second for updates
        with user_input_lock:
            if user_input.strip():
                autocomplete_suggestion = generate_completion(subject, user_input)


def real_time_input(subject):
    """Capture user input and display auto-completions."""
    global user_input, autocomplete_suggestion, stop_autocomplete

    print("\n--- Email Auto-Complete Assistant ---\n")
    print("Start typing your email body. Press [Tab] to accept suggestions.")
    print("Press [Enter] when done.\n")

    email_body = ""
    buffer = []
    show_suggestion = False

    try:
        # Start the auto-complete suggestion thread
        autocomplete_thread = threading.Thread(
            target=suggest_autocomplete, args=(subject,)
        )
        autocomplete_thread.start()

        while True:
            char = readchar.readkey()

            # Handle special keys
            if char == readchar.key.SPACE:
                buffer.append(" ")  # Add space to buffer
                email_body += "".join(buffer)  # Append buffer to email body
                buffer = []  # Clear the buffer
                with user_input_lock:
                    user_input = (
                        email_body  # Update user_input to include the final word
                    )
                show_suggestion = True  # Trigger suggestion
            elif char == readchar.key.BACKSPACE:
                if buffer:
                    buffer.pop()  # Remove last character in buffer
                elif email_body:
                    email_body = email_body[:-1]  # Remove last character in body
                show_suggestion = False  # Clear suggestion on new input
            elif char == "\t":  # Tab to accept suggestion
                if autocomplete_suggestion and show_suggestion:
                    email_body += f"{autocomplete_suggestion.strip()} "
                    buffer = []  # Clear buffer after accepting suggestion
                    with user_input_lock:
                        user_input = email_body  # Update user_input after accepting
                    show_suggestion = False  # Suggestion accepted
            elif char == readchar.key.ENTER:  # Enter to finish
                print("\nExiting...")
                break
            else:
                # Append regular characters to the buffer
                buffer.append(char)
                with user_input_lock:
                    user_input = email_body + "".join(
                        buffer
                    )  # Update user_input in real-time
                show_suggestion = False  # Clear suggestion when user types

            # Display inline suggestion or just the current text
            print("\r\033[K", end="")  # Clear the current line
            if show_suggestion and autocomplete_suggestion:
                print(
                    f"{email_body}{''.join(buffer)} [SUGGESTION] {autocomplete_suggestion}",
                    end="",
                    flush=True,
                )
            else:
                print(f"{email_body}{''.join(buffer)}", end="", flush=True)

    except KeyboardInterrupt:
        print("\nExiting the email assistant.")
    finally:
        stop_autocomplete = True
        autocomplete_thread.join()

    print("\nFinal Email Body:\n", email_body.strip())
    print("\n--- End of Demo ---")


if __name__ == "__main__":
    subject = input("Enter the subject of your email: ").strip()
    real_time_input(subject)
