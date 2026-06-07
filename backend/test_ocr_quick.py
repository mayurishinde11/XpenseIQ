# test_ocr_quick.py
# This is a quick test script to verify our OCR service works.
# We give it a real receipt image and see what text it extracts.

import sys
import os

# Add the backend folder to Python's path so it can find our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.ocr_service import extract_text_from_image

# Path to our test receipt image
# Make sure this file exists in your project root folder
IMAGE_PATH = r"C:\Users\ASUS\Desktop\XpenseIQ\test_receipt.jpg"

print("Testing OCR Service...")
print("=" * 50)

# Read the image file as bytes
# "rb" means read as binary (raw bytes, not text)
with open(IMAGE_PATH, "rb") as f:
    image_bytes = f.read()

# Run OCR on the image
result = extract_text_from_image(image_bytes)

# Print the results
print(f"Confidence Score: {result['confidence_score']}")
print(f"Word Count: {result['word_count']}")
print()
print("Extracted Text:")
print("-" * 50)
print(result['cleaned_text'])