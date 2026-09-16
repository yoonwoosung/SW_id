import os
import re
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import io

# This script is for one-time use to pre-process the sample certificate PDF.
# It extracts the text from '신청서.pdf' and saves it to 'sample_cert_text.txt'.
# The main application can then read this text file instantly without performing OCR every time.

import platform

# Tesseract OCR 경로 설정
if platform.system() == "Windows":
    # Windows용 Tesseract 경로
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
else:
    # Linux/macOS용 Tesseract 경로
    pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'

# The OCR and normalization function, copied from app.py to make this script self-contained.
def extract_and_normalize_text_from_pdf(pdf_bytes):
    text = ""
    try:
        # 1. Try text-based extraction first
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        for page in doc:
            text += page.get_text()

        # 2. If text is sparse, attempt OCR
        if len(text.strip()) < 50:
            print("Very little text found, attempting OCR...")
            text = ""
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                pix = page.get_pixmap()
                img_bytes = pix.tobytes("png")
                img = Image.open(io.BytesIO(img_bytes))
                text += pytesseract.image_to_string(img, lang='kor+eng')

        # 3. Normalize the final text
        return re.sub(r'\s+', '', text).lower()

    except Exception as e:
        print(f"An error occurred during PDF processing: {e}")
        return ""

def preprocess_sample():
    """
    Reads '신청서.pdf', extracts its text, and saves it to 'sample_cert_text.txt'.
    """
    sample_pdf_path = os.path.join(os.path.dirname(__file__), '신청서.pdf')
    output_txt_path = os.path.join(os.path.dirname(__file__), 'sample_cert_text.txt')

    print(f"Processing '{sample_pdf_path}'...")

    try:
        with open(sample_pdf_path, 'rb') as f:
            pdf_bytes = f.read()
        
        extracted_text = extract_and_normalize_text_from_pdf(pdf_bytes)

        if not extracted_text:
            print("ERROR: Could not extract any text from the PDF. 'sample_cert_text.txt' will not be created.")
            return

        with open(output_txt_path, 'w', encoding='utf-8') as f:
            f.write(extracted_text)
        
        print(f"Successfully created '{output_txt_path}' with the extracted text.")

    except FileNotFoundError:
        print(f"CRITICAL ERROR: The sample PDF file '{sample_pdf_path}' was not found.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == '__main__':
    preprocess_sample()
