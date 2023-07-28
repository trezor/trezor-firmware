# Ethereum smart contract ABI

The EVM ABI (Application Binary Interface) uses the `(call)data` part of transactions to specify which function to call on a provided smart contract target address.


## Example data

```
a9059cbb000000000000000000000000c460622c115537f05137c407ad17b06bb115be8b0000000000000000000000000000000000000000000000000000000000000123
```
The first 4 bytes (`a9059cbb`) is what is left of the hashed function name (`transfer`) after the keccak256 digest has been truncated. There is some risk of collisions here, and some people have "mined" and registered malicious functions in order to trick users into signing something different than what they think they are signing, and having their assets stolen.

What follows in this example are two 32-byte input parameters:
* An address to transfer to - `0xC460622c115537f05137C407Ad17b06bb115bE8b`, padded to the left with zeroes.
* The token amount to transfer - `0x123`/`291`, also left-padded with zeroes.


## Present state of implementation

Preliminary support for mapping smart contract function hashes exists in `trezor-firmware/core/src/apps/ethereum/sign_tx.py`.

This lets the Trezor device parse and display the function data and parameters being called.

Right now the recognized ABIs are just those for ERC-20 tokens.


## Longer term ambition

In the future the Trezor Suite / host application could provide an ABI for a given function hash. The ABI data would be signed by trusted keys in the same way as in [Ethereum definitions](ethereum-definitions.md) so it doesn't matter if the host machine is compromised.

We could potentially also include smart contract address in the mapping for full disambiguation in the case of identical function names in muliple popular contract.

We assume that less than 1000 EVM smart contracts are called in 90% of end user cases. Only in those cases do we maintain ABI data to display the transaction parameters more nicely to the user.


### Improved display of token amounts etc

We want to display a nice UI approaching Ledger's [clear-signing](https://blog.ledger.com/clear-sign-your-worries-away/).

To minimize occurances of amounts being split between two screens, the tentative goal is to still have a list of properties, but instead of having separate properties for "toToken" and "toAmount" etc, we combine them. Taken the raw properties from the ledger ABI example...
```
{
   "function": "simpleSwap",
   "arguments": {
       "fromToken": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
       "toToken": "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",
       "fromAmount": 5830000000,
       "toAmount": 5300000000000000000,
       "expectedAmount": 5300000000000000000,
       "callees": [0xE7CbBD11bE7f993197aEF41C2D6dF6e5F6867d89],
       "exchangeData": "0xbeef",
       "startIndexes": [0, 196],
       "values": [0],
       "beneficiary": "0x2cBd03487800E5Ae9793dB8d6017D909E676780A",
       "referrer": "ledger2",
       "useReduxToken": false
   }
}
```

...our possible decoding data for that contract could be something like:
```
{
   "title": "Swap tokens",
   "properties":
   [
       # Automatically consumes parameters "fromAmount" and "fromToken"
       # so they are not displayed a 2nd time in the UI
       "from":
       {
           "type": "TokenAmount",
           "data": {
	           "token": "fromAmount",
	           "amount": "fromToken",
           }
       },
       # Consumes parameters "toAmount" and "toToken"
       "to":
       {
           "type": "TokenAmount",
           "data": {
	           "token": "toToken",
	           "amount": "toAmount",
           }
       },
       # Consumes "expectedAmount"
       "expected":
       {
           "type": "TokenAmount",
           "data": {
	           "token": "toToken",
	           "amount": "expectedAmount",
           }
       },
       # Remaining unconsumed properties are 1:1, just including type data for correct parsing and display.
       # Naming collisions are caught.
       "callees": { "type": "address[]" },
       "exchangeData": { "type": "bytes" },
       "startIndexes": { "type": "int[]" },
       "values": { "type": "int[]" },
       "beneficiary": { "type": "address" },
       "referrer": { "type": "str" },
       "useReduxToken": { "type": "bool" },
   ]
}
```

This would lead to roughly this being presented on the Trezor display:
```
Swapping tokens

from: 5830 USDC
to: 5.3 ETH
expected: 5.3 ETH
callees: [0xE7CbBD11bE7f993197aEF41C2D6dF6e5F6867d89],
exchangeData: 0xbeef,
startIndexes: [0, 196],
values: [0],
beneficiary: 0x2cBd03487800E5Ae9793dB8d6017D909E676780A,
referrer: "ledger2",
useReduxToken: false
```

If `TokenAmount.token` is unset, we could fill in the default token for the smart contract.

If token parameters do not get resolved, instead of displaying "123 UNKN" in the format string we should probably fall back to just listing the raw properties (decoded to `address` format for token, and `int` for the value).
