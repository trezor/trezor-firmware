# Bitcoin signing flow

The Bitcoin signing process is one of the most complicated workflows in the Trezor
codebase. This is because Trezor cannot store arbitrarily large transactions in memory,
so both the input data and the results must be sent in chunks. The Protobuf messages
cannot fully encode the data pertaining to a single transaction; instead, the data
is spread out over multiple messages.

## Overview

The signing flow is initiated by a `SignTx` command. The message contains the name of
the coin, number of inputs and outputs, and transaction metadata: version, lock time,
and others that are required for some coins.

In response, Trezor will send a number of `TxRequest` messages, asking for additional
data from the host. The host is supposed to respond with a `TxAck` providing the
requested data.

Trezor can request the following kinds of items:

* input of the transaction being signed
* output of the transaction being signed
* metadata of a _previous transaction_, i.e., the transaction whose UTXO is being spent
* metadata of an _original transaction_, i.e., a transaction that is being replaced by
  the current transaction
* input of a previous or original transaction
* output of a previous or original transaction
* additional trailing data of a previous transaction

As part of each `TxRequest` message, Trezor can also send a chunk of the resulting
serialized transaction, and/or a signature of one of the inputs.

The flow ends when Trezor sends a `TxRequest` with `request_type` of `TXFINISHED`.

## Signing phases

The following content is for reference only, and details might change in the future.
Host code should make no assumptions about the order of the phases.

The list of phases here also does not necessarily correspond to internal phase
numbering.

### Gathering info about current transaction

Trezor will request all inputs and outputs of the transaction to be signed, and set up
data structures that allow it to verify that the same data is sent in the following
phases.

In this phase, Trezor will also ask the user to confirm destination addresses,
the transaction fee, metadata, and the total being sent. If the user confirms, we continue
to the next phase.

### Validation of input data

Trezor must verify that the host does not lie about input amounts, i.e., that the
transaction total in the first phase was calculated correctly.

For this reason, Trezor will ask the host to send each input again. It will then request
data about the referenced previous transaction: metadata, all inputs, all outputs, and
possible trailing data. This allows Trezor to reconstruct the previous transaction and
calculate its hash. If this hash matches the provided one, and the amount on selected
UTXO matches the input amount, the given input is considered valid.

If all internal inputs are taproot, then the verification of the previous transactions
is skipped. This is possible because if the host provides invalid information about the
UTXOs being spent, then the resulting taproot signatures will also be invalid.

Trezor T also supports pre-signed inputs for multi-party signing. If an input has script
type `EXTERNAL` and provides a signature, Trezor will validate the signature against the
previous transaction in this step.

### Serialization and signing

Trezor will ask once again about every input and begin outputting a serialization of the
transaction. For every legacy (non-segwit) input, it is necessary to stream the full set
of inputs and outputs again, so that Trezor can compute the transaction digest which it
then signs. For segwit inputs this is not necessary.

When all inputs are serialized, Trezor will ask for every output, so that it can
serialize it, fill out change addresses, and return the full transaction.

Finally Trezor asks again about segwit inputs to sign them and to serialize the
witnesses.

## Old versus new data structures

Originally, the `TxAck` message contained one field of type `TransactionType`. This, in
turn, contained all the possible fields that Trezor could request:

* `TransactionType` itself contains fields for all necessary metadata, plus a field
  `extra_data` for trailing data.
* `TransactionType.inputs` is an array of `TxInputType` objects, each of which can
  describe either the current input, or an input of a previous transaction.
* `TransactionType.outputs` is an array of `TxOutputType` objects, each of which can
  describe an output of the _current_ transaction.
* `TransactionType.bin_outputs` is an array of `TxOutputBinType` objects, each of which
  can describe an output of a _previous_ transaction.

This organization makes it practical to use the `TransactionType` for host-side storage:
a transaction can be fully stored in one object, and in order to send a `TxAck`
response, you only need to extract the appropriate data.

The cost of this is that this organization makes it extremely unclear _which data_
should be extracted at which points.

To make the constraints more visible, a new set of data types was designed. There is a
`TxAck<Kind>` message for every `Kind` of data. These only define the fields that are
appropriate for that kind of request.

It is possible to use both representations, as they are wire-compatible. However, we
recommend using the new definitions for new applications.

## Request types

