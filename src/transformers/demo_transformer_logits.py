import torch
import os
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd

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
input_text = "[SUBJECT] Question About My iPhone\n[TEXT SO FAR] How "
inputs = tokenizer(input_text, return_tensors="pt")

# Generate multiple sequences with beam search
print("Generating top N inferences...")
beam_outputs = model.generate(
    inputs.input_ids,
    max_length=50,  # Adjust maximum length of generated sequences
    num_beams=10,  # Number of beams for beam search
    num_return_sequences=10,  # Return top N sequences
    output_scores=True,  # Include scores for analysis
    return_dict_in_generate=True,
)

# Decode the top N sequences
sequences = [
    tokenizer.decode(seq, skip_special_tokens=True) for seq in beam_outputs.sequences
]

# Compute unnormalized probabilities from beam search scores
# Beam search scores are negative log probabilities -> convert to unnormalized likelihoods
beam_scores = beam_outputs.sequences_scores
unnormalized_likelihoods = torch.exp(
    beam_scores
).tolist()  # Convert log probabilities to unnormalized likelihoods

# Create a DataFrame for Seaborn visualization
data = pd.DataFrame(
    {"Inference": sequences, "Unnormalized Likelihood": unnormalized_likelihoods}
)
data = data.sort_values(
    "Unnormalized Likelihood", ascending=False
)  # Sort by likelihood

# Visualization with Seaborn
print("Visualizing top N inferences...")
sns.set(style="whitegrid")
plt.figure(figsize=(10, 8))
sns.barplot(
    data=data,
    y="Inference",  # Most likely at the top
    x="Unnormalized Likelihood",
    palette="viridis",
)
plt.xlabel("Unnormalized Likelihood", fontsize=12)
plt.ylabel("Generated Inference", fontsize=12)
plt.title("Top N Most Likely Inferences", fontsize=14)
plt.tight_layout()
plt.show()
