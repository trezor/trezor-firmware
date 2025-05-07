# Solana definitions

To allow nicer token presentation on the device, Trezor allows passing a token
definition as part of the additional info. Currently only one token can be included in
the definitions. Solana tokens are uniquely identified by their mint account. Trezor
additionally expects a name and a ticker symbol.

In the future we might also include definitions for instructions.

## Retrieving the definitions
A full list of Solana definitions is compiled from multiple sources and is available [in
a separate repository](TODO).

From this list, a collection of binary blobs is generated, signed, and made available
online.

A given Trezor firmware will only accept signed definitions newer than a certain date,
typically one month before firmware release. This means that a client application should
either always fetch fresh definitions from the official URLs, or refresh its local copy
frequently.

The base URL for the definitions is `https://data.trezor.io/firmware/definitions/solana`.

To look up a token definition for a given mint account, use the following URL:

`https://data.trezor.io/firmware/definitions/solana/token/<MINT_ACCOUNT>.dat`

`<MINT_ACCOUNT>` is base58-encoded mint account of the token, e.g., `So11111111111111111111111111111111111111112`.

## Definition format

Look at [`ethereum-definitions.md`'s](ethereum_definitions.md) `Definition Format` section.
