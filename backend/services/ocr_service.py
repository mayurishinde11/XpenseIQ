# ocr_service.py
# This file handles everything related to OCR.
# It takes an image file, reads the text from it,
# and returns clean raw text for the AI pipeline to process.

import pytesseract
from PIL import Image
import io
import re

# This line tells pytesseract WHERE Tesseract is installed
# on this Windows machine. Without this line, pytesseract
# cannot find Tesseract and will throw an error.
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'


def extract_text_from_image(image_bytes: bytes) -> dict:
    """
    Takes raw image bytes and extracts text using Tesseract OCR.
    
    image_bytes: the raw binary content of an image file
    returns: a dictionary with extracted text and confidence score
    """

    # Step 1 — Convert raw bytes into a PIL Image object
    # io.BytesIO wraps the bytes so PIL can read them
    # like a file. PIL = Python Imaging Library (Pillow)
    image = Image.open(io.BytesIO(image_bytes))

    # Step 2 — Convert image to RGB
    # Some images are RGBA (with transparency) or grayscale.
    # Tesseract works best with RGB images.
    # Converting ensures consistent results.
    image = image.convert("RGB")

    # Step 3 — Run OCR on the image
    # pytesseract.image_to_string() sends the image to
    # Tesseract and gets back the extracted text as a string
    # lang="eng" means we're reading English text
    raw_text = pytesseract.image_to_string(image, lang="eng")

    # Step 4 — Get confidence data
    # image_to_data() returns detailed information about
    # every word Tesseract detected, including confidence scores
    # output_type=Output.DICT gives us a Python dictionary
    from pytesseract import Output
    data = pytesseract.image_to_data(image, output_type=Output.DICT)

    # Step 5 — Calculate average confidence score
    # Tesseract gives each word a confidence from 0 to 100
    # We filter out -1 values (which mean no text was detected)
    # and calculate the average confidence across all words
    confidences = [
        int(c) for c in data["conf"]
        if str(c).strip() != "-1" and str(c).strip() != ""
    ]

    # If we got confidence values, calculate average
    # Otherwise default to 0
    avg_confidence = sum(confidences) / len(confidences) if confidences else 0

    # Convert from 0-100 scale to 0.0-1.0 scale
    confidence_score = round(avg_confidence / 100, 2)

    # Step 6 — Clean the raw text
    # OCR output often has extra spaces, blank lines, and noise
    # We pass it through our cleaning function
    cleaned_text = clean_ocr_text(raw_text)

    # Step 7 — Return results as a dictionary
    return {
        "raw_text": raw_text,
        "cleaned_text": cleaned_text,
        "confidence_score": confidence_score,
        "word_count": len(cleaned_text.split())
    }


def clean_ocr_text(text: str) -> str:
    """
    Cleans up raw OCR output.
    OCR often produces noisy text with extra spaces,
    weird characters, and blank lines.
    This function normalizes it.
    """

    # Remove lines that are completely empty or just whitespace
    lines = text.split("\n")
    non_empty_lines = [line.strip() for line in lines if line.strip()]

    # Join lines back together
    cleaned = "\n".join(non_empty_lines)

    # Fix common OCR mistakes
    # OCR often confuses these character pairs:
    cleaned = cleaned.replace("|", "I")   # pipe → capital I
    cleaned = cleaned.replace("{}","0")   # curly braces → zero

    # Remove multiple spaces in a row, replace with single space
    cleaned = re.sub(r' +', ' ', cleaned)

    return cleaned


def extract_text_from_pdf(pdf_bytes: bytes) -> dict:
    """
    Extracts text from a PDF file.
    Converts each PDF page to an image, then runs OCR on it.
    """
    try:
        # We use pdf2image library to convert PDF pages to images
        from pdf2image import convert_from_bytes
        
        # Convert PDF bytes to a list of PIL Images
        # Each page becomes one image
        images = convert_from_bytes(pdf_bytes)

        all_text = ""
        total_confidence = 0

        # Run OCR on each page
        for i, image in enumerate(images):
            image = image.convert("RGB")
            page_text = pytesseract.image_to_string(image, lang="eng")
            all_text += f"\n--- Page {i+1} ---\n{page_text}"
            total_confidence += 0.85

        avg_confidence = total_confidence / len(images) if images else 0
        cleaned = clean_ocr_text(all_text)

        return {
            "raw_text": all_text,
            "cleaned_text": cleaned,
            "confidence_score": round(avg_confidence, 2),
            "word_count": len(cleaned.split()),
            "pages": len(images)
        }

    except ImportError:
        return {
            "error": "pdf2image not installed",
            "raw_text": "",
            "cleaned_text": "",
            "confidence_score": 0.0,
            "word_count": 0
        }