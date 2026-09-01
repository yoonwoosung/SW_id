# ============================================================================
# PythonAnywhere WSGI 진입점
# ----------------------------------------------------------------------------
# PA 대시보드 → Web 탭 → "WSGI configuration file" 링크를 열어
# 기존 내용을 전부 지우고 이 파일 내용을 그대로 붙여넣는다.
# (PA 는 이 저장소의 파일이 아니라 /var/www/<user>_pythonanywhere_com_wsgi.py 를 읽는다.
#  이 파일은 붙여넣을 원본을 형상관리하기 위해 저장소에 둔다.)
#
# ★ 아래 <user> 두 군데를 본인 PythonAnywhere 계정명으로 바꿀 것.
# ============================================================================

import sys

# 1) 프로젝트 루트를 import 경로에 추가한다.
#    PA Consoles 에서 `git clone` 한 위치와 정확히 일치해야 한다.
project_home = '/home/<user>/SW_id'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# 2) 작업 디렉터리 고정.
#    app.py 는 __file__ 기준으로 .env 를 찾으므로 필수는 아니지만,
#    상대경로를 쓰는 코드가 섞여도 안전하도록 맞춰둔다.
import os
os.chdir(project_home)

# 3) WSGI application 노출.
#    이 앱에는 create_app() 팩토리가 없고 app.py 모듈 전역에
#    app = Flask(__name__) 가 있으므로(app.py:25) 그대로 가져다 쓴다.
#    app.py 는 import 시점에 load_dotenv() 로 .env 를 읽으므로
#    여기서 환경변수를 따로 로딩할 필요가 없다.
from app import app as application  # noqa: E402

# 참고: app.py 의 db.create_all() 은 `if __name__ == '__main__':` 블록 안에 있어(app.py:83-85)
#       WSGI 로 구동될 때는 실행되지 않는다. 테이블은 서버 콘솔에서 한 번 수동 생성할 것.
