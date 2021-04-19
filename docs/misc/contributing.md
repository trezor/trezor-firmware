# Contribute to Trezor Firmware

Please read the general instructions you can find on our
[wiki](https://wiki.trezor.io/Developers_guide:Contributing).

Your Pull Request should follow these criteria:

- The code is properly tested.
- Tests must pass on [CI](https://travis-ci.org/trezor/trezor-firmware).
- The code is properly formatted. Use `make style_check` to check the format
  and `make style` to do the required changes.
- The generated files are up-to-date. Use `make gen` in repository root to make
  it happen.
- Commits must have concise commit messages, we endorse [Conventional Commits](https://www.conventionalcommits.org).
- A [changelog entry](changelog.md) must be part of the pull request.

### Please read and follow our [review procedure](review.md).
