from flask import Flask
from flask_cors import CORS

from .sort_app import create_sort_app
from .collect_app import create_collect_app
from .config_app import Config, create_config_app


def create_app():
    app = Flask(__name__)
    config = Config()

    # Make sure each API is available from other origins
    CORS(app)

    create_config_app(app, config)
    create_sort_app(app, config)
    create_collect_app(app, config)

    return app
