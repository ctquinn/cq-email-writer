import os
import json
from transformers import (
    AutoTokenizer,
    AutoModelForSeq2SeqLM,
    Trainer,
    TrainingArguments,
    DataCollatorForSeq2Seq,
)
from datasets import Dataset
import torch

# Define relative paths based on script location
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "../../"))

DATA_PATH = os.path.join(PROJECT_ROOT, "src/gcloud/fine_tune_dataset.json")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "src/transformers/fine_tuned_model")
MODEL_NAME = "t5-small"  # You can choose a different model, e.g., "t5-base"


def load_data(data_path):
    """Load the dataset from JSON."""
    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return Dataset.from_list(data)


def tokenize_data(examples, tokenizer, max_input_length=512, max_output_length=128):
    """
    Tokenize the dataset.
    - Inputs: Subject + Text so far
    - Outputs: Next words
    """
    inputs = examples["input"]  # Extract the 'input' field from the batch
    outputs = examples["output"]  # Extract the 'output' field from the batch
    model_inputs = tokenizer(
        inputs,
        max_length=max_input_length,
        padding="max_length",
        truncation=True,
    )
    labels = tokenizer(
        outputs,
        max_length=max_output_length,
        padding="max_length",
        truncation=True,
    )
    model_inputs["labels"] = labels["input_ids"]
    return model_inputs


def main():
    # Load dataset
    print(f"Loading dataset from {DATA_PATH}...")
    dataset = load_data(DATA_PATH)
    print(f"Loaded {len(dataset)} examples.")

    # Load tokenizer and model
    print(f"Loading model and tokenizer ({MODEL_NAME})...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_NAME)

    # Tokenize dataset
    print("Tokenizing dataset...")
    tokenized_dataset = dataset.map(
        lambda examples: tokenize_data(examples, tokenizer),
        batched=True,
        remove_columns=["input", "output"],
    )

    # Data collator
    data_collator = DataCollatorForSeq2Seq(tokenizer, model=model)

    # Training arguments
    print("Setting up training arguments...")
    training_args = TrainingArguments(
        output_dir=OUTPUT_DIR,
        evaluation_strategy="epoch",
        learning_rate=5e-5,
        per_device_train_batch_size=8,
        per_device_eval_batch_size=8,
        num_train_epochs=3,
        weight_decay=0.01,
        save_total_limit=2,
        logging_dir=os.path.join(OUTPUT_DIR, "logs"),
        logging_steps=50,
        save_steps=500,
        save_strategy="steps",
        fp16=True if torch.cuda.is_available() else False,
        push_to_hub=False,
    )

    # Trainer
    print("Initializing Trainer...")
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_dataset,
        eval_dataset=tokenized_dataset,
        data_collator=data_collator,
    )

    # Train
    print("Starting fine-tuning...")
    trainer.train()

    # Save the fine-tuned model
    print(f"Saving model to {OUTPUT_DIR}...")
    trainer.save_model(OUTPUT_DIR)
    tokenizer.save_pretrained(OUTPUT_DIR)
    print("Model saved.")


if __name__ == "__main__":
    main()
