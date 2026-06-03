# ai_service.py
# This file handles all communication with Groq AI.
# Groq is free, fast, and works perfectly in India.
# We use the llama-3.3-70b-versatile model which is
# excellent at structured data extraction.

from groq import Groq
import json
import re
from config import GROQ_API_KEY

# Initialize the Groq client with our API key
client = Groq(api_key=GROQ_API_KEY)


def extract_expense_data(ocr_text: str) -> dict:
    """
    Takes raw OCR text from a receipt and uses Groq AI
    to extract structured expense data.

    ocr_text: the cleaned text from our OCR service
    returns: structured dictionary with all expense fields
    """

    prompt = f"""
You are an AI that extracts structured data from receipt/bill text.

Extract the following fields from the receipt text below.
If a field cannot be found, use null.

Return ONLY a valid JSON object with these exact fields:
{{
    "vendor_name": "name of the shop or business",
    "transaction_date": "date in YYYY-MM-DD format",
    "total_amount": numeric value only,
    "subtotal": numeric value only or null,
    "tax_amount": numeric value only or null,
    "tax_type": "GST or VAT or null",
    "currency_code": "INR or USD etc",
    "payment_method": "Cash or UPI or Card or Unknown",
    "receipt_number": "bill/invoice number or null",
    "line_items": [
        {{
            "description": "item name",
            "quantity": numeric or null,
            "unit_price": numeric or null,
            "total_price": numeric or null
        }}
    ],
    "confidence_score": a float between 0.0 and 1.0
}}

Receipt text:
{ocr_text}

Return ONLY the JSON object. No explanation. No markdown. No backticks.
"""

    try:
        # Send the prompt to Groq
        # messages is a list of conversation turns
        # role "user" means this is our input to the AI
        # content is the actual text we're sending
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            # temperature controls randomness
            # 0.1 means very focused, consistent responses
            # good for structured data extraction
            temperature=0.1,
            max_tokens=1000
        )

        # Extract the text from the response
        # response.choices[0] is the first (and only) response
        # message.content is the actual text
        response_text = response.choices[0].message.content.strip()

        # Remove markdown backticks if AI adds them
        if response_text.startswith("```"):
            response_text = re.sub(r'^```[a-z]*\n?', '', response_text)
            response_text = re.sub(r'\n?```$', '', response_text)
            response_text = response_text.strip()

        # Parse JSON string into Python dictionary
        extracted_data = json.loads(response_text)

        return {
            "status": "success",
            "data": extracted_data
        }

    except json.JSONDecodeError as e:
        return {
            "status": "error",
            "error": f"Failed to parse AI response as JSON: {str(e)}",
            "raw_response": response_text if response_text else None
        }

    except Exception as e:
        return {
            "status": "error",
            "error": f"AI service error: {str(e)}"
        }


def classify_expense(vendor_name: str, line_items: list, vendor_hint: str = None) -> dict:
    """
    Classifies an expense into a category using Groq AI.
    """

    # Build a string of item descriptions
    items_text = ""
    if line_items:
        items_text = ", ".join([
            item.get("description", "")
            for item in line_items
            if item.get("description")
        ])

    prompt = f"""
You are an expense classification engine.

Classify this expense into one of these primary categories:
- Food & Dining
- Travel & Transport
- Health & Medical
- Office & Supplies
- Utilities
- Entertainment
- Shopping
- Education
- Finance
- Miscellaneous

Vendor: {vendor_name}
Items purchased: {items_text}
Vendor type hint: {vendor_hint or 'unknown'}

Return ONLY a valid JSON object:
{{
    "primary_category": "category name",
    "subcategory": "specific subcategory",
    "classification_confidence": float between 0.0 and 1.0,
    "classification_reasoning": "one sentence explanation"
}}

Return ONLY the JSON. No explanation. No markdown. No backticks.
"""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.1,
            max_tokens=500
        )

        response_text = response.choices[0].message.content.strip()

        # Clean markdown backticks if present
        if response_text.startswith("```"):
            response_text = re.sub(r'^```[a-z]*\n?', '', response_text)
            response_text = re.sub(r'\n?```$', '', response_text)
            response_text = response_text.strip()

        classification = json.loads(response_text)

        return {
            "status": "success",
            "data": classification
        }

    except Exception as e:
        return {
            "status": "error",
            "error": f"Classification error: {str(e)}"
        }