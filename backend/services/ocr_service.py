# ocr_service.py
# Updated to support:
# - Images: JPG, PNG, WEBP, TIFF, BMP
# - PDF files (using poppler + pdf2image)

import pytesseract
from PIL import Image
import io
import re

# Tell pytesseract where Tesseract is installed
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'


def extract_text_from_image(image_bytes: bytes) -> dict:
    """
    Takes raw image bytes and extracts text using Tesseract OCR.
    Supports JPG, PNG, WEBP, TIFF, BMP formats.
    """

    # Convert raw bytes into PIL Image
    image = Image.open(io.BytesIO(image_bytes))

    # Convert to RGB for consistent results
    image = image.convert("RGB")

    # Run OCR
    raw_text = pytesseract.image_to_string(image, lang="eng")

    # Get confidence data
    from pytesseract import Output
    data = pytesseract.image_to_data(image, output_type=Output.DICT)

    # Calculate average confidence
    confidences = [
        int(c) for c in data["conf"]
        if str(c).strip() != "-1" and str(c).strip() != ""
    ]
    avg_confidence = sum(confidences) / len(confidences) if confidences else 0
    confidence_score = round(avg_confidence / 100, 2)

    # Clean the text
    cleaned_text = clean_ocr_text(raw_text)

    return {
        "raw_text": raw_text,
        "cleaned_text": cleaned_text,
        "confidence_score": confidence_score,
        "word_count": len(cleaned_text.split()),
        "source": "image"
    }


def extract_text_from_pdf(pdf_bytes: bytes) -> dict:
    """
    Extracts text from a PDF file.
    Uses poppler to convert each page to an image,
    then runs Tesseract OCR on each page.
    """
    try:
        from pdf2image import convert_from_bytes

        # Convert PDF pages to list of PIL Images
        # poppler_path tells pdf2image where poppler is installed
        images = convert_from_bytes(
            pdf_bytes,
            poppler_path=r"C:\Users\ASUS\Downloads\Release-26.02.0-0\poppler\Library\bin"
        )

        all_text = ""
        all_confidences = []

        # Run OCR on each page
        for i, image in enumerate(images):
            image = image.convert("RGB")

            # Extract text from this page
            page_text = pytesseract.image_to_string(image, lang="eng")
            all_text += f"\n--- Page {i+1} ---\n{page_text}"

            # Get confidence for this page
            from pytesseract import Output
            data = pytesseract.image_to_data(image, output_type=Output.DICT)
            confidences = [
                int(c) for c in data["conf"]
                if str(c).strip() != "-1" and str(c).strip() != ""
            ]
            if confidences:
                all_confidences.extend(confidences)

        # Calculate overall confidence
        avg_confidence = sum(all_confidences) / len(all_confidences) if all_confidences else 0
        confidence_score = round(avg_confidence / 100, 2)

        cleaned = clean_ocr_text(all_text)

        return {
            "raw_text": all_text,
            "cleaned_text": cleaned,
            "confidence_score": confidence_score,
            "word_count": len(cleaned.split()),
            "pages": len(images),
            "source": "pdf"
        }

    except Exception as e:
        return {
            "error": str(e),
            "raw_text": "",
            "cleaned_text": "",
            "confidence_score": 0.0,
            "word_count": 0,
            "source": "pdf"
        }


def clean_ocr_text(text: str) -> str:
    """
    Cleans up raw OCR output.
    Removes empty lines, fixes common OCR mistakes,
    and normalizes whitespace.
    """

    # Remove empty lines
    lines = text.split("\n")
    non_empty_lines = [line.strip() for line in lines if line.strip()]
    cleaned = "\n".join(non_empty_lines)

    # Fix common OCR mistakes
    cleaned = cleaned.replace("|", "I")
    cleaned = cleaned.replace("{}", "0")

    # Remove multiple spaces
    cleaned = re.sub(r' +', ' ', cleaned)

    return cleaned