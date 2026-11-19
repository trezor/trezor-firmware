# Safety checks

The safety check setting (`SafetyCheckLevel`) determines how Trezor responds
to requests that may be dangerous to the user, such as a request to sign a
transaction with an excessive fee.

| Level               | Response to a dangerous request                             |
|---------------------|-------------------------------------------------------------|
| `Strict`            | Trezor rejects the request. This is the default.            |
| `PromptAlways`      | Trezor warns the user and continues if the user confirms.   |
| `PromptTemporarily` | Like `PromptAlways`, but reverts to `Strict` after restart. |

We say that safety checks are disabled if the level is `PromptAlways` or
`PromptTemporarily`. This document describes which checks the setting may
disable and what Trezor has to do once it has disabled them.

## Which checks can be disabled

A check should depend on the setting only if the request which it rejects has a
legitimate use that cannot be achieved while the check is enforced. For
example, signing with a key at a non-standard derivation path is the only way
to recover funds that were sent to such a path.

## Warning the user

Disabling safety checks is an exceptional operation. When safety checks are
disabled, Trezor's only duty is to warn the user when a workflow enters the
territory that is inaccessible under `Strict`.

- A warning is shown before the dangerous action which it concerns.
- Displaying a value is not a warning. A derivation path shown on the address
  screen does not tell the user that the path is unusual. The warning has to
  be a separate prompt which states what is wrong.
- Each distinct kind of risk requires its own warning, since a warning about one
  kind of risk does not tell the user about another. For example, a warning
  about the fee does not cover a change address at a non-standard path.
- One warning per kind of risk is sufficient in a workflow, unless the warning
  names a specific instance, such as the path. It then covers only that
  instance. Warning about each instance should be weighed against its cost in
  implementation complexity, resources and scalability.

## Non-standard derivation paths

A path is non-standard if it does not match any of the path schemas of the
application. Under `Strict` safety checks, Trezor rejects a request which uses
such a path. When safety checks are disabled, Trezor accepts the request.
Whether it has to show a warning depends on how the request uses the key at the
path.

A path which the user has to unlock before use, such as a SLIP-25 path, is not
a non-standard path. Trezor rejects it at every safety check level until the
user unlocks it.

### Returning without displaying

A public key or an address is generally safe to release. Thus, returning one to
the host without displaying it requires no warning, even at a non-standard
path.

There are exceptions:

- A quantum computer may be able to compute the private key of an exported
  XPUB and with it the private keys of the entire subtree. Trezor therefore
  warns before exporting an XPUB whose subtree is particularly sensitive. This
  warning is shown at every safety check level, see `validate_xpub_export()`.
- A public key or an address at a path which the user has to unlock, such as a
  SLIP-25 path, reveals private information. This is why Trezor rejects such a
  path until the user unlocks it.

### Displaying

The user treats a displayed address or public key as one that is safe to
receive funds to. An attacker who controls the host could have the user confirm
an address at a path with random high-entropy indices. Wallets would not
discover the funds sent to this address and the attacker could demand a ransom
for revealing the path. Thus, an address or a public key at a non-standard path
is displayed only after a warning.

A change address is treated as a displayed address, since the user receives
funds at it. This applies even though Trezor does not display the address. The
same holds for an address for which Trezor issues a message authentication code
(MAC), by which it later recognises the address as the user's own, see
`get_address_mac()`.

### Signing

A key at a non-standard path may hold funds of a different coin than the one
named in the request. An attacker who controls the host could have the user
sign a seemingly harmless testnet transaction which in fact spends the user's
bitcoins. Thus, signing with a key at a non-standard path requires a warning.
