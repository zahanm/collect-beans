import yaml
from flask import Flask


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

    return app
