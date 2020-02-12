# Communication

_Note: In this section we describe the internal functioning of the communication protocol. If you wish to implement Trezor support you should use [Connect](https://github.com/trezor/connect/) or [python-trezor](https://pypi.org/project/trezor/), which will do all this hard work for you._

We use [Protobuf v2](https://developers.google.com/protocol-buffers/) for host-device communication. The communication cycle is very simple, Trezor receives a message (request), acts on it and responds with another one (response). Trezor on its own is incapable of initiating the communication.

## Definitions

Protobuf messages are defined in the [Common](https://github.com/trezor/trezor-firmware/tree/master/common) project, which is part of this monorepo. This repository is also exported to [trezor/trezor-common](https://github.com/trezor/trezor-common) to be used by third parties, which prefer not to include the whole monorepo. That copy is read-only mirror and all changes are happening in this monorepo.

## Notable topics

- [Sessions](sessions.md)
- [Passphrase](passphrase.md)

