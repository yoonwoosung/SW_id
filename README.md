# FarmLink: 체험형 농산물 직거래 플랫폼

## 1. 프로젝트 소개 (Project Introduction)

**FarmLink**는 농산물 과잉 생산 및 산지 폐기 문제를 해결하기 위해 탄생한 위치 기반 '체험형' 농산물 직거래 플랫폼입니다. 소비자는 농장에 방문하여 직접 수확하는 등 다양한 체험을 할 수 있고, 농가는 새로운 수익 모델을 창출하며 농산물 폐기를 줄일 수 있습니다. 이를 통해 농가와 소비자가 상생하는 지속가능한 농업 생태계를 구축하고자 합니다.

## 2. 주요 기능 (Key Features)

### 🌱 일반 사용자 (Experiencers)
- **회원가입 및 로그인**: 일반 사용자로 가입하여 모든 서비스를 이용할 수 있습니다.
- **농장 체험 및 봉사 탐색**: 지도 기반으로 주변 농장의 체험 및 봉사활동을 쉽게 찾아볼 수 있습니다.
- **체험/봉사 신청**: 원하는 날짜와 시간을 선택하여 간편하게 체험이나 봉사를 신청할 수 있습니다.
- **신청 내역 관리**: '내 정보' 페이지에서 자신의 신청 현황을 확인하고 관리할 수 있습니다.
- **후기 및 문의 작성**: 참여한 체험에 대한 후기를 남기거나 궁금한 점을 농장주에게 문의할 수 있습니다.

### 🚜 농장주 (Farmers)
- **농장주 전용 회원가입**: 농장주로 가입하여 자신의 농장을 등록하고 관리할 수 있습니다.
- **농장 및 체험 등록**: 농장 정보, 체험 프로그램, 봉사자 모집 공고 등을 직접 등록하고 수정할 수 있습니다.
- **농장주 대시보드**: 예약 현황, 방문객 통계, 평균 별점 등 농장 운영에 필요한 핵심 정보를 한눈에 파악할 수 있습니다.
- **예약 관리**: 달력(FullCalendar)을 통해 날짜별 예약자 정보를 시각적으로 확인하고 관리할 수 있습니다.
- **1365 연계 봉사**: 봉사활동 시간을 공식적으로 인정받을 수 있는 기능을 제공합니다.

## 3. 기술 스택 (Tech Stack)

- **Backend**: Python, Flask, SQLAlchemy
- **Database**: MySQL
- **Frontend**: HTML, CSS, JavaScript, Bootstrap, jQuery
- **APIs & Libraries**: Kakao Maps API, FullCalendar.js, Font Awesome
- **Deployment**: PythonAnywhere

## 4. 로컬 실행 방법 (How to Run)

### Prerequisites
- Python 3.x
- MySQL

### Installation
1.  **프로젝트 클론**
    ```bash
    git clone https://github.com/your-username/FarmLink.git
    cd FarmLink
    ```

2.  **가상 환경 생성 및 활성화**
    ```bash
    python -m venv venv
    source venv/bin/activate  # Linux/macOS
    .\venv\Scripts\activate  # Windows
    ```

3.  **의존성 설치**
    ```bash
    pip install -r requirements.txt
    ```

### Configuration
1.  **환경 변수 설정**:
    `app.py` 파일 내에서 직접 수정하거나 환경 변수를 설정합니다. 데이터베이스 정보와 Kakao API 키가 필요합니다.

    *   `SECRET_KEY`: Flask 애플리케이션의 시크릿 키
    *   `DB_USERNAME`, `DB_PASSWORD`, `DB_HOSTNAME`, `DB_NAME`: MySQL 데이터베이스 연결 정보
    *   `KAKAO_API_KEY`: Kakao Maps API 사용을 위한 API 키

    **예시 (`app.py` 내 직접 설정):**
    ```python
    app.secret_key = 'your-secret-key'
    db_username = 'your_db_user'
    db_password = 'your_db_password'
    db_hostname = 'localhost'
    db_name     = 'farmlink_db'
    app.config['KAKAO_API_KEY'] = 'your_kakao_api_key'
    ```

### Running the Application
1.  **데이터베이스 테이블 생성**:
    Python 인터프리터를 실행하고 다음 코드를 입력하여 테이블을 생성합니다.
    ```python
    from app import app, db
    with app.app_context():
        db.create_all()
    ```

2.  **Flask 서버 실행**:
    ```bash
    flask run
    ```
    또는
    ```bash
    python app.py
    ```
    서버가 실행되면 웹 브라우저에서 `http://127.0.0.1:5000`으로 접속할 수 있습니다.

## 5. 데이터베이스 (Database)

이 프로젝트는 **MySQL**을 관계형 데이터베이스로 사용합니다. 모든 테이블 모델은 `app.py` 파일 내에 `db.Model`을 상속받는 클래스로 정의되어 있습니다. `db.create_all()` 명령어를 통해 정의된 모델에 따라 데이터베이스에 테이블이 자동으로 생성됩니다.

## 6. 프로젝트 구조 (Project Structure)

```
.
├── app.py              # Flask 메인 애플리케이션 파일 (라우트, 모델 정의)
├── requirements.txt    # Python 의존성 목록
├── README.md           # 프로젝트 설명 파일
├── static/             # 정적 파일 (CSS, JS, 이미지)
│   ├── css/
│   ├── js/
│   └── uploads/        # 사용자가 업로드한 파일 (프로필, 농장 사진 등)
└── templates/          # HTML 템플릿 파일
    ├── index.html      # 메인 페이지
    ├── login.html      # 로그인 페이지
    ├── register.html   # 회원가입 페이지
    ├── my_farm.html    # 농장주 대시보드
    └── ...             # 기타 페이지 템플릿
```