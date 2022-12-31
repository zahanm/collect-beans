from flask import Flask
from flask_cors import CORS

from .utilities import Config
from .sort_app import create_sort_app
from .collect_app import create_collect_app


def create_app():
    app = Flask(__name__)
    config = Config()

    # Make sure each API is available from other origins
    CORS(app)

    create_sort_app(app, config)
    create_collect_app(app, config)

    return app
