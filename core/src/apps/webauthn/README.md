# WebAuthn

MAINTAINER = Andrew R. Kozlik <andrew.kozlik@satoshilabs.com>

AUTHOR = Andrew R. Kozlik <andrew.kozlik@satoshilabs.com>

REVIEWER = Jan Pochyla <jan.pochyla@satoshilabs.com>, Ondrej Vejpustek <ondrej.vejpustek@satoshilabs.com>

-----

This app implements WebAuthn authenticator functionality in accordance with the following specifications:

* [Web Authentication](https://www.w3.org/TR/webauthn/): An API for accessing Public Key Credentials Level 1, W3C Recommendation, 4 March 2019
* [FIDO Client to Authenticator Protocol (CTAP) v2.0](https://fidoalliance.org/specs/fido-v2.0-ps-20190130/fido-client-to-authenticator-protocol-v2.0-ps-20190130.html#sctn-hmac-secret-extension), Proposed Standard, January 30, 2019
* [SLIP-0022](https://github.com/satoshilabs/slips/blob/master/slip-0022.md): FIDO2 credential ID format for HD wallets

## Supported features and algorithms

This implementation supports client-side credential storage on the device and user verification by PIN entry, making the Trezor T a first-factor roaming authenticator usable for passwordless login.

### User verification

The device is capable of verifying the user within itself by direct PIN entry via the touchscreen. Client PIN is not supported, because it is less secure than direct PIN verification. The authenticatorClientPIN command is therefore implemented only to the extent required by the hmac-secret extension. Namely, only the getKeyAgreement subcommand is supported.

### Credential selection

Credential selection is supported directly on the device. The authenticatorGetNextAssertion command is therefore not implemented.

### Public key credential algorithms

* COSE algorithm ES256 (-7): ECDSA using the NIST P-256 curve with SHA-256.

### Extenstions

* hmac-secret extension.

### Attestation types

* Self attestation.
