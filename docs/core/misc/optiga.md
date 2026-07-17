# Optiga data object configuration

The following table outlines the Optiga data object configuration used in Trezor Safe devices. Two configurations exist, distinguished by the presence of the TROPIC01 secure element:

* **Optiga-only**, used in Trezor Safe 3 (T2B1, T3B1) and Trezor Safe 5 (T3T1). Here *n* = 1 and `PIN_MAX_TRIES` = 16.
* **Optiga+Tropic**, used in Trezor Safe 7 (T3W1). Here *n* = 10 and `PIN_MAX_TRIES` = 10.

Throughout this document *n* denotes the number of data objects `STRETCHED_PINS[0]`, ..., `STRETCHED_PINS[n-1]` used by the PIN protection scheme and `PIN_MAX_TRIES` denotes the maximum number of PIN attempts. The table is written in terms of these two parameters. The few rows that differ structurally between the configurations are labeled accordingly. For an explanation of the PIN protection scheme that these data objects implement, including authorization graphs and design rationale, see [PIN verification](pin-verification.md).

| **OID** | **Name** | **Read** | **Write** | **Execute** | **Type/Usage** | **Size (bytes)** | **Notes** | **Storage version** |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| E0E0 | `CERT_INF` | Always | Never | Always | DEVCERT | | Infineon certificate. | |
| E0E1 | `CERT_DEV` | Always | Never | Always | DEVCERT | | Device certificate chain. | |
| E0E2 | `CERT_FIDO` | Always | Never | Always | DEVCERT | | FIDO attestation certificate. | |
| E0E3 | | | | | DEVCERT | ≤ 1728 | Unused public key certificate. | |
| E0E8 | | | | | TA | ≤ 1200 | Unused root CA public key certificate. | |
| E0E9 | | | | | TA | ≤ 1200 | Unused root CA public key certificate. | |
| E0F0 | `KEY_DEV` | Never | Never | Conf(`KEY_PAIRING`) | Sign | | NIST P-256 device private key. | |
| E0F1 | | | | | | | Unused private ECC key. | |
| E0F2 | `KEY_FIDO` | Never | Never | Conf(`KEY_PAIRING`) | Sign | | NIST P-256 FIDO attestation private key. | |
| E0F3 | `PIN_ECDH` | Never | Always | Luc(`PIN_TOTAL_CTR`) | KeyAgree | | NIST P-256 key for ECDH PIN stretching step. | ≥ 3 |
| E120 | `STRETCHED_PIN_CTR` | Always | Auto(`PIN_SECRET`) | Always | UPCTR | 8 | Counter which limits the guesses at `STRETCHED_PINS[*]`. Limit set to `PIN_MAX_TRIES`. | ≥ 3 |
| E121 | `PIN_TOTAL_CTR` | Always | Never | Always | UPCTR | 8 | Counter which limits the total number of PIN stretching operations over the lifetime of the device. Limit set to 600000. | ≥ 3 |
| E122 | `PIN_HMAC_CTR` | Always | Auto(`STRETCHED_PINS[0]`) | Always | UPCTR | 8 | Counter which limits the use of `PIN_HMAC`. Limit set to `PIN_MAX_TRIES`. | ≥ 5 |
| E123 | | | | | UPCTR | 8 | Unused monotonic counter. | |
| E140 | `KEY_PAIRING` | Never | Never | Always | PTFBIND | 32 | Shared platform binding secret. | |
| E200 | `PIN_CMAC` | Never | Always | Luc(`PIN_TOTAL_CTR`) | Enc | 32 | Key for AES-CMAC PIN stretching step. | ≥ 3 |
| F1D0 | `PIN_SECRET` | Auto(`STRETCHED_PINS[n-1]`) | Always | Always | AUTOREF | 32 | Counter-protected PIN secret and reset key for `STRETCHED_PIN_CTR`. | ≥ 3 |
| F1D1 | Optiga-only: `PIN_HMAC_V4` | Never | Never | Luc(`PIN_TOTAL_CTR`) | PRESSEC | 32 | Deprecated key for HMAC-SHA256 PIN stretching step. In the Optiga+Tropic configuration this OID holds `STRETCHED_PINS[1]`, see the next row. | 3, 4 |
| F1D1 | Optiga+Tropic: `STRETCHED_PINS[1]` | Auto(`STRETCHED_PINS[0]`) | Auto(`STRETCHED_PINS[2]`) | Luc(`STRETCHED_PIN_CTR`) | AUTOREF | 32 | Digest of the second stretched PIN. In the Optiga-only configuration this OID holds the deprecated `PIN_HMAC_V4`, see the previous row. | ≥ 6 |
| F1D2 | `STRETCHED_PINS[2]` | Auto(`STRETCHED_PINS[1]`) | Auto(`STRETCHED_PINS[3]`) | Luc(`STRETCHED_PIN_CTR`) | AUTOREF | 32 | Unused in the Optiga-only configuration. | ≥ 6 |
| F1D3 | `STRETCHED_PINS[3]` | Auto(`STRETCHED_PINS[2]`) | Auto(`STRETCHED_PINS[4]`) | Luc(`STRETCHED_PIN_CTR`) | AUTOREF | 32 | Unused in the Optiga-only configuration. | ≥ 6 |
| F1D4 | `STRETCHED_PINS[0]` | Never | Auto(`STRETCHED_PINS[1]`) | Luc(`STRETCHED_PIN_CTR`) | AUTOREF | 32 | Digest of the first stretched PIN. Named `STRETCHED_PIN` in the code paths where *n* = 1. This OID is used as the first slot in both configurations to preserve compatibility. | ≥ 3 |
| F1D5 | `STRETCHED_PINS[4]` | Auto(`STRETCHED_PINS[3]`) | Auto(`STRETCHED_PINS[5]`) | Luc(`STRETCHED_PIN_CTR`) | AUTOREF | 32 | Unused in the Optiga-only configuration. | ≥ 6 |
| F1D6 | `STRETCHED_PINS[5]` | Auto(`STRETCHED_PINS[4]`) | Auto(`STRETCHED_PINS[6]`) | Luc(`STRETCHED_PIN_CTR`) | AUTOREF | 32 | Unused in the Optiga-only configuration. | ≥ 6 |
| F1D7 | `STRETCHED_PINS[6]` | Auto(`STRETCHED_PINS[5]`) | Auto(`STRETCHED_PINS[7]`) | Luc(`STRETCHED_PIN_CTR`) | AUTOREF | 32 | Unused in the Optiga-only configuration. | ≥ 6 |
| F1D8 | `PIN_HMAC` | Never | Auto(`STRETCHED_PINS[0]`) | Luc(`PIN_HMAC_CTR`) | PRESSEC | 32 | Counter-protected key for HMAC-SHA256 PIN stretching step. | ≥ 5 |
| F1D9 | `STRETCHED_PINS[7]` | Auto(`STRETCHED_PINS[6]`) | Auto(`STRETCHED_PINS[8]`) | Luc(`STRETCHED_PIN_CTR`) | AUTOREF | 32 | Unused in the Optiga-only configuration. | ≥ 6 |
| F1DA | `STRETCHED_PINS[8]` | Auto(`STRETCHED_PINS[7]`) | Auto(`STRETCHED_PINS[9]`) | Luc(`STRETCHED_PIN_CTR`) | AUTOREF | 32 | Unused in the Optiga-only configuration. | ≥ 6 |
| F1DB | `STRETCHED_PINS[9]` | Auto(`STRETCHED_PINS[8]`) | Auto(`PIN_SECRET`) | Luc(`STRETCHED_PIN_CTR`) | AUTOREF | 32 | Unused in the Optiga-only configuration. | ≥ 6 |
| F1E0 | | | | | | ≤ 1500 | Unused data object. | |
| F1E1 | | | | | | ≤ 1500 | Unused data object. | |

Notes on the table:

* Access conditions written in terms of `STRETCHED_PINS[n-1]` refer to `STRETCHED_PINS[9]` (F1DB) in the Optiga+Tropic configuration and to `STRETCHED_PINS[0]` (F1D4) in the Optiga-only configuration. In the Optiga-only configuration (*n* = 1) the chain consists solely of `STRETCHED_PINS[0]`: its write access is Auto(`PIN_SECRET`) and its authorization directly grants read access to `PIN_SECRET`.
* The read and write access conditions of the `STRETCHED_PINS[*]` objects form a chain: authorization with `STRETCHED_PINS[i]` grants read access to `STRETCHED_PINS[i+1]`, terminating in read access to `PIN_SECRET`, and authorization with `STRETCHED_PINS[i+1]` grants write access to `STRETCHED_PINS[i]`, so that the chain can be rewritten starting from `PIN_SECRET` when the PIN is set. The purpose of the chain is explained in [PIN verification](pin-verification.md).
