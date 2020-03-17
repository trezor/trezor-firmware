# trezorctl Bitcoin transaction JSON format

Since version 0.11.2, `trezorctl` allows fully offline signing of Bitcoin and
Bitcoin-like altcoin transactions encoded in a custom JSON structure. Starting with
version 0.11.6, this is the only supported format for signing.

## Structure

The structure of the JSON matches the shape of the relevant protobuf messages. See
file [messages-bitcoin.proto] for up-to-date structure.

The root is an object with the following attributes:

* __`coin_name`__: string representing the coin name as listed in [coin defs]. If
  missing, `"Bitcoin"` is used.
* __`inputs`__: array of `TxInputType` objects. Must be present.
* __`outputs`__: array of `TxOutputType` objects. Must be present.
* __`details`__: object of type `SignTx`, specifying transaction metadata. Can be
  omitted.
* __`prev_txes`__: object whose keys are hex-encoded transaction hashes, and values are
  objects of type `TransactionType`. When signing a transaction with non-SegWit inputs,
  each previous transaction must have an entry in `prev_txes`. With pure SegWit
  transactions, this field can be omitted.

See definition of the respective object types in [messages-bitcoin.proto] for
descriptions of individual fields.

[messages-bitcoin.proto]: ../../common/protob/messages-bitcoin.proto
[coin defs]: ../../common/defs/bitcoin

**Please note** that the `optional` keyword in the protobuf definition does _not_
indicate that the field can be omitted, nor does the `default` extension mean that the
default value will be used if missing.

### Derivation paths

A derivation path in the field `address_n` is encoded as an array of numbers according
to the BIP-32 specification. Use `trezorlib.tools.parse_path` to convert a string
derivation path to the corresponding array.

### Inputs

```protobuf
enum InputScriptType {
    SPENDADDRESS = 0;       // standard P2PKH address
    SPENDMULTISIG = 1;      // P2SH multisig address
    EXTERNAL = 2;           // reserved for external inputs (coinjoin)
    SPENDWITNESS = 3;       // native SegWit
    SPENDP2SHWITNESS = 4;   // SegWit over P2SH (backward compatible)
}

message TxInputType {
    repeated uint32 address_n = 1;   // BIP-32 path to derive the key from master node
    required bytes prev_hash = 2;    // hash of previous transaction output to spend by this input
    required uint32 prev_index = 3;  // index of previous output to spend
    optional bytes script_sig = 4;   // script signature, unset for tx to sign
    optional uint32 sequence = 5;    // sequence (default=0xffffffff)
    optional InputScriptType script_type = 6   ;    // defines template of input script
    optional MultisigRedeemScriptType multisig = 7; // Filled if input is going to spend multisig tx
    optional uint64 amount = 8;                     // amount of previous transaction output
    optional uint32 decred_tree = 9;                // only for Decred
    optional uint32 decred_script_version = 10;     // only for Decred
}
```

Each input must have a derivation path (`address_n`), `prev_hash` and `prev_index`
refering to the output being spent, `sequence` number, `script_type` corresponding to
the desired signature type, and `amount`.

The field `script_sig` must not be set.

The field `multisig` can be used for multisig inputs. Documenting the multisig structure is TBD. With regular inputs, `multisig` must not be set.

`decred` fields must only be set when relevant to your currency.

### Outputs

```protobuf
enum OutputScriptType {
    PAYTOADDRESS = 0;       // string address output; change is a P2PKH address
    PAYTOMULTISIG = 2;      // change output is a multisig address
    PAYTOOPRETURN = 3;      // op_return
    PAYTOWITNESS = 4;       // change output is native SegWit
    PAYTOP2SHWITNESS = 5;   // change output is SegWit over P2SH
}

message TxOutputType {
    optional string address = 1;    // destination address in Base58 encoding
    repeated uint32 address_n = 2;  // derivation path for change address
    required uint64 amount = 3;     // amount to spend in satoshis
    required OutputScriptType script_type = 4;      // output script type
    optional MultisigRedeemScriptType multisig = 5; // multisig output definition
    optional bytes op_return_data = 6;              // defines op_return data
    optional uint32 decred_script_version = 7;      // only for Decred
 
```

