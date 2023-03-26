# Snippets


This folder is storing non-essential scripts (snippets, gists), which may however come in handy in a year or two.

These scripts do not need to have a high standard, but each of those should have a short description of what is it doing.

## [sign_tx.py](./sign_tx.py)
- signing of BTC transactions that can be spent with currently connected device
- need to specify the input UTXOs and the output address(es)
- generates a serialized transaction that can be then announced to the network

## [unify_test_files.py](./unify_test_files.py)
- enforcing some readability practices in test files and possibly adding information about paths and addresses used
- need to specify all the files to be modified and optionally the path-to-address translation file
- rewrites the files in place, or just prints the intended changes when run with `-c`

## [monero_unused_functions](./monero_unused_functions.py)
- Find functions from Monero cryptography that are not used.
