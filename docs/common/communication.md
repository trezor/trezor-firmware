# Communication

We use [Protobuf v2](https://developers.google.com/protocol-buffers/) for host-device communication. The communication cycle is very simple, Trezor receives a message, acts on it and responds with another message. Trezor on its own is incapable of initiating the communication.

The Protobuf definitions can be found in `common/protob`.
