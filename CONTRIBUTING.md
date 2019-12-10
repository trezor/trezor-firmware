# Contribute to Trezor Firmware

Please read the general instructions you can find on our [wiki](https://wiki.trezor.io/Developers_guide:Contributing).

In this repository your Pull request should follow these criteria:

- The code is properly tested.
- Tests must pass on [CI](https://travis-ci.org/trezor/trezor-firmware).
- The code is properly formatted. The make command `make style_check` checks if it is so and you can use `make style` to make it happen.
- Generated files are up-to-date. Use `make gen` in repository root to make it happen.
- Commits must have concise commit messages, the imperative mood is preferred ([rationale](https://gist.github.com/robertpainsi/b632364184e70900af4ab688decf6f53)).
- Multiple commits per PR are allowed, but please do not use reverts etc. - use interactive rebase.
Do not use merge (e.g. merge trezor/master into...). Again, use rebase.
