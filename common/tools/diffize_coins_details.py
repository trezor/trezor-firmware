#!/usr/bin/env python3

import json
import os
import subprocess
import tempfile

import click
import requests

LIVE_URL = "https://trezor.io/static/json/coins_details.json"
COINS_DETAILS = os.path.join(
    os.path.dirname(__file__), "..", "defs", "coins_details.json"
)


def diffize_file(coins_details, tmp):
    coins_list = list(coins_details["coins"].values())
    for coin in coins_list:
        coin.pop("marketcap_usd", None)
        links = coin.get("links", {})
        wallets = coin.get("wallet", {})
        for link in links:
            links[link] = links[link].rstrip("/")
        for wallet in wallets:
            wallet["url"] = wallet["url"].rstrip("/")

        if not coin.get("wallet"):
            coin.pop("wallet", None)

    coins_list.sort(key=lambda c: c["name"])

    for coin in coins_list:
        name = coin["name"]
        for key in coin:
            print(name, "\t", key, ":", coin[key], file=tmp)
    tmp.flush()


@click.command()
def cli():
    """Compare data from trezor.io/coins with current coins_details.json

    Shows a nicely formatted diff between the live version and the trezor-common
    version. Useful for catching auto-generation problems, etc.
    """
    live_json = requests.get(LIVE_URL).json()
    with open(COINS_DETAILS) as f:
        coins_details = json.load(f)

    Tmp = tempfile.NamedTemporaryFile
    with Tmp("w") as tmpA, Tmp("w") as tmpB:
        diffize_file(live_json, tmpA)
        diffize_file(coins_details, tmpB)
        subprocess.call(["diff", "-u", "--color=auto", tmpA.name, tmpB.name])


if __name__ == "__main__":
    cli()
