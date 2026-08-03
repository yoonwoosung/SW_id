# models/__init__.py — DB 테이블(엔티티) 모음. db와 모든 모델을 한 곳에서 노출한다.
# 이 패키지를 import하면 모든 모델 클래스가 SQLAlchemy 레지스트리에 등록되어
# 관계(relationship) 문자열 참조와 create_all()이 정상 동작한다.
from models.base import db
from models.user import User
from models.experience import Experience
from models.review import Review
from models.inquiry import Inquiry
from models.reservation import Application
from models.notification import Notification
from models.user_request import UserRequest
from models.proposal import Proposal
from models.click_log import ClickLog
from models.wishlist import Wishlist
from models.point_log import PointLog

__all__ = [
    'db', 'User', 'Experience', 'Review', 'Inquiry', 'Application', 'Notification',
    'UserRequest', 'Proposal', 'ClickLog', 'Wishlist', 'PointLog',
]
