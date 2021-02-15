# Binance

MAINTAINER = Stanislav Marcinko <stanislav.marcinko@satoshilabs.com>

AUTHOR = Stanislav Marcinko <stanislav.marcinko@satoshilabs.com>

REVIEWER = Jan Matějek <jan.matejek@satoshilabs.com>

-----

Implementation is based on [binance chain documentation](https://binance-chain.github.io/blockchain.html) and tested against fixtures from [binance javascript sdk](https://github.com/binance-chain/javascript-sdk/). Only a subset of messages needed for sdk integration is implemented.

## Transactions

Binance transaction consists of a transaction message wrapped in a standard transaction structure (see documentation). One message per transaction.

Implemented subset of messages:
Place Order
Cancel Order
Transfer

## Testing

Mnemonic for recovering wallet used in binance sdk tests:
offer caution gift cross surge pretty orange during eye soldier popular holiday mention east eight office fashion ill parrot vault rent devote earth cousin
