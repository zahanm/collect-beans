import base64
import datetime
import json
import os
import time

from flask import Flask, render_template, request, jsonify, send_file
import plaid

# Get Plaid API keys from https://dashboard.plaid.com/account/keys
PLAID_CLIENT_ID = os.getenv("PLAID_CLIENT_ID")
PLAID_SECRET = os.getenv("PLAID_SECRET")
# Use 'sandbox' to test with Plaid's Sandbox environment (username: user_good,
# password: pass_good)
# Use `development` to test with live users and credentials and `production`
# to go live
PLAID_ENV = os.getenv("PLAID_ENV", "sandbox")
# PLAID_PRODUCTS is a comma-separated list of products to use when initializing
# Link. Note that this list must contain 'assets' in order for the app to be
# able to create and retrieve asset reports.
PLAID_PRODUCTS = [
    pp.strip() for pp in os.getenv("PLAID_PRODUCTS", "transactions").split(",")
]

# PLAID_COUNTRY_CODES is a comma-separated list of countries for which users
# will be able to select institutions from.
PLAID_COUNTRY_CODES = [
    cc.strip() for cc in os.getenv("PLAID_COUNTRY_CODES", "US").split(",")
]


PLAID_CLIENT_NAME = "Bean Collector"
PLAID_LANGUAGE = "en"

client = plaid.Client(
    client_id=PLAID_CLIENT_ID,
    secret=PLAID_SECRET,
    environment=PLAID_ENV,
    api_version="2020-09-14",
)

app = Flask(__name__)


@app.route("/")
def index():
    return send_file("static/index.html")


@app.route("/index.js")
def index_scripts():
    return render_template(
        "index.js",
        plaid_products=",".join(PLAID_PRODUCTS),
    )


access_token = None

# Exchange token flow - exchange a Link public_token for
# an API access_token
# https://plaid.com/docs/#exchange-token-flow
@app.route("/get_access_token", methods=["POST"])
def get_access_token():
    global access_token
    public_token = request.form["public_token"]
    try:
        exchange_response = client.Item.public_token.exchange(public_token)
    except plaid.errors.PlaidError as e:
        return jsonify(format_error(e))

    pretty_print_response(exchange_response)
    access_token = exchange_response["access_token"]
    return jsonify(exchange_response)


# Retrieve ACH or ETF account numbers for an Item
# https://plaid.com/docs/#auth
@app.route("/auth", methods=["GET"])
def get_auth():
    try:
        auth_response = client.Auth.get(access_token)
    except plaid.errors.PlaidError as e:
        return jsonify(
            {
                "error": {
                    "display_message": e.display_message,
                    "error_code": e.code,
                    "error_type": e.type,
                }
            }
        )
    pretty_print_response(auth_response)
    return jsonify({"error": None, "auth": auth_response})


# Retrieve Transactions for an Item
# https://plaid.com/docs/#transactions
@app.route("/transactions", methods=["GET"])
def get_transactions():
    # Pull transactions for the last 30 days
    start_date = "{:%Y-%m-%d}".format(datetime.datetime.now() + datetime.timedelta(-30))
    end_date = "{:%Y-%m-%d}".format(datetime.datetime.now())
    try:
        transactions_response = client.Transactions.get(
            access_token, start_date, end_date
        )
    except plaid.errors.PlaidError as e:
        return jsonify(format_error(e))
    pretty_print_response(transactions_response)
    return jsonify({"error": None, "transactions": transactions_response})


# Retrieve Identity data for an Item
# https://plaid.com/docs/#identity
@app.route("/identity", methods=["GET"])
def get_identity():
    try:
        identity_response = client.Identity.get(access_token)
    except plaid.errors.PlaidError as e:
        return jsonify(
            {
                "error": {
                    "display_message": e.display_message,
                    "error_code": e.code,
                    "error_type": e.type,
                }
            }
        )
    pretty_print_response(identity_response)
    return jsonify({"error": None, "identity": identity_response})


# Retrieve real-time balance data for each of an Item's accounts
# https://plaid.com/docs/#balance
@app.route("/balance", methods=["GET"])
def get_balance():
    try:
        balance_response = client.Accounts.balance.get(access_token)
    except plaid.errors.PlaidError as e:
        return jsonify(
            {
                "error": {
                    "display_message": e.display_message,
                    "error_code": e.code,
                    "error_type": e.type,
                }
            }
        )
    pretty_print_response(balance_response)
    return jsonify({"error": None, "balance": balance_response})


# Retrieve an Item's accounts
# https://plaid.com/docs/#accounts
@app.route("/accounts", methods=["GET"])
def get_accounts():
    try:
        accounts_response = client.Accounts.get(access_token)
    except plaid.errors.PlaidError as e:
        return jsonify(
            {
                "error": {
                    "display_message": e.display_message,
                    "error_code": e.code,
                    "error_type": e.type,
                }
            }
        )
    pretty_print_response(accounts_response)
    return jsonify({"error": None, "accounts": accounts_response})


