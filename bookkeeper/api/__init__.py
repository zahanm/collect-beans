import yaml
from flask import Flask

from pathlib import Path


def create_app():
    app = Flask(__name__)

    with open("/data/CONFIG.yaml") as f:
        config = yaml.full_load(f)

    @app.route("/")
    def hello():
        return {
            "message": "Hello, World out there!",
            "test-config": list(config["categories"].keys())[0],
        }

    @app.route("/get_progress")
    def progress():
        data = Path("/data")
        return {
            "destination_file": None,
            "main_file": None,
            "journal_files": [p.name for p in data.glob("*.beancount")],
        }

    return app
