# Examples demonstrating how to use trezorctl

Show all available [options](OPTIONS.md):

```
$ trezorctl --help
```

Retrieve features, settings and coin types supported by your device:

```
$ trezorctl get-features
```

## Bitcoin examples

Get first receiving address of first account for Bitcoin (Legacy /
non-SegWit):

```
$ trezorctl btc get-address -n "m/44h/0h/0h/0/0"
```

Get first receiving address of first account for Bitcoin (SegWit-in-P2SH):

```
$ trezorctl btc get-address -n "m/49h/0h/0h/0/0" -t p2shsegwit
```

Get first receiving address of first account for Bitcoin (native SegWit P2WPKH):

```
$ trezorctl btc get-address -n "m/84h/0h/0h/0/0" -t segwit
```

Get first receiving address of first account for Bitcoin (Taproot single-sig P2TR):

```
$ trezorctl btc get-address -n "m/86h/0h/0h/0/0" -t taproot
```

Get Legacy Bitcoin address for some account, second address in change
chain:

```
$ trezorctl btc get-address -n "m/44h/0h/3h/1/12"
```

Get public node of first Bitcoin account:

```
$ trezorctl btc get-public-node -n "m/44h/0h/0h"
```

## Signing transactions

Ask device to sign transaction. Transaction must be specified in
`tx.json` file (see [transaction format](transaction-format.md)) and
use the `btc sign-tx` command.

The command will return a signed transaction in hexadecimal format,
which can be broadcasted on the network.

```
$ trezorctl btc sign-tx tx.json
```

## Ethereum examples

Get first address of first Ethereum account:

```
$ trezorctl ethereum get-address -n "m/44h/60h/0h/0/0"
```

Sign Ethereum transaction (requires `eth-hash`, `rlp`, and `web3` packages to be
installed, `pip install trezor[ethereum]`):

```
$ trezorctl ethereum sign-tx \
    -n "m/44h/60h/0h/0/0" \
    --chain-id 1 \
    --address 0x8ea7a3fccc211ed48b763b4164884ddbcf3b0a98 \
    --value 0.1 \
    --gas-limit 21000 \
    --gas-price 20 \
    --nonce 0 \
    --data ""
```

Sign Ethereum transaction with EIP-1559 fee parameters:

```
$ trezorctl ethereum sign-tx \
    -n "m/44h/60h/0h/0/0" \
    --chain-id 1 \
    --address 0x8ea7a3fccc211ed48b763b4164884ddbcf3b0a98 \
    --value 0.1 \
    --gas-limit 21000 \
    --max-gas-fee 20 \
    --max-priority-fee 1 \
    --nonce 0 \
    --data ""
```

Sign ERC20 token transaction:

```
$ trezorctl ethereum sign-tx-erc20 \
    -n "m/44h/60h/0h/0/0" \
    --chain-id 1 \
    --token-address 0xdac17f958d2ee523a2206206994597c13d831ec7 \
    --to 0x8ea7a3fccc211ed48b763b4164884ddbcf3b0a98 \
    --amount 1.23 \
    --gas-limit 100000 \
    --gas-price 20 \
    --nonce 0
```

## Litecoin examples

Get first receiving address of first Litecoin account:

```
$ trezorctl ltc get-address -n "m/44h/2h/0h/0/0"
```

## Retrieve device entropy

Get 256 bytes of entropy from the device (not from the seed/TRNG):

```
$ trezorctl get-entropy 256 | xxd -r -p > entropy.bin
```

## Device management examples

### Set up a new device

```
$ trezorctl device setup
```

### Wipe device

**DANGER**: This will erase all data from the device!

```
$ trezorctl device wipe
```

### Load device from mnemonic

Load the device with a pre-generated mnemonic (all data will be wiped):

```
$ trezorctl device load \
  -m "your mnemonic words go here separated by spaces"
```

### Change PIN

Set new PIN:

```
$ trezorctl device change-pin
```

Remove existing PIN:

```
$ trezorctl device change-pin -r
```

### Enable/disable passphrase

Enable passphrase:

```
$ trezorctl device change-passphrase-settings -e
```

Disable passphrase:

```
$ trezorctl device change-passphrase-settings -d
```