# Create and then retrieve an Asset Report for one or more Items. Note that an
# Asset Report can contain up to 100 items, but for simplicity we're only
# including one Item here.
# https://plaid.com/docs/#assets
@app.route("/assets", methods=["GET"])
def get_assets():
    try:
        asset_report_create_response = client.AssetReport.create([access_token], 10)
    except plaid.errors.PlaidError as e:
        return jsonify(
            {
                "error": {
                    "display_message": e.display_message,
                    "error_code": e.code,
                    "error_type": e.type,
                }
            }
        )
    pretty_print_response(asset_report_create_response)

    asset_report_token = asset_report_create_response["asset_report_token"]

    # Poll for the completion of the Asset Report.
    num_retries_remaining = 20
    asset_report_json = None
    while num_retries_remaining > 0:
        try:
            asset_report_get_response = client.AssetReport.get(asset_report_token)
            asset_report_json = asset_report_get_response["report"]
            break
        except plaid.errors.PlaidError as e:
            if e.code == "PRODUCT_NOT_READY":
                num_retries_remaining -= 1
                time.sleep(1)
                continue
            return jsonify(
                {
                    "error": {
                        "display_message": e.display_message,
                        "error_code": e.code,
                        "error_type": e.type,
                    }
                }
            )

    if asset_report_json == None:
        return jsonify(
            {
                "error": {
                    "display_message": "Timed out when polling for Asset Report",
                    "error_code": e.code,
                    "error_type": e.type,
                }
            }
        )

    asset_report_pdf = None
    try:
        asset_report_pdf = client.AssetReport.get_pdf(asset_report_token)
    except plaid.errors.PlaidError as e:
        return jsonify(
            {
                "error": {
                    "display_message": e.display_message,
                    "error_code": e.code,
                    "error_type": e.type,
                }
            }
        )

    return jsonify(
        {
            "error": None,
            "json": asset_report_json,
            "pdf": base64.b64encode(asset_report_pdf),
        }
    )


# Retrieve investment holdings data for an Item
# https://plaid.com/docs/#investments
@app.route("/holdings", methods=["GET"])
def get_holdings():
    try:
        holdings_response = client.Holdings.get(access_token)
    except plaid.errors.PlaidError as e:
        return jsonify(
            {
                "error": {
                    "display_message": e.display_message,
                    "error_code": e.code,
                    "error_type": e.type,
                }
            }
        )
    pretty_print_response(holdings_response)
    return jsonify({"error": None, "holdings": holdings_response})


# Retrieve Investment Transactions for an Item
# https://plaid.com/docs/#investments
@app.route("/investment_transactions", methods=["GET"])
def get_investment_transactions():
    # Pull transactions for the last 30 days
    start_date = "{:%Y-%m-%d}".format(datetime.datetime.now() + datetime.timedelta(-30))
    end_date = "{:%Y-%m-%d}".format(datetime.datetime.now())
    try:
        investment_transactions_response = client.InvestmentTransactions.get(
            access_token, start_date, end_date
        )
    except plaid.errors.PlaidError as e:
        return jsonify(format_error(e))
    pretty_print_response(investment_transactions_response)
    return jsonify(
        {"error": None, "investment_transactions": investment_transactions_response}
    )


# Retrieve high-level information about an Item
# https://plaid.com/docs/#retrieve-item
@app.route("/item", methods=["GET"])
def item():
    item_response = client.Item.get(access_token)
    institution_response = client.Institutions.get_by_id(
        item_response["item"]["institution_id"], country_codes=PLAID_COUNTRY_CODES
    )
    pretty_print_response(item_response)
    pretty_print_response(institution_response)
    return jsonify(
        {
            "error": None,
            "item": item_response["item"],
            "institution": institution_response["institution"],
        }
    )


@app.route("/set_access_token", methods=["POST"])
def set_access_token():
    global access_token
    access_token = request.form["access_token"]
    item = client.Item.get(access_token)
    return jsonify({"error": None, "item_id": item["item"]["item_id"]})


# Create link_token flow - make a temporary link_token
# that the client Link will use to talk to Plaid
# https://plaid.com/docs/api/tokens/#linktokencreate
@app.route("/create_link_token", methods=["POST"])
def create_link_token():
    configs = {
        "user": {"client_user_id": "1"},
        "products": PLAID_PRODUCTS,
        "client_name": PLAID_CLIENT_NAME,
        "country_codes": PLAID_COUNTRY_CODES,
        "language": PLAID_LANGUAGE,
    }
    if access_token != None:
        configs["access_token"] = access_token
    try:
        create_response = client.LinkToken.create(configs)
    except plaid.errors.PlaidError as e:
        return jsonify(format_error(e))
    pretty_print_response(create_response)
    return jsonify(create_response)


def pretty_print_response(response):
    print(json.dumps(response, indent=2, sort_keys=True))


def format_error(e):
    return {
        "error": {
            "display_message": e.display_message,
            "error_code": e.code,
            "error_type": e.type,
            "error_message": e.message,
        }
    }


if __name__ == "__main__":
    app.run(port=os.getenv("PORT", 5000))