All outputs must have an `amount` and a `script_type`.

For normal (non-change) outputs, the field `address` must be set to an address string,
and the `script_type` must be set to `"PAYTOADDRESS"`. `address_n` must not be set.

For outputs returning change, `address` must not be set, and `address_n` must be a
derivation path of the desired change address. `script_type` indicates the desired
address type of the change output.

For `OP_RETURN` outputs, `script_type` must be set to `"PAYTOOPRETURN"` and
`op_return_data` must be filled appropriately. `address_n` and `address` must not be
set.

`decred` fields must only be set when relevant to your currency.

### Transaction metadata

The following is a shortened definition of the `SignTx` protobuf message. Note that it
is possible to set fields `outputs_count`, `inputs_count` and `coin_name`, but their
values will be ignored. Instead, the number of elements in `outputs`, `inputs`, and the
value of `coin_name` from root object will be used.

All fields are optional unless required by your currency.

```protobuf
message SignTx {
    optional uint32 version = 4;           // transaction version
    optional uint32 lock_time = 5;         // transaction lock_time
    optional uint32 expiry = 6;            // only for Decred and Zcash
    optional bool overwintered = 7;        // only for Zcash
    optional uint32 version_group_id = 8;  // only for Zcash, nVersionGroupId when overwintered is set
    optional uint32 timestamp = 9;         // only for Peercoin, transaction timestamp
    optional uint32 branch_id = 10;        // only for Zcash, BRANCH_ID when overwintered is set
}
```

### Previous transactions

For inputs that do not use BIP-143 (SegWit) signing, each input transaction must have an
entry in the `prev_txes` object. The following object definitions are used:

```protobuf
message TxInputType {
    required bytes prev_hash = 2;     // hash of previous transaction output to spend by this input
    required uint32 prev_index = 3;   // index of previous output to spend
    optional bytes script_sig = 4;    // script signature, unset for tx to sign
    optional uint32 sequence = 5;     // sequence (default=0xffffffff)
    optional uint32 decred_tree = 9;  // only for Decred
}

message TxOutputBinType {
    required uint64 amount = 1;
    required bytes script_pubkey = 2;
    optional uint32 decred_script_version = 3;  // only for Decred
}

message TransactionType {
    optional uint32 version = 1;
    repeated TxInputType inputs = 2;
    repeated TxOutputBinType bin_outputs = 3;
    optional uint32 lock_time = 4;
    optional bytes extra_data = 8;          // only for Zcash
    optional uint32 expiry = 10;            // only for Decred and Zcash
    optional bool overwintered = 11;        // only for Zcash
    optional uint32 version_group_id = 12;  // only for Zcash, nVersionGroupId when overwintered is set
    optional uint32 timestamp = 13;         // only for Peercoin, transaction timestamp
    optional uint32 branch_id = 14;         // only for Zcash, BRANCH_ID when overwintered is set
}
```

## Encoding

