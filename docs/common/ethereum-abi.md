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


## Present state of implementation & longer term goal

Preliminary support for mapping smart contract function hashes exists in `trezor-firmware/core/src/apps/ethereum/sign_tx.py`.

This lets the Trezor device parse and display the function data and parameters being called.

Right now the recognized ABIs are just those for ERC-20 tokens. In the future the Trezor Suite / host application could provide an ABI for a given function hash. The ABI data would be signed by trusted keys in the same way as in [Ethereum definitions](ethereum-definitions.md) so it doesn't matter if the host machine is compromised.
