from datetime import date, timedelta
import json
import logging
from time import sleep
from typing import Any, List

from flask import Flask, request, render_template
from plaid import ApiException

from .collect_plaid import PlaidCollector
from .collect_editor import LedgerEditor
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
    logging.getLogger().setLevel(logging.INFO)

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
        errors: List[str] = []
        if mode == "transactions":
            # collect
            try:
                account_to_txns = collector.fetch_transactions(start, end, importer)
            except ApiException as e:
                errors.append(str(e.body))
            else:
                # insert and write new file
                for account, txns in account_to_txns.items():
                    try:
                        LedgerEditor.insert(config, account, txns)
                    except RuntimeError as re:
                        errors.append(str(re))
            # return status
            return {
                "importer": importer.name,
                "returncode": len(errors),
                "errors": errors,
            }
        else:
            return {
                "importer": importer.name,
                "returncode": 1,
                "errors": ["Balance mode is unimplemented as-yet."],
            }
