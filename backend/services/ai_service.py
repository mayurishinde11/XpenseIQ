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
    to extract structured expense data including GSTIN.

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
    "gstin": "GST Identification Number if present on receipt or null",
    "vendor_category_hint": "type of business e.g. restaurant, pharmacy, fuel station or null",
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

Important rules:
- For transaction_date: convert any date format to YYYY-MM-DD
- For total_amount: extract the final payable amount, numeric only
- For gstin: GSTIN format is 15 characters e.g. 27AAPFU0939F1ZV
- For line_items: extract every individual item with its price
- For confidence_score: rate how confident you are in the extraction

Receipt text:
{ocr_text}

Return ONLY the JSON object. No explanation. No markdown. No backticks.
"""

    try:
        # Send the prompt to Groq
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            # temperature=0.1 means very focused, consistent responses
            # good for structured data extraction
            temperature=0.1,
            max_tokens=1500
        )

        # Extract the text from the response
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

    vendor_name: name of the vendor
    line_items: list of items purchased
    vendor_hint: type of business if known
    returns: category and subcategory
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

Rules:
1. Use vendor name and items to determine the best category
2. Never assign Miscellaneous if a better category fits
3. Be specific with subcategory

Return ONLY a valid JSON object:
{{
    "primary_category": "category name from the list above",
    "subcategory": "specific subcategory e.g. Restaurant, Pharmacy, Fuel Station",
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


def generate_expense_report(expenses: list) -> dict:
    """
    Takes a list of expense records and generates
    an analytics report using Groq AI.

    expenses: list of expense dictionaries
    returns: structured report with insights
    """

    # Build a summary of expenses to send to AI
    expense_summary = json.dumps(expenses[:20], indent=2)

    prompt = f"""
You are an expense analytics assistant.

Given these expense records, generate a concise report.

Return ONLY a valid JSON object:
{{
    "total_spend": numeric total of all amounts,
    "transaction_count": number of expenses,
    "average_transaction": numeric average amount,
    "top_category": "category with highest spend",
    "top_vendor": "vendor with highest spend",
    "insights": [
        "insight 1 about spending pattern",
        "insight 2 about spending pattern",
        "insight 3 about spending pattern"
    ],
    "recommendations": [
        "recommendation 1 to reduce costs",
        "recommendation 2 to reduce costs"
    ]
}}

Expense records:
{expense_summary}

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
            temperature=0.3,
            max_tokens=1000
        )

        response_text = response.choices[0].message.content.strip()

        if response_text.startswith("```"):
            response_text = re.sub(r'^```[a-z]*\n?', '', response_text)
            response_text = re.sub(r'\n?```$', '', response_text)
            response_text = response_text.strip()

        report = json.loads(response_text)

        return {
            "status": "success",
            "data": report
        }

    except Exception as e:
        return {
            "status": "error",
            "error": f"Report generation error: {str(e)}"
        }