The `TxRequest` message always contains a `request_type` field, indicating which kind of
data it wants. In addition, `request_details` specify the particular piece of data
requested.

If `request_details.tx_hash` is set, Trezor is requesting data about a specified
previous transaction. If it is unset, Trezor wants data about current transaction.

### Transaction input

Trezor sets `request_type` to `TXINPUT`, and `request_details.tx_hash` is unset.

`request_details.request_index` is the index of the input in the transaction: 0 is the
first input, 1 is second, etc.

**Old style:** Host must respond with a `TxAck` message. The field `tx.inputs` must be
set to an array of one element, which describes the requested input. All other fields
should be left unset.

**New style:** Host must respond with a `TxAckInput` message. All relevant data must be
set on `tx.input`.

#### Normal (internal) inputs

Usually, the user owns, and wants to sign, all inputs of the transaction. For that, the
host must specify a derivation path for the key, and script type `SPENDADDRESS` (legacy),
`SPENDP2SHWITNESS` (P2SH segwit), `SPENDWITNESS` (native segwit) or `SPENDTAPROOT`.

#### Multisig inputs

For multisig inputs, the XPUBs of all signers (including the current user) must be
provided in the `multisig` structure. Legacy multisig uses type `SPENDMULTISIG`, P2SH
segwit and native segwit multisig use the same type as non-multisig inputs, i.e.
`SPENDP2SHWITNESS` or `SPENDWITNESS`.

Full documentation for multisig is TBD.

#### External inputs

