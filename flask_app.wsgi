# PythonAnywhere WSGI 진입점.
# PA 대시보드 Web 탭의 "WSGI configuration file" 내용을 이 파일로 대체하거나 이 내용을 붙여넣는다.
# <user> 를 본인 PythonAnywhere 계정명으로 바꿀 것.
import sys

project_home = '/home/<user>/SW_id'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# app.py가 import 시점에 load_dotenv로 .env를 읽으므로 여기서 별도 로딩은 불필요.
# create_app() 팩토리는 없고 모듈 전역 app 객체를 그대로 WSGI application으로 노출한다.
from app import app as application
