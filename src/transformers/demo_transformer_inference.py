import os

from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

# Disable parallelism to avoid issues if running on local machine
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Path to fine-tuned model
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "../../"))
MODEL_PATH = os.path.join(PROJECT_ROOT, "src/transformers/fine_tuned_model")

# Load the fine-tuned model and tokenizer
print("Loading the fine-tuned model and tokenizer...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_PATH)

# Test input
input_text = (
    "[SUBJECT] Question About My iPhone\n[TEXT SO FAR] Hey Mike, I was wondering if"
)
inputs = tokenizer(input_text, return_tensors="pt")

# Generate the output
print("Generating output...")
output_ids = model.generate(
    inputs.input_ids,
    max_length=100,  # Adjust max_length as needed
    num_beams=10,  # Beam search for better results (optional)
    early_stopping=True,
)
output_text = tokenizer.decode(output_ids[0], skip_special_tokens=True)

print("Generated Output:")
print(output_text)
