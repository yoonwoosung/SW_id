import os

# 기본 경로 설정
basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    """기본 설정 클래스"""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'mysql-secret-key-for-production')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(basedir, 'static/uploads')
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    KAKAO_API_KEY = os.environ.get('KAKAO_API_KEY', '54569873db07a9b66faf2a7be5c41a1c')

    @staticmethod
    def init_app(app):
        pass

class DevelopmentConfig(Config):
    """개발 환경 설정"""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL', 
        'mysql+mysqlconnector://root:rootpass0723@localhost/myfarm_db')

class ProductionConfig(Config):
    """운영(배포) 환경 설정"""
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    # 예: 'mysql+mysqlconnector://user:password@server_ip/prod_db'

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
