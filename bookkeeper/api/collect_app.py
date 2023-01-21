from datetime import date
import json
import logging
from pathlib import Path
import subprocess
from typing import Any, List

from flask import Flask, request, render_template
from plaid import ApiException

from .collect_plaid import PlaidCollector
from .collect_editor import LedgerEditor
from .config_app import Config
from .serialise import importer_from_dict


def create_collect_app(app: Flask, config: Config):
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
        mode = request.json["mode"]
        assert mode == "transactions" or mode == "balance"
        importer = importer_from_dict(request.json["importer"])
        errors: List[str] = []
        if mode == "transactions":
            start = date.fromisoformat(request.json["start"])
            end = date.fromisoformat(request.json["end"])
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
            # collect
            try:
                account_to_txns = collector.fetch_balance(importer)
            except ApiException as e:
                errors.append(str(e.body))
            else:
                # insert and write new file
                for account, txns in account_to_txns.items():
                    try:
                        LedgerEditor.insert(config, account, txns)
                    except RuntimeError as re:
                        errors.append(str(re))
            return {
                "importer": importer.name,
                "returncode": len(errors),
                "errors": errors,
            }

    @app.route("/collect/backup", methods=["GET", "POST"])
    def collect_backup():
        """
        Sample command:
        rclone sync --progress accounts/ backup-accounts/current --backup-dir backup-accounts/`date -I`
        """
        current_dir = Path("/data")
        backups_dir = Path("/backups")
        if request.method == "POST":
            args = [
                "rclone",
                "sync",
                str(current_dir),
                str(backups_dir / "current"),
                "--backup-dir",
                f"{backups_dir}/{date.today().isoformat()}",
                "--exclude",
                ".git/",
                "--exclude",
                "*.picklecache",
            ]
            logging.info(" ".join(args))
            subprocess.check_call(args)
        backup_ledger = backups_dir / "current" / config["files"]["current-ledger"]
        with open(backup_ledger, "r") as backup:
            old_contents = backup.read()
        with open(current_dir / config["files"]["current-ledger"], "r") as ledger:
            new_contents = ledger.read()
        return {
            "contents": {"old": old_contents, "new": new_contents},
            "timestamps": {"last_backup": backup_ledger.stat().st_mtime},
        }

    @app.route("/collect/last-imported")
    def collect_last_imported():
        accounts = request.args.getlist("accounts")
        return {
            "last": {
                acc: last.isoformat() if last else None
                for acc, last in LedgerEditor.last_imported(config, accounts).items()
            }
        }

    @app.route("/collect/other-importers")
    def collect_other_importers():
        def account_schema(acc):
            return {
                "name": acc["name"],
                "currency": acc["currency"],
            }

        def importer_schema(name, imp):
            ii = {
                "name": name,
                "downloader": imp["downloader"],
                "accounts": [
                    account_schema(acc)
                    for acc in imp["accounts"]
                    if imp["downloader"] != "plaid"
                    or "sync" not in acc
                    or acc["sync"] != request.args.get("mode", "transactions")
                ],
            }
            if "importer" in imp:
                ii["importer"] = imp["importer"]
            if "instructions" in imp:
                ii["instructions"] = imp["instructions"]
            return ii

        importers = [
            importer_schema(name, importer)
            for name, importer in config["importers"].items()
            if importer["downloader"] != "plaid"
            or any(
                [
                    acc["sync"] != request.args.get("mode", "transactions")
                    for acc in importer["accounts"]
                ]
            )
        ]

        return {"importers": importers}
