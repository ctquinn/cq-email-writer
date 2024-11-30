# src/chrome_extension/model_server/app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
import torch

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes


# Load the model
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "../../.."))
MODEL_PATH = os.path.join(
    PROJECT_ROOT, "src/transformers/fine_tuned_model_email_writer"
)

tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_PATH)


@app.route("/autocomplete", methods=["POST"])
def autocomplete():
    data = request.json
    subject = data.get("subject", "") if data else ""
    text_so_far = data.get("text_so_far", "") if data else ""

    # Prepare input
    input_text = f"[SUBJECT] {subject}\n[TEXT SO FAR] {text_so_far.strip()}"
    inputs = tokenizer(input_text, return_tensors="pt")

    print(f"Generating completion for input text: {input_text}")

    # Generate output
    with torch.no_grad():
        output_ids = model.generate(
            inputs.input_ids,
            max_length=50,
            num_beams=5,
            early_stopping=True,
        )
    suggestion = tokenizer.decode(output_ids[0], skip_special_tokens=True)

    print(f"Generated suggestion: {suggestion}")

    return jsonify({"suggestion": suggestion})


if __name__ == "__main__":
    app.run(port=5000, debug=True)
