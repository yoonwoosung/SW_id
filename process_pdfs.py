import os
import re
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import io
from app import db, User, app

import platform

# Tesseract OCR 경로 설정
if platform.system() == "Windows":
    # Windows용 Tesseract 경로
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
else:
    # Linux/macOS용 Tesseract 경로
    pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'

def extract_and_normalize_text_from_pdf(pdf_bytes):
    text = ""
    try:
        # 1. 텍스트 기반 추출 시도
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        for page in doc:
            text += page.get_text()

        # 2. 텍스트가 거의 없다면 OCR 시도
        if len(text.strip()) < 50:
            print("텍스트가 거의 없어 OCR을 시도합니다.")
            text = ""
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                pix = page.get_pixmap()
                img_bytes = pix.tobytes("png")
                img = Image.open(io.BytesIO(img_bytes))
                text += pytesseract.image_to_string(img, lang='kor+eng')

        # 3. 최종 텍스트 정규화
        return re.sub(r'\s+', '', text).lower()

    except Exception as e:
        print(f"PDF 처리 중 오류 발생: {e}")
        return ""

def process_pending_pdfs():
    with app.app_context():
        pending_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'pending_verification')
        processed_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'processed_verification')
        os.makedirs(processed_dir, exist_ok=True)

        # --- Load the pre-processed sample certificate text ---
        sample_cert_text = ""
        try:
            sample_txt_path = os.path.join(os.path.dirname(__file__), 'sample_cert_text.txt')
            with open(sample_txt_path, 'r', encoding='utf-8') as f:
                sample_cert_text = f.read()
            if not sample_cert_text:
                print("CRITICAL ERROR: 'sample_cert_text.txt' is empty. Please run the preprocess_sample_cert.py script first.")
                return
        except FileNotFoundError:
            print("CRITICAL ERROR: 'sample_cert_text.txt' not found. Please run the preprocess_sample_cert.py script first.")
            return

        if not os.path.exists(pending_dir):
            print(f"'{pending_dir}' not found.")
            return

        for filename in os.listdir(pending_dir):
            if not filename.endswith('.pdf'):
                continue

            file_path = os.path.join(pending_dir, filename)
            
            # 이메일 정보 추출 (파일 이름 형식: farmer_cert_{email}_filename.pdf)
            match = re.search(r'farmer_cert_(.*?)_', filename)
            if not match:
                print(f"Could not extract email from filename: {filename}")
                continue
            
            email = match.group(1)
            user = User.query.filter_by(email=email).first()

            if not user:
                print(f"User with email '{email}' not found for PDF '{filename}'")
                continue

            print(f"Processing PDF for user: {email}")

            try:
                with open(file_path, 'rb') as f:
                    uploaded_text = extract_and_normalize_text_from_pdf(f.read())

                if uploaded_text and sample_cert_text in uploaded_text:
                    user.certificate_status = 'approved'
                    print(f"  -> Certificate APPROVED for {email}")
                else:
                    user.certificate_status = 'rejected'
                    print(f"  -> Certificate REJECTED for {email}")
                
                db.session.commit()

                # 처리된 파일 이동
                os.rename(file_path, os.path.join(processed_dir, filename))
                print(f"  -> Moved '{filename}' to processed directory.")

            except Exception as e:
                print(f"Error processing file {filename} for user {email}: {e}")

if __name__ == '__main__':
    print("Starting PDF processing task...")
    process_pending_pdfs()
    print("PDF processing task finished.")
