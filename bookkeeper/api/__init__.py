from typing import Optional
from pathlib import Path

import yaml
from flask import Flask, request


def create_app():
    app = Flask(__name__)
    cache = Cache()

    with open("/data/CONFIG.yaml") as f:
        config = yaml.full_load(f)

    @app.route("/")
    def hello():
        return {
            "message": "Hello, World out there!",
            "test-config": list(config["categories"].keys())[0],
        }

    @app.route("/progress", methods=["GET", "POST"])
    def progress():
        if request.method == "POST":
            cache.reset()
            cache.op = "sort"
            cache.destination_file = request.form.get("destination_file")
            cache.main_file = request.form.get("main_file")
        data = Path("/data")
        return {
            "destination_file": cache.destination_file,
            "main_file": cache.main_file,
            "journal_files": [p.name for p in data.glob("*.beancount")],
        }

    return app


class Cache:
    op: Optional[str] = None
    destination_file: Optional[str] = None
    main_file: Optional[str] = None

    def reset(self):
        self.op = None
        self.destination_file = None
        self.main_file = None
