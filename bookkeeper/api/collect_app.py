import json
from typing import Any

from flask import Flask, request, render_template


def create_collect_app(app: Flask, config: Any):
    # Needed so that it sees my edits to the template file once this app is running
    app.config["TEMPLATES_AUTO_RELOAD"] = True

    @app.route("/collect.py")
    def collect_script():
        def account_schema(acc):
            return {"name": acc["name"], "plaid_id": acc["id"]}

        def importer_schema(name, imp):
            return {
                "name": name,
                "op_id": imp["op-id"],
                "op_vault": imp["op-vault"],
                "institution_id": imp["institution-id"],
                "accounts": [
                    account_schema(acc)
                    for acc in imp["accounts"]
                    if acc["sync"] == request.args.get("mode", "transactions")
                ],
            }

        importers = [
            importer_schema(name, importer)
            for name, importer in config["importers"].items()
            if importer["downloader"] == "plaid"
            and any(
                [
                    acc["sync"] == request.args.get("mode", "transactions")
                    for acc in importer["accounts"]
                ]
            )
        ]
        data = {"importers": importers}
        return render_template("collect.py.jinja", data=json.dumps(data, indent=2))