Object types are encoded by a variant of [proto3 JSON mapping](https://developers.google.com/protocol-buffers/docs/proto3#json).
The following notable differences exist:

1. due to the fact that Trezor protocol uses proto2, the logic for omitted fields is
   different. If a value is missing or null in JSON, it is considered unset for the
   corresponding protobuf.
2. proto3 JSON mapping encodes `bytes` as Base64. The transaction format encodes them as
   hexadecimal strings. This will be changed in a future revision, but the hex strings
   will still be understood.
3. Field names are expected in `snake_case`, identical to the protobuf definition. In
   the future, support for `camelCase` field names will be added.

Otherwise the encoding is identical:

* numeric fields (`uint32`, `uint64`) are encoded as JSON numbers
* `bool` fields are encoded as JSON booleans (`true`, `false`)
* `string` fields are encoded as JSON strings
* `bytes` fields are encoded as JSON strings with hex representation of the bytes content
* `repeated` fields are JSON arrays of the inner type
* `enum` fields can be either a JSON number of the value, or a JSON string of the name
* nested objects are JSON objects

## Example

The JSON below encodes a transaction with the following inputs:

* [e9cec1644db8fa95fe639a9b503a63ea587d2f4e480d3847703e3ec73adf6b5a](https://btc5.trezor.io/tx/e9cec1644db8fa95fe639a9b503a63ea587d2f4e480d3847703e3ec73adf6b5a)  
  output **0** (P2PKH address 1Jw5FrKhi2aWbbF4h3QRWLog5AjsJYGswv)  
  at derivation path **m/44'/0'/0'/0/282**  
  amount **85 170** sat
* [1f545c0ca1f2c055e199c70457025c1e393edd013a274a976187115a5c601155](https://btc5.trezor.io/tx/1f545c0ca1f2c055e199c70457025c1e393edd013a274a976187115a5c601155)  
  output **0** (P2SH-SegWit address 3DEAk9KGrgvj2gHQ1hyfCXus9hZr9K8Beh)  
  at derivation path **m/49'/0'/0'/0/55**  
  amount **500 000** sat

And the following outputs:

* **12 345** sat to address **3DDEgt7quAq7XqoG6PjVXi1eeAea4rfWck**
* **562 825** sat to a P2SH-SegWit change address at derivation path **m/49'/0'/0'/1/99**
* fee of 10 000 sat

(Note that Trezor does not support change addresses when mixing input types. The example
is designed purely to showcase the JSON structure. Usually, all inputs should have the
same `script_type`.)

Transaction version is **2**, other metadata is not set.

```json
{
  "coin_name": "Bitcoin",
  "details": {
    "version": 2
  },
  "inputs": [
    {
      "address_n": [
        2147483692,
        2147483648,
        2147483648,
        0,
        282
      ],
      "amount": 85170,
      "prev_hash": "e9cec1644db8fa95fe639a9b503a63ea587d2f4e480d3847703e3ec73adf6b5a",
      "prev_index": 0,
      "script_type": "SPENDADDRESS",
      "sequence": 4294967293
    },
    {
      "address_n": [
        2147483697,
        2147483648,
        2147483648,
        0,
        55
      ],
      "amount": 500000,
      "prev_hash": "1f545c0ca1f2c055e199c70457025c1e393edd013a274a976187115a5c601155",
      "prev_index": 0,
      "script_type": "SPENDP2SHWITNESS",
      "sequence": 4294967293
    }
  ],
  "outputs": [
    {
      "address": "3DDEgt7quAq7XqoG6PjVXi1eeAea4rfWck",
      "amount": 12345,
      "script_type": "PAYTOADDRESS"
    },
    {
      "address_n": [
        2147483697,
        2147483648,
        2147483648,
        1,
        99
      ],
      "amount": 562825,
      "script_type": "PAYTOP2SHWITNESS"
    }
  ],
  "prev_txes": {
    "e9cec1644db8fa95fe639a9b503a63ea587d2f4e480d3847703e3ec73adf6b5a": {
      "bin_outputs": [
        {
          "amount": 85170,
          "script_pubkey": "76a914c4b4272ca6d3b069dcf7afdda172a7dae677d4c988ac"
        },
        {
          "amount": 2375277,
          "script_pubkey": "a914115125511fa9f301ecdda8bb73401644c260c61b87"
        }
      ],
      "inputs": [
        {
          "prev_hash": "59ef8b5633c2a8bf0a21edcbc4b9f271572061f81d42b366fe3b8bc0ec68014e",
          "prev_index": 1,
          "script_sig": "1600149043ed42ab198d95067d8760c247f164c4933f3f",
          "sequence": 4294967295
        }
      ],
      "lock_time": 0,
      "version": 1
    }
  }
}

```
