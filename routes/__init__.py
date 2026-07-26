# routes/ — 도메인별 라우트 모듈. register_routes(app)로 모든 라우트를 앱에 등록한다.
from routes import (experience, farm, farmer, auth, user_routes, reservation, review, volunteer, admin, recommend, nearby, course, esg, product)


def register_routes(app):
    experience.register(app)
    farm.register(app)
    farmer.register(app)
    auth.register(app)
    user_routes.register(app)
    reservation.register(app)
    review.register(app)
    volunteer.register(app)
    admin.register(app)
    recommend.register(app)
    nearby.register(app)
    course.register(app)
    esg.register(app)
    product.register(app)
