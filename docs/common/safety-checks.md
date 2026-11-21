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

- The warning is shown before the dangerous action is carried out.
- Displaying a value is not a warning. A derivation path shown on the address
  screen does not tell the user that the path is unusual. The warning has to
  be a separate prompt which states what is wrong.
- One warning per workflow is sufficient. A warning may be repeated within a
  workflow if there is a security reason to do so, and if it does not introduce
  implementation complexity, requires no extra resources and does not affect
  the scalability of the workflow.

## Public keys and addresses

Public keys are generally safe to release. Thus, returning a public key or an
address to the host without displaying it requires no warning, even if the
derivation path is non-standard.

There are exceptions. A quantum computer may be able to compute the private key
of an exported XPUB and with it the private keys of the entire subtree. Trezor
therefore warns before exporting an XPUB whose subtree is particularly
sensitive. This warning is shown at every level, see `validate_xpub_export()`.

Displaying an address is different, because the user treats a displayed address
as one that is safe to receive funds to. An attacker who controls the host
could have the user confirm an address at a path with random high-entropy
indices. Wallets would not discover the funds sent to this address and the
attacker could demand a ransom for revealing the path. Thus, an address or a
public key at a non-standard path is displayed only after a warning. The same
applies to a change address, since Trezor then sends funds to the path without
displaying the address at all.
