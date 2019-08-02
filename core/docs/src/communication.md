# Communication

We use [Protobuf v2](https://developers.google.com/protocol-buffers/) for host-device communication. The communication cycle is very simple, Trezor receives a message, acts on it and responds with another message. Trezor on its own is incapable of initiating the communication.


## Definitions

Protobuf messages are defined in the [Common](http://github.com/trezor/trezor-firmware/blob/master/common) project, which is part of this monorepo. This repository is also exported to [trezor/trezor-common](https://github.com/trezor/trezor-common) to be used by third parties, which prefer not to include the whole monorepo. This copy is read-only and all changes are happening in this monorepo.
