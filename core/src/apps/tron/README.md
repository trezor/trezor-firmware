# TRON [WIP]

Tron is an EVM like network that allows for nearly free token transfers like `USDT` etc. It achieves this by using `Bandwidth` and `Energy` for transfers, instead of `Gas` in Ethereum. `Bandwidth` is used for native `TRX` transfer, while `Energy` is used for `TRC-20` tokens like `Tether - USDT` etc.

It uses `Protobuf` for encoding its transactions. Each transaction contains its main operation as a `contract`[^1] along with supported data like expiration timestamp, block hash reference[^2], etc.

[`TronWeb` implementation](https://github.com/tronprotocol/tronweb) should be used as source of truth. The documentation on [tron.network](developers.tron.network) and [Tronprotocol](https://github.com/tronprotocol) were incorrect in some places.

## Implementation Notes

Transaction signing begins by sending `TronSignTx` message that contains the header information, including the BIP32 path to the key (e.g. `m/44h/195h/0h/0/0`). Trezor then awaits the contract to be included in the transaction as another message (e.g. `TronTransferContract`). When a valid contract is received, Trezor signs the `raw_data` part of the final transaction and sends the signature in the `TronSignature` message.

## Fees

The `Bandwidth` consumed for processing any transaction is equal to the size of the transaction, i.e. 250 byte transaction = 250 Bandwidth points.
`Energy` is consumed only on smart contract invocation calls like `TRC-20` tokens are being transferred. If the user has sufficient `Energy` and `Bandwidth` for a transaction, they generally don't have to pay any fee[^3]. If they lack either, some `TRX` is burned to pay for the remaining resource.

### Capping fees

TRON only allows a maximum limit on the Energy **cost** using the `fee_limit` field in any transaction. It is displayed in `SUN` and only limits the `TRX` to be burned when the `Energy` is insufficient.

TRON also allows for [energy cost sharing](https://developers.tron.network/docs/energy-consumption-mechanism#tron-energy-sharing-mechanism) between the caller and the deployer of the smartcontract. The `fee_limit` only applies to the caller.

For native TRX transfer via `TransferContract`, there is no way to cap the `Bandwidth` consumption or tentative `TRX` that could be burned to make up for `Bandwidth` deficit.
Therefore, we do not show any fees to the user on the device. The host application like Trezor Suite, should display potential resource consumption numbers.

## Features supported

- [X] Generate addresses for Receiving `TRX` or other tokens.
- [X] `TransferContract`: Sending `TRX`
- [X] `TriggerSmartContract`: Send `USDT`, `USDD`, etc.
- [ ] `FreezeBalanceV2`: Stake `TRX` to get more `Bandwidth` or `Energy`
- [ ] `UnfreezeBalanceV2`: Unstake frozen `TRX`

### Notes

[^1]: It is encoded as a list to support multiple contracts in a transaction in future. Currently only one contract is supported per transaction.
[^2]: TRON uses block hash reference for avoiding cross-chain replay attacks unlike using chain_ID while signing [EIP-155]
[^3]: There are other fees charged for using other features like `1 TRX` for adding a `Note` to the transaction, etc.


## Appendix

### Explanation for the 2 step message

- Tron using Protobuf is _almost_ a blessing.
- The simplest design would be to send the transaction protobuf message, parse it correctly and sign it. The only missing info in that message would be the key derivation path. If we plug it in the transaction message itself, it would disturb the final protobuf encoding (There would be a way to remove it and re-encode but that's not necessarily better).
- So the natural second idea would be to send the derivation path prior to the transaction. Having compromised with the 2 step message already, we can make it prettier by sending the 'top part' of the transaction along with the derivation path. This 'top part' is contract agnostic, thus making it a pretty denominator to any command we (will) support. The second message thus simply becomes the contract.
