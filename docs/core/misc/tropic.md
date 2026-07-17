# Tropic slot configuration

This document outlines how the firmware uses the slots of the TROPIC01 secure element in Trezor Safe 7 (T3W1). For the chip's user access privilege configuration, see [Tropic configurations](tropic_configs.md). For an explanation of how the mac-and-destroy slots and the KEK masks are used in PIN protection, see [PIN verification](pin-verification.md).

## Pairing key slots

| **Slot** | **Name** | **Usage** |
| --- | --- | --- |
| 0 | `FACTORY_PAIRING_KEY_SLOT` | Used by prodtest to inject the privileged and unprivileged pairing keys. |
| 1 | `UNPRIVILEGED_PAIRING_KEY_SLOT` | Used by the HSM to inject the FIDO attestation key and generate the device key, and by unofficial firmware. |
| 2 | `PRIVILEGED_PAIRING_KEY_SLOT` | Used by official firmware. |
| 3 | | Unused. |

Sessions established with the privileged and unprivileged pairing keys operate on disjoint sets of mac-and-destroy and KEK masks slots, see below.

## ECC key slots

| **Slot** | **Name** | **Usage** |
| --- | --- | --- |
| 0 | `DEVICE_KEY_SLOT` | Device attestation private key. |
| 1 | `FIDO_KEY_SLOT` | FIDO attestation private key. |
| 2–31 | | Unused. |

## R-memory data slots

Each slot holds up to 444 bytes (475 bytes from Tropic firmware version 2.0.0, limited to 444 for backwards compatibility).

| **Slot** | **Name** | **Usage** |
| --- | --- | --- |
| 0–2 | `FIDO_CERT_FIRST_SLOT` | FIDO attestation certificate. |
| 3–5 | `DEVICE_CERT_FIRST_SLOT` | Device attestation certificate chain. |
| 6 | `CONFIG_DISTRIBUTION_VERSION_SLOT` | Version of the Tropic configuration. |
| 7 | `CONFIG_BACKUP_DISTRIBUTION_VERSION_SLOT` | Backup of slot 6. |
| 8–127 | | Unused. |
| 128 | `KEK_MASKS_PRIVILEGED_SLOT` | XOR masks of the storage key encryption key, one 32-byte mask per PIN attempt index. Written and read by the privileged session. |
| 129–255 | | Unused. |
| 256 | `KEK_MASKS_UNPRIVILEGED_SLOT` | As slot 128, for the unprivileged session. |
| 257–511 | | Unused. |

## Mac-and-destroy slots

The chip provides 128 mac-and-destroy slots. Slots 0–63 are used by the privileged session and slots 64–127 by the unprivileged session (`FIRST_MAC_AND_DESTROY_SLOT_PRIVILEGED` and `FIRST_MAC_AND_DESTROY_SLOT_UNPRIVILEGED` in the code).

Within its 64-slot range, the slot used for PIN attempt index *i* is

```
slot = first_slot + (change_pin_counter * 11 + i) mod 64
```

where `change_pin_counter` is the number of times the PIN has been changed (see below). Shifting the slot allocation on every PIN change spreads wear across the slots. The shift constant 11 is coprime to 64, so the allocation achieves the maximum possible period in `change_pin_counter`.

## Monotonic counter slots

| **Slot** | **Name** | **Usage** |
| --- | --- | --- |
| 0–3 | | Unused. |
| 4 | `CHANGE_COUNTER_SLOT` | Counts the number of times the PIN has been changed. Tropic monotonic counters only decrement, so the stored value is `0xfffffffe` minus the number of PIN changes. Shared by the privileged and unprivileged sessions. |
| 5–15 | | Unused. |
