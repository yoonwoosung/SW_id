담당자 A: PM / 백엔드 리드
프로젝트의 뼈대와 규칙을 세우고, 전체 흐름을 관리하는 역할입니다.

코드 및 설정 (Code & Configuration)

GitHub Repository: 프로젝트 전체 소스코드를 관리할 저장소를 생성하고, 초기 브랜치(main, develop)를 설정합니다.

app.py (초기 버전): Flask 앱의 기본 구조를 만들고, 담당자 B와 C가 작업할 페이지들의 가상 URL 경로(라우팅)를 미리 정의합니다.

dummy_data.py: 앱에서 사용할 농장, 체험 정보 등 모든 가상 데이터의 최종 구조(Key-Value 형식 등)를 확정하고 파일을 생성합니다.

문서 및 관리 (Docs & Management)

GitHub Issues: 팀원들이 수행할 개별 작업들을 이슈로 등록하여 업무를 할당하고 진행 상황을 추적합니다.

발표 자료 (PPT): 프로젝트의 최종 결과물을 발표할 PPT를 제작하고 발표를 총괄합니다.

담당자 B: 풀스택 개발자 (체험자 기능)
소비자가 앱을 사용하며 접하게 될 모든 핵심 화면과 기능을 개발합니다.

HTML 파일 (in templates 폴더)

index.html: 프로젝트의 메인 페이지. dummy_data.py의 농장 목록을 보여주고, 카카오맵 위에 위치를 표시합니다.

detail_experience.html: 개별 농장의 상세 정보를 보여주는 페이지입니다.

volunteer_apply.html: 체험이나 봉사를 신청하는 양식이 포함된 페이지입니다.

Python 코드 (in app.py)

위에 명시된 3개 HTML 페이지(index, detail_experience, volunteer_apply)를 실제로 웹에 띄워주는 Flask 로직을 작성합니다.

JavaScript 코드 (in static/js 폴더)

카카오맵 API 연동 스크립트: index.html에서 농장 위치 데이터를 받아와 지도에 여러 개의 핀(마커)을 표시하는 기능을 구현합니다.

담당자 C: 풀스택 개발자 (농장주/관리자 기능)
농장주와 관리자를 위한 페이지와, 프로젝트의 핵심 시연 기능을 책임집니다.

HTML 파일 (in templates 폴더)

farmer_dashboard.html: 농장주가 예약 현황을 볼 수 있는 대시보드 UI를 개발합니다.

farmer_register.html: 농장주가 자신의 농장과 체험을 등록하는 페이지 UI를 개발합니다.

admin.html (가칭): 관리자가 1365 봉사 실적을 관리하는 페이지 UI를 개발합니다.

Python 코드 (in app.py)

'1365 실적 다운로드' 기능: admin.html 페이지에서 특정 버튼을 클릭하면, 담당자 D가 미리 만들어 둔 샘플 엑셀(CSV) 파일을 사용자가 다운로드할 수 있도록 하는 Flask 로직을 구현합니다. (핵심 기능)

담당자 D: UI/UX 및 배포 담당
사용자가 쾌적하게 앱을 사용하도록 디자인을 입히고, 최종 결과물을 외부 서버에 공개합니다.

CSS 및 디자인 에셋 (in static 폴더)

static/css/style.css: 웹사이트 전반에 적용될 공통 디자인(폰트, 색상, 버튼 모양 등)을 코드로 작성합니다.

templates/layout.html: 모든 HTML 파일의 기본이 될 공통 상단 메뉴(네비게이션 바), 하단 정보(푸터) 등을 포함한 기본 레이아웃 템플릿을 제작합니다.

기타 파일

샘플 엑셀/CSV 파일: '1365 실적 다운로드' 기능 시연에 사용될 가상의 봉사활동 실적 데이터 파일을 제작합니다. (sample_data.csv 등)

테스트 및 배포 (QA & Deployment)

QA 활동: 개발된 모든 기능을 사용자 입장에서 직접 사용해보며 버그를 찾고, 불편한 점을 기록하여 팀원들에게 공유합니다.

서버 배포: 완성된 Flask 프로젝트를 PythonAnywhere와 같은 무료 호스팅 서비스에 업로드하여 실제 인터넷 주소로 접속할 수 있도록 만듭니다.



기능
my_farm_project/
├── app.py              # (두뇌🧠) URL 접속 처리, 데이터 가공, HTML 연결 등 핵심 로직 담당
├── dummy_data.py       # (임시 창고📦) 실제 DB를 대신할 가짜 데이터 보관 및 제공

├── templates/          # (얼굴🎭) 사용자가 보는 모든 HTML 페이지의 원본 파일 보관
│   ├── layout.html         # (공통 뼈대) 모든 페이지에 공통으로 들어갈 헤더/메뉴 등 기본 틀
│   ├── index.html          # (체험자 메인) 전체 농장 체험 목록을 보여주는 첫 화면
│   ├── detail_experience.html # (체험 상세) 단일 농장 체험의 상세 정보를 표시
│   │
│   ├── farmer_dashboard.html # (농부 메인) 농부가 등록한 자신의 체험 목록을 보는 화면
│   ├── farmer_register.html  # (농부 등록) 새로운 체험을 등록하는 입력 폼
│   │
│   ├── volunteer_apply.html    # (봉사자 메인) 지원 가능한 봉사활동 목록을 표시
│   ├── volunteer_detail.html   # (봉사 상세) 단일 봉사활동의 상세 정보와 날짜 선택 기능
│   └── volunteer_myinfo.html   # (봉사자 내정보) 자신의 봉사 신청 현황을 확인
│
└── static/             # (옷과 장식🎨) 디자인(CSS), 기능(JS), 이미지 등 정적 파일 보관
    ├── css/
    │   └── style.css       # (디자이너) 웹사이트의 색상, 글꼴, 레이아웃 등 전반적인 디자인 정의
    └── js/
        └── main.js         # (기능 전문가) 날짜 선택, 시간 계산 등 동적인 사용자 인터랙션 담당


담당부분 정리
my_farm_farm_project/
├── app.py              # (담당자 A) 전체 구조 설계, (담당자 B, C) 각자 맡은 기능의 라우트 로직 구현
├── dummy_data.py       # (담당자 A) 데이터 구조 최종 확정

├── templates/          # (담당자 B, C, D) 각 담당자가 자신의 페이지 UI 개발
│   ├── layout.html         # (담당자 D) 모든 페이지의 공통 뼈대 설계 및 제작
│   ├── index.html          # (담당자 B) 체험자 메인 페이지 개발
│   ├── detail_experience.html # (담당자 B) 체험 상세 페이지 개발
│   │
│   ├── farmer_dashboard.html # (담당자 C) 농장주 대시보드 UI 개발
│   ├── farmer_register.html  # (담당자 C) 농장주 체험 등록 페이지 UI 개발
│   │
│   ├── volunteer_apply.html    # (담당자 B) 체험 신청(봉사) 페이지 개발
│   ├── volunteer_detail.html   # (담당자 B) 봉사 상세 페이지 개발
│   └── volunteer_myinfo.html   # (담당자 B) 봉사자 '내 정보' 페이지 개발
│
└── static/             # (담당자 D) 웹사이트의 전체적인 디자인 및 정적 파일 총괄
    ├── css/
    │   └── style.css       # (담당자 D) 공통 디자인 시스템 개발
    └── js/
        └── main.js         # (담당자 B) 카카오맵 API 연동 등 체험자 기능 관련 JS 개발