Trezor T can include inputs that it will not sign, typically because they are owned by
another party. Such inputs are of type `EXTERNAL` and the host does not specify a
derivation path for the key. Instead, these inputs must either already have a valid
signature or they must come with an ownership proof. If the input already has a valid
signature, then the host provides the `script_sig` and/or `witness` fields. If the other
signing party hasn't signed their input yet (i.e., with two Trezors, one must sign first
so that the other can include a pre-signed input), they can instead provide a
[SLIP-19](https://github.com/satoshilabs/slips/blob/master/slip-0019.md)
ownership proof in the `ownership_proof` field, with optional commitment data in
`commitment_data`. The `script_pubkey` field is required for all external inputs.

### Transaction output

Trezor sets `request_type` to `OUTPUT`, and `request_details.tx_hash` is unset.

`request_details.request_index` is the index of the output in the transaction: 0 is the
first input, 1 is second, etc.

**Old style:** Host must respond with a `TxAck` message. The field `tx.outputs` must be
set to an array of one element, which describes the requested output. All other fields
should be left unset.

**New style:** Host must respond with a `TxAckOutput` message. All relevant data must be
set on `tx.output`.

#### External outputs

Outputs that send coins to a particular address are always of type `PAYTOADDRESS`. The
address is sent as a string in the field `address`.

#### Change outputs

Outputs that send coins back to the same owner must specify a derivation path and the
appropriate script type. If the derivation path has the same prefix as _all_ inputs, and
a matching script type (legacy, p2sh segwit, native segwit), it is considered to be a
change output, and its amount is subtracted from the total.

`address` must not be specified in this case. It is instead derived internally from the
provided derivation path.

#### OP_RETURN outputs

Outputs of type `PAYTOOPRETURN` must not specify `address` nor `address_n`, and the
`amount` must be zero. The OP_RETURN data is sent as `op_return_data` field.

### Previous transaction metadata

Trezor sets `request_type` to `TXMETA`. `request_details.tx_hash` is a transaction hash,
matching one of the current transaction inputs.

**Old style:** Host must respond with a `TxAck` message. The structure `tx` must be
filled out with relevant data, in particular, `inputs_cnt` and `outputs_cnt` must be set
to the number of transaction inputs and outputs. Arrays `inputs`, `outputs`,
`bin_outputs` and `extra_data` should be empty.

**New style:** Host must respond with a `TxAckPrevMeta` message. All relevant data must
be set on `tx`.

#### Extra data

Some coins (e.g., Zcash) contain data at the end of transaction serialization that
Trezor does not understand. The host must indicate the length of this extra data in the
field `extra_data_len`.

To figure out which is the extra data, the host must parse the serialized previous
transaction up to the last field understood by Trezor. In case of Zcash, that is:

* version + version group ID
* number of inputs, and every input
* number of outputs, and every output
* lock time
* expiry

All data after the `expiry` field is considered "extra data".

### Previous transaction input

Trezor sets `request_type` to `TXINPUT`. `request_details.tx_hash` is a transaction
hash, matching one of the current transaction inputs.

**Old style:** Host must respond with a `TxAck` message. The field `tx.inputs` must be
set to an array of one element, which describes the requested input of the specified
previous transaction. All other fields should be left unset.

**New style:** Host must respond with a `TxAckPrevInput` message. All relevant data must
be set on `tx.input`.

### Previous transaction output

Trezor sets `request_type` to `TXOUTPUT`. `request_details.tx_hash` is a transaction
hash, matching one of the current transaction inputs.

**Old style:** Host must respond with a `TxAck` message. The field `tx.bin_outputs` must
be set to an array of one element, which describes the requested output of the specified
previous transaction. All other fields should be left unset.

**New style:** Host must respond with a `TxAckPrevOutput` message. All relevant data
must be set on `tx.output`.

### Previous transaction trailing data

On some coins, such as Zcash, the transaction serialization can contain data not
understood by Trezor. This data is not relevant for validation, but it must be included
so that Trezor can correctly compute the previous transaction hash.

Trezor sets `request_type` to `TXEXTRADATA`. `request_details.tx_hash` is a transaction
hash, matching one of the current transaction inputs.

`request_details.extra_data_offset` specifies the offset of the requested data from the
_start_ of the extra data. `request_details.extra_data_length` specifies the length of
the requested chunk.

**Old style:** Host must respond with a `TxAck` message. The field `tx.extra_data` must
contain the specified chunk, starting at the given offset and of exactly the given
length. All other fields should be unset.

**New style:** Host must respond with a `TxAckPrevExtraData` message. The chunk must be
set to `tx.extra_data_chunk`.

### Original transaction input

Trezor sets `request_type` to `TXORIGINPUT`. `request_details.tx_hash` is the
transaction hash of the original transaction.

Host must respond with a `TxAckInput` message. All relevant data must be set in
`tx.input`. The derivation path and `script_type` are mandatory for all original
internal inputs. For each original transaction, one of its original internal inputs must
be accompanied with a valid signature in the `script_sig` and/or `witness` fields.

### Original transaction output

Trezor sets `request_type` to `TXORIGOUTPUT`. `request_details.tx_hash` is the
transaction hash of the original transaction.

Host must respond with a `TxAckOutput` message. All relevant data must be set in
`tx.output`. The derivation path and script type are mandatory for all original
change-outputs.

## Replacement transactions

A replacement transaction is a transaction that uses the same inputs as one or more
transactions which have already been signed (the original transactions). Replacement
transactions can be used to securely bump the fee of an already signed transaction
([BIP-125](https://github.com/bitcoin/bips/blob/master/bip-0125.mediawiki)) or to
participate as a sender in PayJoin
([BIP-78](https://github.com/bitcoin/bips/blob/master/bip-0078.mediawiki)). Trezor only
supports signing of replacement transaction which do not increase the amount that the
user is spending on external outputs. Thus when signing a replacement transaction the
user only needs to confirm the fee modification and the original TXIDs without being
shown any outputs, since the original external outputs must have already been confirmed
by the user and any new external outputs can only be paid for by new external inputs.

The host signals that a transaction is a replacement transaction by setting the
`orig_hash` and `orig_index` fields for at least one `TxInput`. Trezor will then
automatically request metadata about the original transaction and verify the original
signatures.

A replacement transaction in Trezor must satisfy the following requirements:

* All inputs of the original transactions must be inputs of the replacement transation.
* All _external_ outputs of the original transactions must be outputs of the replacement
  transation.
* The value of an external output may be decreased only if there are no new external
  inputs. This should only be used to bump the fee if the original transaction transfers
  the entire account balance and there is no other source available to bump the fee.
* The replacement transaction must not increase the amount that the user is spending
  on external outputs.
* Original transactions must have the same effective `nLockTime` as the replacement
  transaction.
* The inputs and outputs of the original transactions must not be permuted in the
  replacement transaction, but they can be interleaved with new inputs or with inputs
  from another original transaction.
* New `OP_RETURN` outputs cannot be added in the replacement transaction.

So the replacement transaction is, for example, allowed to:

* Increase the user's contribution to the mining fee by adding new inputs or decreasing
  or removing change outputs.
* Decrease the user's contribution to the mining fee by increasing or adding
  change-outputs.
* Add external inputs (PayJoin) and use them to introduce new outputs, increase the
  original external outputs or even to increase the user's change outputs so as to
  decrease the amount that the user is spending.

## Implementation notes

### Pseudo-code

The following is a rough outline of host-side implementation. See above for detailed
info.

```python
transaction_bytes = ""
signatures = [""] * len(INPUTS)

def sign_tx():
    # send initial message
    send_message(
        SignTx(
            coin_name,
            inputs_count=len(INPUTS),
            outputs_count=len(OUTPUTS),
            # ...fill individual metadata fields
        )
    )

    # wait for TxAck forever, until Trezor indicates we are finished
    while True:
        msg = receive_message()

        # extract data first
        extract_streamed_data(msg.serialized)

        if msg.request_type == TXFINISHED:
            # we are done
            break

        if msg.details.tx_hash is not None:
            # Trezor requires data about some previous transaction
            send_response_prev(msg.request_type, msg.details)
        else:
            # Trezor requires data about this transaction
            send_response_current(msg.request_type, msg.details)

def extract_streamed_data(ser: TxRequestSerializedType):
    global transaction_bytes, signatures
    # append serialized data to what we got so far
    transaction_bytes += ser.serialized_tx
    if ser.signature_index is not None:
        # read the signature
        signatures[ser.signature_index] = ser.signature

def send_response_prev(request_type: RequestType, details: TxRequestDetailsType):
    prev_tx = get_prev_tx(details.tx_hash)
    if request_type == TXINPUT:
        send_prev_input(prev_tx.inputs[details.request_index])
    elif request_type == TXOUTPUT:
        send_prev_output(prev_tx.outputs[details.request_index])
    elif request_type == TXMETA:
        send_prev_metadata(prev_tx)
    elif request_type == TXEXTRADATA:
        offset = details.extra_data_offset
        length = details.extra_data_length
        extra_data_chunk = prev_tx.extra_data[offset : offset + length]
        send_prev_extra_data(extra_data_chunk)

def send_response_current(request_type: RequestType, details: TxRequestDetailsType):
    if request_type == TXINPUT:
        send_input(INPUTS[details.request_index])
    elif request_type == TXOUTPUT:
        send_output(OUTPUTS[details.request_index])
```

### Wire compatibility

The new definitions are structured so that the Protobuf binary encoded form can be
decoded into both representations. This means that the host can encode data in the old
representation, and Trezor will successfully and correctly decode it into the new one.

This is done by reusing field IDs as appropriate, and taking advantage of the fact that
Protobuf encodes arrays as a sequence of the same field repeated a number of times.

For example, here is a part of the `TxAck` definition:

```protobuf
message TxAck {
    optional TransactionType tx = 1;

    message TransactionType {
        // ... some fields omitted ...
        repeated TxInputType inputs = 2;
        // ... some fields omitted ...

        message TxInputType {
            repeated uint32 address_n = 1;
            // ... some fields omitted ...
            optional uint64 amount = 8;
            // ... some fields omitted ...
        }
    }
}
```

A message carrying these fields would look like this:

```
FIELD 1 (type NESTED):
    FIELD 2 (type NESTED):
        FIELD 1 (type int): 0x8000002c
        FIELD 1 (type int): 0x80000000
        FIELD 1 (type int): 0x80000000
        FIELD 1 (type int): 0
        FIELD 1 (type int): 0
        FIELD 8 (type int): 1234567
```

We can see that this is identical as if the type definition looked as follows; indeed,
we only renamed the types, removed some fields, and set some `optional` or `repeated`
to `required` instead.

```protobuf
message TxAckInput {
    required TxAckInputWrapper tx = 1;

    message TxAckInputWrapper {
        required TxInput input = 2; // the field is now required instead of repeated

        message TxInput {
            repeated uint32 address_n = 1;
            required uint64 amount = 8;
        }
    }
}
```

A caveat of this approach is that this introduces invisible dependencies: `TxInput` and
`PrevInput` fold into the same old-style `TxInputType`, so adding new fields must be
done carefully.

We expect to gradually deprecate the `TransactionType`. At that point, the new-style
types will be fully independent.
