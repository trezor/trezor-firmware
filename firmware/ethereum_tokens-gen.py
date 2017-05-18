#!/usr/bin/env python3
import requests

def get_tokens():
    URL = 'https://raw.githubusercontent.com/kvhnuke/etherwallet/mercury/app/scripts/tokens/ethTokens.json'
    r = requests.get(URL)
    return r.json()

tokens = get_tokens()

subst = {
    'BeerCoin \U0001F37A': 'BEER',
    'CryptoCarbon': 'CCRB',
    'DAO_extraBalance': 'DAOe',
    'DGX 1.0': 'DGX1',
    'Unicorn \U0001F984': 'UNCRN',
}

for t in tokens:
    address, symbol, decimal = t['address'], t['symbol'], t['decimal']
    if symbol in subst:
        symbol = subst[symbol]
    address = '\\x'.join([address[i:i + 2] for i in range(0, len(address), 2)])[2:].lower()
    print('\t{"%s", "%s", %d},' % (address, symbol, decimal))
