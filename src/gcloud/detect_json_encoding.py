import chardet

# Read the file in binary mode
file_path = "fine_tune_dataset_fixed.json"
with open(file_path, "rb") as f:
    raw_data = f.read()

# Detect encoding
result = chardet.detect(raw_data)
print(f"Detected encoding: {result['encoding']}")

# E.g. to fix: iconv -f MacRoman -t utf-8 fine_tune_dataset.json > fine_tune_dataset_fixed.json
