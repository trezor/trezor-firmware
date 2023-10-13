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

## Adding a new coin

### Forks and derivatives

If the coin you are adding is a fork of Bitcoin or other cryptocurrency
we already support (in other words, new app is not needed) you can
modify the definitions in the [trezor-firmware][] repository and file a
PR. In such case the coin does not have to be in TOP30 (see below), but
we still reserve the right not to include the coin. The location depends
on the type of the asset to be added:

-   **Bitcoin clones** should be added to the [common/defs/bitcoin][]
    subdirectory as separate .json files
-   **Ethereum networks/chains** should be added to the
    [ethereum-lists/chains][]
-   **Ethereum tokens** should be added to the [ethereum-lists/tokens][]
    repository
-   **NEM mosaics** should be added to the
    [common/defs/nem/nem_mosaics.json][] file

### Other

At the moment, we do not have the capacity to add new coins that do not
fit the aforementioned category. Our current product goal is to unite
what we support in firmware and in Trezor Suite and since firmware is
way ahead of Suite we want to pause for a bit, implement the remaining
coins into Suite and then consider adding new coins. This effectively
means that **our team will not be accepting any requests to add new
cryptocurrencies.**

  [trezor-firmware]: https://github.com/trezor/trezor-firmware
  [common/defs/bitcoin]: https://github.com/trezor/trezor-firmware/tree/main/common/defs/bitcoin
  [ethereum-lists/chains]: https://github.com/ethereum-lists/chains
  [ethereum-lists/tokens]: https://github.com/ethereum-lists/tokens
  [common/defs/nem/nem_mosaics.json]: https://github.com/trezor/trezor-firmware/tree/main/common/defs/nem/nem_mosaics.json
  [common/defs/misc/misc.json]: https://github.com/trezor/trezor-firmware/tree/main/common/defs/misc/misc.json
