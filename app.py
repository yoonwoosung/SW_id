from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "테스트 성공: Hello World!"