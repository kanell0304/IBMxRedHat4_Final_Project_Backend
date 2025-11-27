# import 경로 꼬인다고 해서 주석처리 했습니다

# # app/__init__.py  (프로젝트 루트에 위치)
# import importlib, sys

# # backend.app 패키지를 불러와서
# _backend_app = importlib.import_module("IBMxRedHat4_Final_Project_Backend.app")

# # 현재 패키지 이름(app)을 backend.app 패키지 객체로 바인딩
# # 이렇게 하면 'from app.xxx import ...'가 'backend.app.xxx'로 동작함
# sys.modules[__name__] = _backend_app
