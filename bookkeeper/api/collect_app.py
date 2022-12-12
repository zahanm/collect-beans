from datetime import date, timedelta
import json
import logging
from time import sleep
from typing import Any

from flask import Flask, request, render_template

from .collect_plaid import PlaidCollector
from .serialise import importer_from_dict


def create_collect_app(app: Flask, config: Any):
    # Needed so that it sees my edits to the template file once this app is running
    app.config["TEMPLATES_AUTO_RELOAD"] = True

    @app.route("/collect.py")
    def collect_script():
        def account_schema(acc):
            return {
                "name": acc["name"],
                "plaid_id": acc["id"],
                "currency": acc["currency"],
            }

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

    collector = PlaidCollector(config)
    # TODO remove this
    logging.getLogger().setLevel(logging.DEBUG)

    @app.route("/collect/run", methods=["POST"])
    def collect_run():
        """
        Run a Plaid transactions / balance fetch for a particular importer,
        and insert the entries into the current ledger.
        """
        assert request.json is not None
        start = date.fromisoformat(request.json["start"])
        end = date.fromisoformat(request.json["end"])
        mode = request.json["mode"]
        assert mode == "transactions" or mode == "balance"
        importer = importer_from_dict(request.json["importer"])
        if mode == "transactions":
            # collect
            account_to_txns = collector.fetch_transactions(start, end, importer)
            # insert and write new file
            print(account_to_txns)
            # return status
            return {"returncode": 0, "errors": []}
        else:
            return {
                "returncode": 1,
                "errors": ["Balance mode is unimplemented as-yet."],
            }
