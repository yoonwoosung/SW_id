# models/album.py — 추억 앨범(일지) 및 커뮤니티 공유 엔티티
from datetime import datetime
from models.base import db


class Album(db.Model):
    __tablename__ = 'album'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    title = db.Column(db.String(100), nullable=False, default='제목 없음')
    shape_theme = db.Column(db.String(30), nullable=False, default='shape-portrait')
    cover_theme = db.Column(db.String(30), nullable=False, default='cover-green')
    paper_theme = db.Column(db.String(30), nullable=False, default='paper-white')
    inner_page_count = db.Column(db.Integer, nullable=False, default=2)
    pages_data = db.Column(db.Text(length=4294967295), nullable=True)  # LONGTEXT (대용량 JSON 저장)

    # 커뮤니티(추억 광장) 공개 필드
    is_public = db.Column(db.Boolean, nullable=False, default=False)
    category = db.Column(db.String(20), nullable=False, default='all')

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('albums', cascade="all, delete-orphan", lazy=True))

    def to_dict(self, include_pages=False):
        data = {
            'id': self.id,
            'title': self.title,
            'shape_theme': self.shape_theme,
            'cover_theme': self.cover_theme,
            'paper_theme': self.paper_theme,
            'inner_page_count': self.inner_page_count,
            'is_public': self.is_public,
            'category': self.category,
            'user_nickname': self.user.nickname if self.user else '익명',
            'created_at': self.created_at.strftime('%Y-%m-%dT%H:%M:%S'),
            'updated_at': self.updated_at.strftime('%Y-%m-%dT%H:%M:%S')
        }
        import json
        try:
            parsed = json.loads(self.pages_data) if self.pages_data else []
        except (json.JSONDecodeError, TypeError):
            parsed = []

        # 커버 페이지(index 0)는 목록에서도 썸네일 렌더링에 필요하므로 항상 포함
        data['cover_page'] = parsed[0] if parsed else {}

        if include_pages:
            data['pages_data'] = parsed
        return data