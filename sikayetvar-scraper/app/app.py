"""
Flask Uygulama Fabrikası
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from flask import Flask, send_from_directory
from flask_cors import CORS
from app.routes.api import api_bp
from config import FLASK_HOST, FLASK_PORT, FLASK_DEBUG


def create_app() -> Flask:
    app = Flask(
        __name__,
        static_folder="static",
        static_url_path="/static"
    )
    CORS(app)

    # Blueprint kaydet
    app.register_blueprint(api_bp)

    # Ana sayfa – dashboard
    @app.route("/")
    def index():
        return send_from_directory(app.static_folder, "index.html")

    @app.route("/favicon.ico")
    def favicon():
        return "", 204

    return app


def run():
    app = create_app()
    print(f"\n🚀 Dashboard: http://localhost:{FLASK_PORT}")
    print("Durdurmak için Ctrl+C\n")
    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=FLASK_DEBUG)
