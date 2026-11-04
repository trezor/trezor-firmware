# Trezor card model

Reference model of a Trezor NFC card, which holds the seed and performs every operation derived from it.
The emulator's vault reaches it through `core/embed/sec/vault/card/` when built with `TREZOR_VAULT_CARD=1`.

- `card_model.c`: the card's logic as one function, APDU in and response out. No I/O.
- `server.c`: TCP server around it. One connection is one tap, and the card resets at each end of the tap.
- `transport_model.c`: the model linked in-process, for native tests or an app without a card.
- `test_vault_card.c`: the emulator's `vault_card.c` backend against the model, with the local vault stubbed.
- `test_card_tap.c`: the same over TCP against a server playing a slow user: prompt, re-tap, cancel and timeout.

The protocol is in `core/embed/sec/vault/card/card_proto.h`.

```sh
make -C tests/card_model test                  # native tests, in-process and over TCP
make -C tests/card_model                       # also builds build/card_model_server
tests/card_model/build/card_model_server -v    # 127.0.0.1:28993, "all all ..." seed
TREZOR_VAULT_CARD=1 xtask build firmware --emulator -m T3T1 -p test-live
./core/emu.py                                  # asks for the card on screen
```

`-p` sets another port, which the emulator reads from `TREZOR_CARD_PORT`. `-m` sets another mnemonic.
The server also plays the user who taps the card:
`-t MS` presents the card that long after the firmware asks for it, `-i` presents it when Enter is pressed,
and `-k MS` takes the card away after that long without a command, so the next operation needs a new tap.
For Android, see `docs/core/build/android.md`.

On the card: BIP-39 seed selection with the passphrase, hardened derivation and xpubs, and secp256k1 ECDSA.
On the phone: public derivation from a cached xpub, so showing addresses needs no tap.
Not yet on the card: access code, batched signing, BIP-340, Ed25519, NIST P-256, SLIP-21 and ECDH.
Those ops fail closed on a card handle.
