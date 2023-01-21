from typing import Any

from flask import Flask
import yaml


class Config:

    _data: Any

    def __init__(self) -> None:
        self.reload()

    def reload(self):
        with open("/data/CONFIG.yaml") as f:
            self._data = yaml.full_load(f)

    def __getitem__(self, k: str):
        return self._data[k]


def create_config_app(app: Flask, config: Config):
    """
    Config-related endpoints
    """

    @app.route("/config/reload", methods=["POST"])
    def config_reload():
        """
        Reload config from disk
        """
        config.reload()
        return {"success": True}
