# models/__init__.py — DB 테이블(엔티티) 모음. db와 모든 모델을 한 곳에서 노출한다.
from models.base import db
from models.user import User
from models.experience import Experience
from models.review import Review
from models.inquiry import Inquiry
from models.inquiry_reply import InquiryReply  # [프 추가] 문의 답변
from models.reservation import Application
from models.notification import Notification
from models.user_request import UserRequest
from models.proposal import Proposal
from models.click_log import ClickLog          # [백 기능] 최근 본 체험 로그
from models.wishlist import Wishlist           # [백 기능] 위시리스트
from models.point_log import PointLog          # [백 기능] 포인트 시스템
from models.farm import Farm                    # [공통] 농장 정보

__all__ = [
    'db', 'User', 'Experience', 'Review', 'Inquiry', 'InquiryReply', 'Application',
    'Notification', 'UserRequest', 'Proposal', 'ClickLog', 'Wishlist', 'PointLog', 'Farm',
]