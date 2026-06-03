# test_ai_quick.py
# Quick test to verify our Gemini AI service works correctly.
# We give it the same OCR text from our receipt and see
# what structured data it extracts.

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.ai_service import extract_expense_data, classify_expense
import json

# This is the same text our OCR extracted from the receipt
# In real usage, this comes directly from ocr_service.py
sample_ocr_text = """
JOY STORES
Egra
BILL NO.: 8023 Date: 16.11.2020
Name: Nairitee Bera
Pens 248.00
Pencils 29.00
Books 748.00
Notebooks 160.00
Craft paper 10.50
Dairies 1540.00
Total: 2735.00
"""

print("Testing AI Extraction...")
print("=" * 50)

# Test 1 - Extract expense data
result = extract_expense_data(sample_ocr_text)

if result["status"] == "success":
    print("Extraction SUCCESS")
    print(json.dumps(result["data"], indent=2))
else:
    print("Extraction FAILED")
    print(result["error"])

print()
print("=" * 50)
print("Testing AI Classification...")
print("=" * 50)

# Test 2 - Classify the expense
line_items = [
    {"description": "Pens"},
    {"description": "Pencils"},
    {"description": "Books"},
    {"description": "Notebooks"}
]

classification = classify_expense(
    vendor_name="JOY STORES",
    line_items=line_items,
    vendor_hint="stationery store"
)

if classification["status"] == "success":
    print("Classification SUCCESS")
    print(json.dumps(classification["data"], indent=2))
else:
    print("Classification FAILED")
    print(classification["error"])