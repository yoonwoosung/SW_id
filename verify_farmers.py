import os
import sys
import cv2 # OpenCV 라이브러리
import numpy as np

# 현재 스크립트 경로를 기준으로 프로젝트 경로 추가 (PythonAnywhere에서 필요)
project_home = '/home/kevin4201/FarmLink' # 본인의 PythonAnywhere 프로젝트 경로로 수정하세요.
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# 이제 app의 구성 요소를 import 할 수 있습니다.
from app import app, db, User

# 성능 개선을 위한 OpenCV 전처리 기능이 포함된 OCR 함수
def enhanced_ocr_from_pdf(pdf_bytes):
    text = ""
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            # 1. 해상도를 높여 이미지 추출
            pix = page.get_pixmap(dpi=300)
            img_bytes = pix.tobytes("png")

            # 2. OpenCV로 이미지 전처리
            img_np = np.frombuffer(img_bytes, np.uint8)
            img = cv2.imdecode(img_np, cv2.IMREAD_COLOR)
            gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            _, binary_img = cv2.threshold(gray_img, 127, 255, cv2.THRESH_BINARY)
            
            # 3. 전처리된 이미지로 OCR 수행
            preprocessed_img = Image.fromarray(binary_img)
            text += pytesseract.image_to_string(preprocessed_img, lang='kor+eng')
        
        return re.sub(r'\s+', '', text).lower()
    except Exception as e:
        print(f"PDF 처리 중 오류 발생: {e}")
        return ""

def verify_pending_farmers():
    with app.app_context():
        pending_users = User.query.filter_by(role='farmer', verification_status='pending').all()
        
        if not pending_users:
            print("인증 대기 중인 사용자가 없습니다.")
            return

        # 샘플 텍스트 로드
        try:
            sample_txt_path = os.path.join(project_home, 'sample_cert_text.txt')
            with open(sample_txt_path, 'r', encoding='utf-8') as f:
                sample_cert_text = f.read()
        except FileNotFoundError:
            print("오류: sample_cert_text.txt 파일을 찾을 수 없습니다.")
            return

        print(f"총 {len(pending_users)}명의 인증을 시작합니다.")

        for user in pending_users:
            pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], user.farmer_certificate_pdf)
            if not os.path.exists(pdf_path):
                print(f"오류: {user.email}의 PDF 파일을 찾을 수 없습니다. 경로: {pdf_path}")
                user.verification_status = 'error'
                continue
            
            try:
                with open(pdf_path, 'rb') as f:
                    pdf_bytes = f.read()
                
                # 개선된 OCR 함수 호출
                uploaded_text = enhanced_ocr_from_pdf(pdf_bytes)

                if uploaded_text and sample_cert_text in uploaded_text:
                    user.verification_status = 'verified'
                    print(f"성공: {user.email} 인증 완료.")
                else:
                    user.verification_status = 'rejected'
                    print(f"실패: {user.email} 인증 실패.")
            except Exception as e:
                print(f"오류: {user.email} 처리 중 예외 발생 - {e}")
                user.verification_status = 'error'

        db.session.commit()
        print("인증 작업 완료.")

if __name__ == '__main__':
    verify_pending_farmers()